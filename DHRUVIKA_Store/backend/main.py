import os, json, sqlite3, uuid
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent

# Frontend directory: check multiple possible locations
_candidates = [
    ROOT.parent / "frontend",           # ../frontend (local dev layout)
    ROOT / "frontend",                  # ./frontend (same-dir layout)
    Path(os.getenv("FRONTEND_DIR", "")) if os.getenv("FRONTEND_DIR") else None,
]
PROJECT = ROOT.parent
FRONTEND_DIR: Optional[Path] = None
for _c in _candidates:
    if _c and Path(_c).is_dir():
        FRONTEND_DIR = Path(_c)
        break

load_dotenv(ROOT / ".env")

from odoo_client import odoo_client

DB_PATH = ROOT / "cheersagar.db"
app = FastAPI(title="Cheer Sagar Store API", version="1.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PRODUCTS = [
    {"id":"dhruvika-500","name":"Dhruvika Organic Jaggery Powder","subtitle":"Nature Sweetness — 100% Natural, Chemical Free","weight":"500 g","price":149,"compare_at":179,"description":"Dhruvika Organic Jaggery Powder delivers pure nature sweetness. Made with 100% natural sugarcane using a chemical-free process and containing zero added sugar. An ideal healthy replacement for white sugar in chai, desserts, baking, and daily cooking.","image":"/assets/product.png","tag":"BESTSELLER"},
    {"id":"dhruvika-1kg","name":"Dhruvika Organic Jaggery Powder","subtitle":"Nature Sweetness — 100% Natural (1 KG)","weight":"1 kg","price":269,"compare_at":319,"description":"Dhruvika Organic Jaggery Powder 1 kg pack. 100% Natural Jaggery with chemical-free processing and no added sugar. Store in a cool, dry place.","image":"/assets/product.png","tag":"1 KG PACK"},
    {"id":"dhruvika-combo","name":"Dhruvika Organic Jaggery Powder (Pack of 2)","subtitle":"Nature Sweetness — Value Duo (2 × 500 g)","weight":"2 × 500 g","price":279,"compare_at":358,"description":"Dhruvika Organic Jaggery Powder 2 × 500 g bundle. Pure nature sweetness, 100% natural jaggery, chemical free and no added sugar.","image":"/assets/product.png","tag":"SAVE MORE"}
]

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, customer_name TEXT NOT NULL, email TEXT NOT NULL,
            phone TEXT NOT NULL, address TEXT NOT NULL, city TEXT NOT NULL,
            postal_code TEXT NOT NULL, items_json TEXT NOT NULL, amount_paise INTEGER NOT NULL,
            payment_method TEXT NOT NULL, payment_status TEXT NOT NULL, utr_number TEXT,
            odoo_order_id TEXT, odoo_sync_status TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        try:
            con.execute("ALTER TABLE orders ADD COLUMN utr_number TEXT")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE orders ADD COLUMN odoo_order_id TEXT")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE orders ADD COLUMN odoo_sync_status TEXT")
        except Exception:
            pass
        con.execute("""CREATE TABLE IF NOT EXISTS order_items (
            order_id TEXT, product_id TEXT, quantity INTEGER, unit_price INTEGER
        )""")
init_db()

class Item(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=20)

class Checkout(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    email: str
    phone: str = Field(min_length=8, max_length=20)
    address: str = Field(min_length=5, max_length=300)
    city: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=5, max_length=10)
    items: list[Item]
    payment_method: str = "upi"
    utr_number: Optional[str] = None

class PaymentConfirm(BaseModel):
    utr_number: str = Field(min_length=4, max_length=50)

def price_cart(items):
    if not items:
        raise HTTPException(400, "Your cart is empty.")
    by_id = {p["id"]: p for p in PRODUCTS}
    lines, total = [], 0
    for item in items:
        p = by_id.get(item.product_id)
        if not p: raise HTTPException(400, f"Unknown product: {item.product_id}")
        line_total = p["price"] * item.quantity
        total += line_total
        lines.append({"product_id":p["id"],"name":p["name"],"weight":p["weight"],"quantity":item.quantity,"unit_price":p["price"],"line_total":line_total})
    return lines, total

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "Cheer Sagar Store API",
        "odoo_domain": os.getenv("ODOO_URL", "https://cheersagar.odoo.com")
    }

