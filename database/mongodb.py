from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["CraftMyCakeDB"]

users_collection = db["users"]
cakes_collection = db["cakes"]
cart_collection = db["cart"]
orders_collection = db["orders"]
custom_cakes_collection = db["custom_cakes"]
reviews_collection = db["reviews"]
contacts_collection = db["contacts"]
custom_requests_collection = db["custom_requests"]
favorites_collection = db["favorites"]
addresses_collection = db["addresses"]
vendors_collection = db["vendors"]