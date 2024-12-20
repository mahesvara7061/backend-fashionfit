import requests
from requests.auth import HTTPBasicAuth
from config import Config

BASE_URL = "https://api-m.sandbox.paypal.com" if Config.PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"

# Lấy Access Token
def get_access_token():
    url = f"{BASE_URL}/v1/oauth2/token"
    headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}
    response = requests.post(url, headers=headers, data=data, auth=HTTPBasicAuth(Config.PAYPAL_CLIENT_ID, Config.PAYPAL_SECRET))
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Unable to fetch access token: {response.json()}")

# Tạo đơn hàng
def create_order(amount, currency, return_url, cancel_url):
    access_token = get_access_token()
    url = f"{BASE_URL}/v2/checkout/orders"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": currency,
                "value": amount
            }
        }],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url
        }
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        order = response.json()
        approval_url = next(link["href"] for link in order["links"] if link["rel"] == "approve")
        return {"order_id": order["id"], "approval_url": approval_url}
    else:
        raise Exception(f"Unable to create order: {response.json()}")

# Thực hiện thanh toán
def capture_order(order_id):
    access_token = get_access_token()
    url = f"{BASE_URL}/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Unable to capture order: {response.json()}")
