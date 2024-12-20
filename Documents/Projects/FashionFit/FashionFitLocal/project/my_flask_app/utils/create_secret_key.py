import secrets

# Tạo secret key an toàn
secret_key = secrets.token_hex(32)  # Chuỗi 32 bytes
print(secret_key)
