import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson.objectid import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Game Top-up API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utility helpers
class ObjectIdStr(str):
    @classmethod
    def validate(cls, v):
        try:
            return str(ObjectId(v))
        except Exception:
            raise ValueError("Invalid ObjectId")


def to_serializable(doc):
    if not doc:
        return doc
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    # Convert datetimes to isoformat
    for k, v in list(doc.items()):
        try:
            import datetime
            if isinstance(v, (datetime.datetime, datetime.date)):
                doc[k] = v.isoformat()
        except Exception:
            pass
    return doc


# Schemas (importing our definitions for typing clarity only)
from schemas import Game, Topupoption, Order  # noqa: E402


# Seed data model
class SeedGame(BaseModel):
    name: str
    code: str
    image: Optional[str] = None
    publisher: Optional[str] = None


@app.get("/")
def root():
    return {"message": "Game Top-up API is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# Public endpoints
@app.get("/api/games")
def list_games():
    docs = get_documents("game")
    return [to_serializable(d) for d in docs]


@app.get("/api/games/{game_code}")
def get_game_by_code(game_code: str):
    doc = db["game"].find_one({"code": game_code})
    if not doc:
        raise HTTPException(status_code=404, detail="Game not found")
    return to_serializable(doc)


@app.get("/api/games/{game_id}/options")
def list_options(game_id: str):
    docs = get_documents("topupoption", {"game_id": game_id})
    return [to_serializable(d) for d in docs]


class CreateOrder(BaseModel):
    game_id: str
    option_id: str
    player_id: str
    region: Optional[str] = None
    payment_method: str


@app.post("/api/orders")
def create_order(payload: CreateOrder):
    # fetch option to get price/credits
    option = db["topupoption"].find_one({"_id": ObjectId(payload.option_id)})
    if not option:
        raise HTTPException(status_code=404, detail="Top-up option not found")

    order_doc = {
        "game_id": payload.game_id,
        "option_id": payload.option_id,
        "player_id": payload.player_id,
        "region": payload.region,
        "payment_method": payload.payment_method,
        "status": "pending",
        "amount": float(option.get("amount", 0)),
        "credits": int(option.get("credits", 0))
    }
    order_id = create_document("order", order_doc)
    created = db["order"].find_one({"_id": ObjectId(order_id)})
    return to_serializable(created)


@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    try:
        doc = db["order"].find_one({"_id": ObjectId(order_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Order not found")
        return to_serializable(doc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")


# Seed endpoint to populate sample games and options (idempotent)
@app.post("/api/seed")
def seed_data(games: Optional[List[SeedGame]] = None):
    default_games = games or [
        SeedGame(name="Mobile Legends", code="mlbb", image="https://i.imgur.com/Kk2r6sG.png", publisher="Moonton"),
        SeedGame(name="PUBG Mobile", code="pubgm", image="https://i.imgur.com/7nYVJr9.png", publisher="Tencent"),
        SeedGame(name="Free Fire", code="ff", image="https://i.imgur.com/4J2hX3E.png", publisher="Garena"),
    ]

    created_games = []
    for g in default_games:
        existing = db["game"].find_one({"code": g.code})
        if existing:
            created_games.append(to_serializable(existing))
            continue
        inserted_id = create_document("game", g.model_dump())
        created = db["game"].find_one({"_id": ObjectId(inserted_id)})
        created_games.append(to_serializable(created))

    # Create options if not exist
    for game in created_games:
        if db["topupoption"].count_documents({"game_id": game["id"]}) == 0:
            presets = [
                {"title": "86 Diamonds", "amount": 1.59, "credits": 86},
                {"title": "172 Diamonds", "amount": 3.09, "credits": 172},
                {"title": "257 Diamonds", "amount": 4.59, "credits": 257},
                {"title": "500 Diamonds", "amount": 8.99, "credits": 500},
            ]
            for p in presets:
                create_document(
                    "topupoption",
                    {"game_id": game["id"], **p}
                )

    return {"games": created_games}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
