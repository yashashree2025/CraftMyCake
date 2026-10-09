from database.mongodb import users_collection

data = {
    "name":"Yashashree",
    "email":"test@gmail.com"
}

users_collection.insert_one(data)

print("Data Inserted Successfully")