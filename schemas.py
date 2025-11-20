"""
Database Schemas for the Game Top-up App

Each Pydantic model below represents a MongoDB collection. The collection
name is the lowercase of the class name (e.g., Game -> "game").
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class Game(BaseModel):
    """
    Games available for top-up
    Collection: "game"
    """
    name: str = Field(..., description="Game display name")
    code: str = Field(..., description="Unique code identifier for the game (e.g., 'mlbb')")
    image: Optional[str] = Field(None, description="Image URL for the game banner/icon")
    publisher: Optional[str] = Field(None, description="Game publisher name")


class Topupoption(BaseModel):
    """
    Top-up denominations/options for a specific game
    Collection: "topupoption"
    """
    game_id: str = Field(..., description="Related game id (as string)")
    title: str = Field(..., description="Display title (e.g., '86 Diamonds')")
    amount: float = Field(..., ge=0, description="Price in USD")
    credits: int = Field(..., ge=1, description="In-game credits granted")


class Order(BaseModel):
    """
    Purchase orders created by users
    Collection: "order"
    """
    game_id: str = Field(..., description="Game id")
    option_id: str = Field(..., description="Topup option id")
    player_id: str = Field(..., description="Player/User ID in the game")
    region: Optional[str] = Field(None, description="Optional region/server")
    payment_method: str = Field(..., description="Payment channel chosen by the user")
    status: str = Field("pending", description="Order status: pending|paid|delivered|failed|cancelled")
    amount: float = Field(..., ge=0, description="Amount to pay")
    credits: int = Field(..., ge=1, description="In-game credits to deliver")
