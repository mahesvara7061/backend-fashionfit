from flask import g
from pymongo import MongoClient

exchange_rate = 25400 # USD to VND

def get_db(db_name="FashionFit"):
    """
    Kết nối với MongoDB và trả về đối tượng database.
    """
    if "client" not in g:
        g.client = MongoClient("mongodb+srv://mahesvara:2004@products.i9zzz.mongodb.net/")
    return g.client[db_name]

def close_db(exception):
    """
    Đóng kết nối MongoDB khi kết thúc ứng dụng.
    """
    db_client = g.pop("client", None)
    if db_client is not None:
        db_client.close()
