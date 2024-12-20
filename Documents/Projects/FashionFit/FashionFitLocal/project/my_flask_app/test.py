import requests

BASE_URL = "https://services.giaohangtietkiem.vn"
API_TOKEN = "IDlMNSes2cRE43PckpfXqvZ9PeQJAHlnjkgoki"
PARTNER_CODE = "S22801838"

# Hàm để hủy đơn hàng
def cancel_order(order_code):
    url = f'{BASE_URL}/services/shipment/cancel/{order_code}'
    headers = {
        'Token': API_TOKEN,
        'X-Client-Source': PARTNER_CODE,
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers)
    return response.json()

label = "S22801838.SGP95-S4.1367508829"
response = cancel_order(label)
print(response)
