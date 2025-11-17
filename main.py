import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId
import base64

from database import db, create_document, get_documents
from schemas import WalletStyle, Upload as UploadSchema, Order

app = FastAPI(title="Laser Engraved Slim Wallets API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "wallets-api"}


@app.get("/api/styles")
def list_styles():
    """Return available wallet styles (seed minimal defaults if empty)."""
    try:
        styles = get_documents("walletstyle")
        if not styles:
            # Seed a few default styles if collection is empty
            seeds = [
                WalletStyle(
                    title="Carbon Fiber Slim Wallet",
                    description="Durable carbon fiber plates with RFID blocking.",
                    price=59.0,
                    images=[
                        "https://images.unsplash.com/photo-1585386959984-a4155223162d?auto=format&fit=crop&w=1200&q=60",
                    ],
                    finishes=["Matte Black", "Gunmetal", "Silver"],
                ),
                WalletStyle(
                    title="Aluminum Slim Wallet",
                    description="Lightweight anodized aluminum construction.",
                    price=49.0,
                    images=[
                        "https://images.unsplash.com/photo-1512496015851-a90fb38ba796?auto=format&fit=crop&w=1200&q=60",
                    ],
                    finishes=["Matte Black", "Navy", "Forest"],
                ),
                WalletStyle(
                    title="Titanium Slim Wallet",
                    description="Premium titanium with sleek edges.",
                    price=89.0,
                    images=[
                        "https://images.unsplash.com/photo-1562184552-1e86cae0b2d9?auto=format&fit=crop&w=1200&q=60",
                    ],
                    finishes=["Raw", "Stonewash", "Black Ti"],
                ),
            ]
            for s in seeds:
                create_document("walletstyle", s)
            styles = get_documents("walletstyle")
        # Convert ObjectId to string if present
        for s in styles:
            if "_id" in s:
                s["id"] = str(s.pop("_id"))
        return {"styles": styles}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/upload")
async def upload_art(file: UploadFile = File(...)):
    """Accept an image upload and store as base64 in DB, return upload id."""
    try:
        content = await file.read()
        data_b64 = base64.b64encode(content).decode("utf-8")
        doc = UploadSchema(
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            size=len(content),
            data_b64=data_b64,
        )
        upload_id = create_document("upload", doc)
        return {"upload_id": upload_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class CartItemIn(BaseModel):
    product_id: str
    quantity: int = 1
    finish: Optional[str] = None
    engraving_text: Optional[str] = None
    upload_id: Optional[str] = None


class CustomerIn(BaseModel):
    name: str
    email: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str


class CheckoutIn(BaseModel):
    items: List[CartItemIn]
    customer: CustomerIn


@app.post("/api/checkout")
def checkout(payload: CheckoutIn):
    """
    Create a simple order record. Payment is mocked for now (status pending).
    """
    try:
        # Calculate totals based on DB product prices
        items_full = []
        subtotal = 0.0
        for item in payload.items:
            prod = db["walletstyle"].find_one({"_id": ObjectId(item.product_id)})
            if not prod:
                raise HTTPException(status_code=404, detail=f"Product not found: {item.product_id}")
            price = float(prod.get("price", 0)) * int(item.quantity)
            subtotal += price
            items_full.append({
                "product_id": item.product_id,
                "title": prod.get("title"),
                "price_each": float(prod.get("price", 0)),
                "quantity": int(item.quantity),
                "finish": item.finish,
                "engraving_text": item.engraving_text,
                "upload_id": item.upload_id,
            })
        shipping = 5.0 if subtotal < 75 else 0.0
        total = round(subtotal + shipping, 2)

        order_doc = Order(
            items=items_full,  # type: ignore
            customer=payload.customer.model_dump(),  # type: ignore
            subtotal=round(subtotal, 2),
            shipping=shipping,
            total=total,
            status="pending",
        )
        order_id = create_document("order", order_doc)
        return {"order_id": order_id, "status": "pending", "amount": total}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/schema")
def get_schema_info():
    """Expose basic schema info for tooling."""
    return {
        "collections": ["walletstyle", "upload", "order"],
    }


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
            response["database"] = "✅ Connected"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                response["collections"] = db.list_collection_names()
            except Exception:
                pass
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