@app.get("/api/products")
def products():
    return PRODUCTS

@app.get("/api/merchant-info")
def merchant_info():
    phone = os.getenv("MERCHANT_PHONE", "9955303969")
    upi_id = os.getenv("MERCHANT_UPI_ID", "9955303969@upi")
    name = os.getenv("MERCHANT_NAME", "Cheer Sagar")
    odoo_url = os.getenv("ODOO_URL", "https://cheersagar.odoo.com")
    return {
        "store_name": name,
        "phone": phone,
        "upi_id": upi_id,
        "whatsapp": phone,
        "odoo_domain": odoo_url
    }

# ----------------- Odoo Integration Endpoints -----------------

@app.get("/api/odoo/status")
def odoo_status():
    """Returns Odoo connection status, domain info, and order sync metrics."""
    test_res = odoo_client.test_connection()
    with db() as con:
        total_orders = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        synced_orders = con.execute("SELECT COUNT(*) FROM orders WHERE odoo_sync_status='synced'").fetchone()[0]
        pending_orders = con.execute("SELECT COUNT(*) FROM orders WHERE odoo_sync_status!='synced' OR odoo_sync_status IS NULL").fetchone()[0]
    return {
        "target_domain": "cheersagar.odoo.com",
        "odoo_url": odoo_client.url,
        "database": odoo_client.db,
        "is_configured": odoo_client.is_configured(),
        "connection_test": test_res,
        "orders_summary": {
            "total": total_orders,
            "synced_to_odoo": synced_orders,
            "pending_or_local": pending_orders
        }
    }

@app.post("/api/odoo/test")
def test_odoo():
    """Explicitly test Odoo XML-RPC connection."""
    return odoo_client.test_connection()

@app.post("/api/odoo/sync-order/{order_id}")
def sync_order_to_odoo(order_id: str):
    """Manually sync a local order to Odoo ERP."""
    with db() as con:
        row = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Order not found")
    data = dict(row)
    items = json.loads(data["items_json"])
    res = odoo_client.create_sale_order(
        order_id=order_id,
        customer_name=data["customer_name"],
        email=data["email"],
        phone=data["phone"],
        address=data["address"],
        city=data["city"],
        postal_code=data["postal_code"],
        items=items,
        total_amount=data["amount_paise"] / 100.0,
        payment_method=data["payment_method"],
        payment_status=data["payment_status"],
        utr_number=data.get("utr_number")
    )
    with db() as con:
        con.execute(
            "UPDATE orders SET odoo_order_id=?, odoo_sync_status=? WHERE id=?",
            (res.get("odoo_order_name"), res.get("status", "error"), order_id)
        )
    return res

# ----------------- Order Management Endpoints -----------------

@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    with db() as con:
        row = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not row: raise HTTPException(404, "Order not found")
    data = dict(row)
    data["items"] = json.loads(data.pop("items_json"))
    return data

@app.post("/api/orders/{order_id}/confirm-payment")
def confirm_payment(order_id: str, payload: PaymentConfirm):
    with db() as con:
        row = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Order not found")
        con.execute("UPDATE orders SET payment_status='payment_submitted', utr_number=? WHERE id=?", (payload.utr_number.strip(), order_id))
    
    # Try updating Odoo if credentials exist
    if odoo_client.is_configured() and row["odoo_order_id"]:
        try:
            # We can post a chatter message to the sale order in Odoo
            so_name = row["odoo_order_id"]
            so_ids = odoo_client.execute("sale.order", "search", [[["name", "=", so_name]]], {"limit": 1})
            if so_ids:
                odoo_client.execute("sale.order", "message_post", [so_ids[0]], {
                    "body": f"Payment submitted via UPI. Customer UTR / Ref Number: <b>{payload.utr_number.strip()}</b>"
                })
        except Exception as e:
            print(f"[Odoo Payment Note Warning] {e}")

    return {"status": "ok", "order_id": order_id, "message": "Payment confirmation received. We are verifying your order."}

