# Cheer Sagar — Dhruvika Store

Responsive full-stack e-commerce starter for Cheer Sagar featuring product Dhruvika.

## Features
- Premium natural storefront, product detail section, responsive navigation
- Product pack-size selector, cart quantity controls, subtotal and delivery estimate
- Checkout form with customer and delivery details
- FastAPI backend, SQLite product/order storage, order status API
- Razorpay Checkout integration scaffold for UPI/cards/netbanking
- Demo mode: place a test order without collecting a real payment
- API health and product endpoints

## Run on Windows
1. Install Python 3.10+.
2. Open this folder in VS Code.
3. Double-click `run.bat`, or in PowerShell run:
   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
4. Open http://127.0.0.1:8000

The backend serves the frontend and API from the same origin.

## Odoo ERP Integration (Domain: cheersagar.odoo.com)
The store connects to Odoo ERP for automated order and customer synchronization.

### 1. Create your Odoo Domain:
1. Visit [https://www.odoo.com/trial](https://www.odoo.com/trial).
2. Select **Website**, **eCommerce**, and **Sales** apps.
3. In **Company Name**, enter `Cheersagar`.
4. Odoo will assign the domain: `https://cheersagar.odoo.com`.
5. Enter your name, email, and phone (`9955303969`), then click **Start Now**.
6. Verify your email to activate the account.

### 2. Connect Store to Odoo:
1. Log in to `https://cheersagar.odoo.com`.
2. Click top-right avatar > **My Profile** > **Account Security**.
3. Under **Developer API Keys**, click **New API Key**, and copy the generated key.
4. Open `backend/.env` and update:
   ```env
   ODOO_URL=https://cheersagar.odoo.com
   ODOO_DB=cheersagar
   ODOO_USERNAME=your_odoo_email@example.com
   ODOO_API_KEY=your_odoo_api_key
   ODOO_AUTO_SYNC=true
   ```
5. Test live connection at `http://127.0.0.1:8000/api/odoo/status` or click **⚡ Odoo ERP** in the website footer.

## Payment setup
- **Direct UPI (9955303969):** Customers pay directly to phone number `9955303969` via dynamic UPI QR code, mobile UPI intent links (Google Pay, PhonePe, Paytm, BHIM), and submit payment confirmation/UTR or WhatsApp proof to `+91 9955303969`.
- To customize the UPI handle, edit `backend/.env`:
  ```env
  MERCHANT_PHONE=9955303969
  MERCHANT_UPI_ID=9955303969@upi
  MERCHANT_NAME=Cheer Sagar
  ```
- **Optional Razorpay Gateway:** Set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `backend/.env` for credit/debit card and netbanking support.

## Before launch
Replace demo product photography/pricing/claims with verified brand assets and actual product information. Add shipping policy, privacy policy, terms, refund policy, GST/business details, email/SMS notifications, rate limiting, webhook signature verification, and production hosting/HTTPS. The included integration is a starter and is not a substitute for production payment verification.
