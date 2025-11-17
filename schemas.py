"""
Database Schemas for Laser-Engraved Slim Wallets Store

Each Pydantic model represents a collection in MongoDB. The collection name
is the lowercase class name (e.g., WalletStyle -> "walletstyle").
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class WalletStyle(BaseModel):
    """
    Wallet styles available for purchase
    Collection: "walletstyle"
    """
    title: str = Field(..., description="Display name of the wallet style")
    description: Optional[str] = Field(None, description="Short description")
    price: float = Field(..., ge=0, description="Base price USD")
    images: List[str] = Field(default_factory=list, description="Image URLs for gallery")
    finishes: List[str] = Field(default_factory=lambda: ["Matte Black", "Gunmetal", "Silver"], description="Available finishes")
    in_stock: bool = Field(True, description="Whether available for purchase")

class Upload(BaseModel):
    """
    Uploaded artwork for engraving
    Collection: "upload"
    """
    filename: str
    content_type: str
    size: int
    data_b64: str = Field(..., description="Base64-encoded file contents")

class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1)
    finish: Optional[str] = None
    engraving_text: Optional[str] = None
    upload_id: Optional[str] = None

class Customer(BaseModel):
    name: str
    email: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str

class Order(BaseModel):
    """
    Orders placed by customers
    Collection: "order"
    """
    items: List[CartItem]
    customer: Customer
    subtotal: float = Field(..., ge=0)
    shipping: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    status: str = Field("pending", description="pending|processing|completed|cancelled")
    notes: Optional[str] = None