@app.post("/api/checkout")
def checkout(payload: Checkout):
    lines, total = price_cart(payload.items)
    if payload.payment_method not in ("upi", "online", "demo"):
        raise HTTPException(400, "Unsupported payment method.")
    merchant_phone = os.getenv("MERCHANT_PHONE", "9955303969")
    merchant_upi_id = os.getenv("MERCHANT_UPI_ID", "9955303969@upi")
    merchant_name = os.getenv("MERCHANT_NAME", "Cheer Sagar")
    key_id, key_secret = os.getenv("RAZORPAY_KEY_ID",""), os.getenv("RAZORPAY_KEY_SECRET","")
    configured = key_id.startswith("rzp_") and key_secret and "replace_me" not in key_secret
    order_id = "CS" + uuid.uuid4().hex[:12].upper()
    razorpay_order_id, status = None, "upi_pending" if payload.payment_method == "upi" else "demo_pending"
    if payload.payment_method == "online" and configured:
        try:
            import razorpay
            client = razorpay.Client(auth=(key_id, key_secret))
            rp_order = client.order.create({"amount": total * 100, "currency":"INR", "receipt":order_id, "notes":{"store":merchant_name}})
            razorpay_order_id, status = rp_order["id"], "payment_pending"
        except Exception as exc:
            raise HTTPException(502, "Payment gateway could not create an order. Check Razorpay keys and server logs.")
    
    # Attempt automatic sync to Odoo (cheersagar.odoo.com)
    odoo_order_ref = None
    odoo_sync_status = "pending_configuration"
    if os.getenv("ODOO_AUTO_SYNC", "true").lower() == "true":
        try:
            odoo_res = odoo_client.create_sale_order(
                order_id=order_id,
                customer_name=payload.customer_name,
                email=payload.email,
                phone=payload.phone,
                address=payload.address,
                city=payload.city,
                postal_code=payload.postal_code,
                items=lines,
                total_amount=total,
                payment_method=payload.payment_method,
                payment_status=status,
                utr_number=payload.utr_number
            )
            odoo_sync_status = odoo_res.get("status", "pending_configuration")
            odoo_order_ref = odoo_res.get("odoo_order_name")
        except Exception as exc:
            print(f"[Odoo Sync Warning] {exc}")
            odoo_sync_status = "error"

    with db() as con:
        con.execute("""INSERT INTO orders (
            id,customer_name,email,phone,address,city,postal_code,items_json,amount_paise,
            payment_method,payment_status,utr_number,odoo_order_id,odoo_sync_status
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            order_id,payload.customer_name,payload.email,payload.phone,payload.address,
            payload.city,payload.postal_code,json.dumps(lines),total*100,payload.payment_method,
            status,payload.utr_number,odoo_order_ref,odoo_sync_status
        ))
        for line in lines:
            con.execute("INSERT INTO order_items VALUES (?,?,?,?)",(order_id,line["product_id"],line["quantity"],line["unit_price"]))
    
    upi_intent = f"upi://pay?pa={merchant_upi_id}&pn={merchant_name.replace(' ', '%20')}&am={total}&cu=INR&tn={order_id}"
    return {
        "order_id": order_id,
        "amount": total,
        "currency": "INR",
        "items": lines,
        "payment_method": payload.payment_method,
        "payment_status": status,
        "merchant_phone": merchant_phone,
        "merchant_upi_id": merchant_upi_id,
        "merchant_name": merchant_name,
        "upi_intent": upi_intent,
        "razorpay_order_id": razorpay_order_id,
        "razorpay_key_id": key_id if razorpay_order_id else None,
        "demo_mode": payload.payment_method == "demo" or (payload.payment_method == "online" and not razorpay_order_id),
        "odoo_domain": "cheersagar.odoo.com",
        "odoo_order_ref": odoo_order_ref,
        "odoo_sync_status": odoo_sync_status,
        "message": "Order created. Please complete payment."
    }

# Serve the static frontend — only mount if the folder actually exists.
if FRONTEND_DIR and FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

    @app.get("/")
    def home():
        index = FRONTEND_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(404, "index.html not found in frontend directory.")
else:
    import warnings
    warnings.warn(
        f"[CheerSagar] Frontend directory not found (checked: {_candidates}). "
        "Static files and homepage will NOT be served. "
        "Set FRONTEND_DIR env var to the correct path if needed.",
        RuntimeWarning
    )

    @app.get("/")
    def home_fallback():
        return {
            "service": "Cheer Sagar Store API",
            "status": "running",
            "note": "Frontend not found. Set FRONTEND_DIR or run from the correct working directory.",
            "api_docs": "/docs"
        }
