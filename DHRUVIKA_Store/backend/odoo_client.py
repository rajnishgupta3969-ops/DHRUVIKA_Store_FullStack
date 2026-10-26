import os
import xmlrpc.client
from typing import Dict, Any, Optional, List

class OdooClient:
    """
    Odoo XML-RPC Client for Cheer Sagar Store.
    Connects to Odoo instance (e.g., https://cheersagar.odoo.com)
    and synchronizes customers, sales orders, and products.
    """
    def __init__(
        self,
        url: Optional[str] = None,
        db: Optional[str] = None,
        username: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.url = (url or os.getenv("ODOO_URL", "https://cheersagar.odoo.com")).rstrip("/")
        self.db = db or os.getenv("ODOO_DB", "cheersagar")
        self.username = username or os.getenv("ODOO_USERNAME", "")
        self.api_key = api_key or os.getenv("ODOO_API_KEY", "")
        self._uid = None

    def is_configured(self) -> bool:
        """Check if required credentials are present."""
        return bool(
            self.url
            and self.db
            and self.username
            and self.api_key
            and "@" in self.username
            and "example.com" not in self.username
        )

    def authenticate(self) -> Optional[int]:
        """Authenticate with Odoo and return user ID (uid)."""
        if not self.is_configured():
            return None
        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
            uid = common.authenticate(self.db, self.username, self.api_key, {})
            if uid:
                self._uid = uid
                return uid
        except Exception as e:
            print(f"[Odoo] Authentication error on {self.url} (db: {self.db}): {e}")
        return None

    def execute(self, model: str, method: str, *args, **kwargs):
        """Execute a method on an Odoo model via XML-RPC."""
        if not self._uid:
            self.authenticate()
        if not self._uid:
            raise RuntimeError(
                f"Odoo authentication failed for {self.username} on {self.url} (db: {self.db}). "
                "Please verify your ODOO_URL, ODOO_DB, ODOO_USERNAME, and ODOO_API_KEY."
            )
        models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)
        return models.execute_kw(self.db, self._uid, self.api_key, model, method, list(args), kwargs)

    def test_connection(self) -> Dict[str, Any]:
        """Test the connection and return status info."""
        domain_name = "cheersagar.odoo.com" if "cheersagar" in self.url else self.url
        if not self.is_configured():
            return {
                "success": False,
                "configured": False,
                "domain": domain_name,
                "url": self.url,
                "db": self.db,
                "message": (
                    f"Odoo credentials not configured in backend/.env yet. "
                    f"Target domain: {domain_name}. Please set ODOO_USERNAME and ODOO_API_KEY."
                )
            }
        try:
            uid = self.authenticate()
            if uid:
                user_info = self.execute("res.users", "read", [uid], {"fields": ["name", "company_id"]})
                company_name = user_info[0]["company_id"][1] if user_info and user_info[0].get("company_id") else "Cheer Sagar"
                return {
                    "success": True,
                    "configured": True,
                    "uid": uid,
                    "domain": domain_name,
                    "company_name": company_name,
                    "user_name": user_info[0].get("name", self.username),
                    "message": f"Successfully connected to Odoo domain '{domain_name}'!"
                }
            else:
                return {
                    "success": False,
                    "configured": True,
                    "domain": domain_name,
                    "message": f"Authentication failed on {self.url} with database '{self.db}'. Check email and API key."
                }
        except Exception as e:
            return {
                "success": False,
                "configured": True,
                "domain": domain_name,
                "error": str(e),
                "message": f"Could not reach Odoo at {self.url}: {str(e)}"
            }

    def find_or_create_partner(self, name: str, email: str, phone: str, street: str, city: str, zip_code: str) -> int:
        """Find existing customer by email or phone, or create a new partner in Odoo."""
        partner_ids = []
        if email:
            partner_ids = self.execute("res.partner", "search", [[["email", "=", email.strip()]]], {"limit": 1})
        if not partner_ids and phone:
            partner_ids = self.execute("res.partner", "search", [[["phone", "=", phone.strip()]]], {"limit": 1})

        if partner_ids:
            partner_id = partner_ids[0]
            try:
                self.execute("res.partner", "write", [partner_id], {
                    "street": street,
                    "city": city,
                    "zip": zip_code,
                    "phone": phone
                })
            except Exception:
                pass
            return partner_id

        partner_id = self.execute("res.partner", "create", [{
            "name": name,
            "email": email,
            "phone": phone,
            "street": street,
            "city": city,
            "zip": zip_code,
            "customer_rank": 1,
            "comment": "Created via Cheer Sagar Store (Dhruvika)"
        }])
        return partner_id

    def find_or_create_product(self, product_code: str, name: str, price: float) -> Optional[int]:
        """Find product by internal code or name, or create it in Odoo."""
        try:
            prod_ids = self.execute("product.product", "search", [[["default_code", "=", product_code]]], {"limit": 1})
            if not prod_ids:
                prod_ids = self.execute("product.product", "search", [[["name", "ilike", name]]], {"limit": 1})
            if prod_ids:
                return prod_ids[0]

            new_id = self.execute("product.product", "create", [{
                "name": name,
                "default_code": product_code,
                "list_price": price,
                "type": "consu"
            }])
            return new_id
        except Exception as e:
            print(f"[Odoo] Product lookup/creation error: {e}")
            return None

    def create_sale_order(
        self,
        order_id: str,
        customer_name: str,
        email: str,
        phone: str,
        address: str,
        city: str,
        postal_code: str,
        items: List[Dict[str, Any]],
        total_amount: float,
        payment_method: str = "upi",
        payment_status: str = "pending",
        utr_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Sales Order in Odoo."""
        if not self.is_configured():
            return {
                "success": False,
                "status": "pending_configuration",
                "message": "Odoo is not configured yet. Order saved locally."
            }

        try:
            partner_id = self.find_or_create_partner(
                name=customer_name,
                email=email,
                phone=phone,
                street=address,
                city=city,
                zip_code=postal_code
            )

            order_lines = []
            for item in items:
                p_code = item.get("product_id", "dhruvika")
                p_name = item.get("name", "Dhruvika Organic Jaggery Powder")
                p_qty = float(item.get("quantity", 1))
                p_price = float(item.get("unit_price", 0))
                weight = item.get("weight", "")

                prod_id = self.find_or_create_product(p_code, p_name, p_price)
                line_data = {
                    "name": f"{p_name} ({weight}) - Qty {int(p_qty)}" if weight else p_name,
                    "product_uom_qty": p_qty,
                    "price_unit": p_price,
                }
                if prod_id:
                    line_data["product_id"] = prod_id
                order_lines.append((0, 0, line_data))

            note = (
                f"Cheer Sagar Store Order: {order_id}\n"
                f"Customer Phone: {phone}\n"
                f"Delivery Address: {address}, {city} - {postal_code}\n"
                f"Payment Method: {payment_method.upper()}\n"
                f"Payment Status: {payment_status}"
            )
            if utr_number:
                note += f"\nUPI Transaction UTR / Ref: {utr_number}"

            so_data = {
                "partner_id": partner_id,
                "client_order_ref": order_id,
                "note": note,
                "order_line": order_lines
            }

            so_id = self.execute("sale.order", "create", [so_data])
            so_record = self.execute("sale.order", "read", [so_id], {"fields": ["name", "amount_total"]})
            odoo_order_name = so_record[0]["name"] if so_record else f"SO-{so_id}"

            return {
                "success": True,
                "status": "synced",
                "odoo_order_id": so_id,
                "odoo_order_name": odoo_order_name,
                "partner_id": partner_id,
                "message": f"Order {order_id} successfully created in Odoo as {odoo_order_name}"
            }
        except Exception as e:
            print(f"[Odoo] Error creating sale order: {e}")
            return {
                "success": False,
                "status": "error",
                "error": str(e),
                "message": f"Failed to sync order with Odoo: {str(e)}"
            }

odoo_client = OdooClient()

