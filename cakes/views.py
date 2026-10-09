from django.shortcuts import render,redirect
from database.mongodb import (
    users_collection,
    vendors_collection,
    cakes_collection,
    orders_collection,
    custom_requests_collection,
    favorites_collection,
    contacts_collection,
    reviews_collection
)

from datetime import date
from django.contrib import messages
from bson.objectid import ObjectId
def home(request):
    return render(request, 'home.html')
def signup(request):

    if request.method == "POST":

        fullname = request.POST.get("fullname")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        role = request.POST.get("role")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Phone Validation
        if not phone.isdigit() or len(phone) != 10:

            messages.error(
                request,
                "❌ Phone number must be exactly 10 digits"
            )

            return render(
                request,
                'signup.html'
            )

        # Password Match Validation
        if password != confirm_password:

            messages.error(
                request,
                "❌ Passwords do not match"
            )

            return render(
                request,
                'signup.html'
            )

        # Email Exists Validation
        existing_user = users_collection.find_one(
            {"email": email}
        )

        if existing_user:

            messages.error(
                request,
                "❌ Email already registered"
            )

            return render(
                request,
                'signup.html'
            )

        # Save User in MongoDB
        users_collection.insert_one({

            "fullname": fullname,
            "email": email,
            "phone": phone,
            "role": role,
            "password": password

        })

        messages.success(
            request,
            "🎉 Signup Successful! Please Login."
        )

        return redirect('login')

    return render(
        request,
        'signup.html'
    )

from django.shortcuts import render, redirect
from django.contrib import messages

def login(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        user = users_collection.find_one({
            "email": email
        })

        # Email not found
        if not user:

            messages.error(
                request,
                "Email not registered."
            )

            return render(request, "login.html")

        # Wrong Password
        if user["password"] != password:

            messages.error(
                request,
                "Incorrect Password."
            )

            return render(request, "login.html")

        # Save Session
        request.session["user_email"] = user["email"]
        request.session["user_name"] = user["fullname"]
        request.session["user_role"] = user["role"]

        remember_me = request.POST.get("remember_me")

        if remember_me:
            request.session.set_expiry(1209600)
        else:
            request.session.set_expiry(0)

        role = user.get("role")

        if role == "customer":

            return redirect("shop")

        elif role == "vendor":

            return redirect("vendor_dashboard")

        elif role == "admin":

            return redirect("admin_dashboard")

        else:

            messages.error(
                request,
                "Invalid User Role."
            )

            return render(request, "login.html")

    return render(request, "login.html")

def shop(request):
    if not request.session.get("user_email"):
        return redirect("login")
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    search = {}

    if query:
        search["$or"] = [
            {"cake_name": {"$regex": query, "$options": "i"}},
            {"flavor": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}},
            {"weight": {"$regex": query, "$options": "i"}}
        ]

    if category and category != "All":
        search["category"] = category

    cakes = list(cakes_collection.find(search))

    email = request.session.get("user_email")

    # Default: no favorites
    favorite_ids = []

    if email:

        favorites = favorites_collection.find({
            "user_email": email
        })

        favorite_ids = [fav["cake_id"] for fav in favorites]

    for cake in cakes:

        cake["id"] = str(cake["_id"])

        if cake["id"] in favorite_ids:
            cake["is_favorite"] = True
        else:
            cake["is_favorite"] = False

    return render(
        request,
        "shop.html",
        {
            "cakes": cakes,
            "query": query,
            "category": category
        }
    )

def cake_details(request, cake_id):

    cake = cakes_collection.find_one({
        "_id": ObjectId(cake_id)
    })

    if not cake:
        messages.error(request, "Cake not found")
        return redirect("shop")

    # Convert MongoDB _id to normal id
    cake["id"] = str(cake["_id"])

    return render(
        request,
        "cake_details.html",
        {
            "cake": cake
        }
    )
from datetime import date
from django.contrib import messages
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage

def customize_cake(request):

    if request.method == "POST":

        image = request.FILES.get("reference_image")   
        image_path = ""

        if image:
            image_path = default_storage.save(
                f"custom_cakes/{image.name}",
                image
            )

        request_data = {

            "customer_name": request.session.get("user_name"),
            "customer_email": request.session.get("user_email"),

            "occasion": request.POST.get("occasion"),
            "shape": request.POST.get("shape"),
            "flavor": request.POST.get("flavor"),
            "weight": request.POST.get("weight"),
            "theme": request.POST.get("theme"),
            "budget": request.POST.get("budget"),
            "message": request.POST.get("message"),
            "delivery_date": request.POST.get("delivery_date"),
            "delivery_time": request.POST.get("delivery_time"),

            "reference_image": image_path,

            "status": "Pending",

            "vendor_price": "",

            "created_at": str(date.today())
        }

        custom_requests_collection.insert_one(request_data)

        messages.success(
            request,
            "Custom cake request submitted successfully."
        )

        return redirect("customize_cake")

    return render(
        request,
        "customize_cake.html"
    )
def my_custom_requests(request):

    email = request.session.get("user_email")

    user = users_collection.find_one({
        "email": email
    })

    requests = list(
        custom_requests_collection.find(
            {
                "customer_email": email
            }
        ).sort("_id", -1)
    )

    for req in requests:
        req["id"] = str(req["_id"])

    return render(
        request,
        "my_custom_requests.html",
        {
            "user": user,
            "requests": requests
        }
    )

def add_to_cart(request, cake_id):

    cake = cakes_collection.find_one({
        "_id": ObjectId(cake_id)
    })

    if not cake:
        return redirect("shop")

    cart = request.session.get("cart", {})

    if cake_id in cart:

        cart[cake_id]["quantity"] += 1

    else:

        cart[cake_id] = {

    "cake_name": cake["cake_name"],
    "price": cake["price"],
    "weight": cake["weight"],
    "flavor": cake["flavor"],
    "image": cake.get("image"),
    "vendor_email": cake.get("vendor_email"),
    "quantity": 1

}

    request.session["cart"] = cart

    messages.success(request, "Cake added to cart.")

    return redirect("cart")

def remove_from_cart(request, cake_id):

    cart = request.session.get("cart", {})

    if cake_id in cart:
        del cart[cake_id]

    request.session["cart"] = cart

    messages.success(
        request,
        "Cake removed from cart."
    )

    return redirect("cart")

def increase_quantity(request, cake_id):

    cart = request.session.get("cart", {})

    if cake_id in cart:
        cart[cake_id]["quantity"] += 1

    request.session["cart"] = cart

    return redirect("cart")

def decrease_quantity(request, cake_id):

    cart = request.session.get("cart", {})

    if cake_id in cart:

        if cart[cake_id]["quantity"] > 1:

            cart[cake_id]["quantity"] -= 1

        else:

            del cart[cake_id]

    request.session["cart"] = cart

    return redirect("cart")

def cart(request):

    cart = request.session.get("cart", {})

    items = []
    subtotal = 0

    for key, item in cart.items():

        item["id"] = key

        item["total"] = item["price"] * item["quantity"]

        subtotal += item["total"]

        items.append(item)

    delivery = 100 if subtotal > 0 else 0

    total = subtotal 

    return render(request, "cart.html", {

        "cart_items": items,
        "subtotal": subtotal,
        "delivery": delivery,
        "total": total

    })

def checkout(request):

    cart = request.session.get("cart", {})

    cart_items = []
    subtotal = 0

    for cake_id, item in cart.items():

        item["id"] = cake_id
        item["total"] = item["price"] * item["quantity"]

        subtotal += item["total"]

        cart_items.append(item)

    delivery = 0
    total = subtotal

    if request.method == "POST":

        # Logged in customer email
        customer_email = request.session.get("user_email")

        # Vendor email from first cart item
        vendor_email = ""

        if cart_items:
            vendor_email = cart_items[0].get("vendor_email", "")

        order = {

            "customer_name": request.POST.get("fullname"),

            "mobile": request.POST.get("mobile"),

            # IMPORTANT: Save session email instead of form email
            "email": customer_email,

            "vendor_email": vendor_email,

            "address": request.POST.get("address"),

            "city": request.POST.get("city"),

            "state": request.POST.get("state"),

            "pincode": request.POST.get("pincode"),

            "delivery_date": request.POST.get("delivery_date"),

            "delivery_time": request.POST.get("delivery_time"),

            "payment_method": request.POST.get("payment"),

            "items": cart_items,

            "subtotal": subtotal,

            "delivery": delivery,

            "total": total,

            "status": "Pending",

            "order_date": str(date.today())

        }

        result = orders_collection.insert_one(order)
        
        if cart_items and cart_items[0].get("custom_request_id"):

            custom_requests_collection.update_one(

                {
                    "_id": ObjectId(cart_items[0]["custom_request_id"])
                },

                {
                    "$set": {
                        "ordered": True
                    }
                }

            )

        request.session["cart"] = {}

        messages.success(request, "Order placed successfully!")

        return redirect("order_success", order_id=str(result.inserted_id))
    email = request.session.get("user_email")

    user = users_collection.find_one({
        "email": email
    })
    return render(
        request,
        "checkout.html",
        {
            "cart_items": cart_items,
            "subtotal": subtotal,
            "delivery": delivery,
            "total": total,
            "user": user
        }
    )

def proceed_to_payment(request, request_id):

    custom_request = custom_requests_collection.find_one(
        {
            "_id": ObjectId(request_id)
        }
    )

    if not custom_request:
        messages.error(request, "Custom cake request not found.")
        return redirect("my_custom_requests")

    # Create a cart item from the custom cake
    cart = {}

    cart["custom_cake"] = {
    "cake_name": custom_request.get("theme", "Custom Cake"),
    "occasion": custom_request.get("occasion"),
    "price": int(custom_request["vendor_price"]),
    "quantity": 1,
    "weight": custom_request["weight"],
    "flavor": custom_request["flavor"],
    "vendor_email": custom_request.get("vendor_email", ""),
    "image": custom_request.get("reference_image", "")
}

    request.session["cart"] = cart

    return redirect("checkout")

def order_success(request, order_id):

    order = orders_collection.find_one(
        {
            "_id": ObjectId(order_id)
        }
    )

    return render(
        request,
        "order_success.html",
        {
            "order": order,
            "order_id": order_id
        }
    )

def track_order(request):

    email = request.session.get("user_email")

    order = orders_collection.find_one(
        {"email": email},
        sort=[("_id", -1)]
    )

    if not order:
        messages.info(request, "No orders found.")
        return redirect("shop")

    return redirect("order_tracking", order_id=str(order["_id"]))

def order_tracking(request, order_id):

    order = orders_collection.find_one(
        {"_id": ObjectId(order_id)}
    )

    if not order:
        return redirect("my_orders")

    order["id"] = str(order["_id"])

    return render(
        request,
        "order_tracking.html",
        {
            "order": order
        }
    )

def my_orders(request):

    email = request.session.get("user_email")

    user = users_collection.find_one({
        "email": email
    })

    print("Logged in email:", email)

    orders = list(
        orders_collection.find(
            {"email": email}
        ).sort("_id", -1)
    )

    print("Orders Found:", len(orders))

    for order in orders:
        order["id"] = str(order["_id"])

    return render(
        request,
        "my_orders.html",
        {
            "user": user,
            "orders": orders
        }
    )

def profile(request):

    email = request.session.get("user_email")

    # Logged in user
    user = users_collection.find_one({
        "email": email
    })

    # User Orders
    orders = list(
        orders_collection.find({
            "email": email
        }).sort("_id", -1)
    )

    # User Favorites
    favorites = list(
        favorites_collection.find({
            "user_email": email
        })
    )

    # Current selected profile section
    section = request.GET.get("section", "home")

    return render(
        request,
        "profile.html",
        {
            "user": user,
            "orders": orders,
            "favorites": favorites,
            "favorite_count": len(favorites),
            "total_orders": len(orders),
            "section": section
        }
    )

def favorite_cakes(request):

    email = request.session.get("user_email")

    user = users_collection.find_one({
        "email": email
    })

    favorites = list(
        favorites_collection.find({
            "user_email": email
        })
    )

    return render(
        request,
        "favorite_cakes.html",
        {
            "user": user,
            "favorites": favorites
        }
    )

def saved_address(request):

    email = request.session.get("user_email")

    if not email:
        return redirect("login")

    user = users_collection.find_one({
        "email": email
    })

    if request.method == "POST":

        users_collection.update_one(

            {
                "email": email
            },

            {
                "$set": {

                    "fullname": request.POST.get("fullname"),
                    "phone": request.POST.get("phone"),
                    "address": request.POST.get("address"),
                    "city": request.POST.get("city"),
                    "state": request.POST.get("state"),
                    "pincode": request.POST.get("pincode")

                }
            }

        )

        messages.success(
            request,
            "✅ Address updated successfully."
        )

        return redirect("saved_address")

    user = users_collection.find_one({
        "email": email
    })

    return render(
        request,
        "saved_address.html",
        {
            "user": user
        }
    )

def vendor_dashboard(request):

    vendor_email = request.session.get("user_email")

    # Vendor Orders
    orders = list(
        orders_collection.find({
            "vendor_email": vendor_email
        }).sort("_id", -1)
    )

    for order in orders:
        order["id"] = str(order["_id"])

    # Pending Orders Count
    pending_orders = sum(
        1 for order in orders
        if order["status"] == "Pending"
    )

    # Pending Custom Requests
    custom_requests = list(
        custom_requests_collection.find({
            "status": "Pending"
        }).sort("_id", -1)
    )

    for req in custom_requests:
        req["id"] = str(req["_id"])

    return render(
        request,
        "vendor_dashboard.html",
        {
            "orders": orders,
            "pending_orders": pending_orders,
            "custom_requests": custom_requests,
        }
    )

def vendor_profile(request):

    email = request.session.get("user_email")

    if not email:
        return redirect("login")

    vendor = vendors_collection.find_one({
        "vendor_email": email
    })

    if request.method == "POST":

        update_data = {
            "shop_name": request.POST.get("shop_name"),
            "owner_name": request.POST.get("owner_name"),
            "phone": request.POST.get("phone"),
            "address": request.POST.get("address"),
            "city": request.POST.get("city"),
            "state": request.POST.get("state"),
            "pincode": request.POST.get("pincode"),
            "description": request.POST.get("description")
        }

        if request.FILES.get("shop_logo"):
            logo = request.FILES["shop_logo"]
            logo_path = default_storage.save("vendor_logos/" + logo.name, logo)
            update_data["shop_logo"] = logo_path

        if request.FILES.get("shop_banner"):
            banner = request.FILES["shop_banner"]
            banner_path = default_storage.save("vendor_banners/" + banner.name, banner)
            update_data["shop_banner"] = banner_path

        vendors_collection.update_one(
            {"vendor_email": email},
            {"$set": update_data}
        )

        messages.success(request, "Profile Updated Successfully.")
        return redirect("vendor_profile")

    return render(request, "vendor_profile.html", {
        "vendor": vendor
    })

def manage_cakes(request):

    vendor_email = request.session.get("user_email")

    search = request.GET.get("search", "").strip()

    query = {
        "vendor_email": vendor_email
    }

    if search:
        query["cake_name"] = {
            "$regex": search,
            "$options": "i"
        }

    cakes = list(cakes_collection.find(query))

    for cake in cakes:
        cake["id"] = str(cake["_id"])

    return render(
        request,
        "manage_cakes.html",
        {
            "cakes": cakes,
            "search": search
        }
    )

from django.core.files.storage import default_storage

def add_cake(request):

    if request.method == "POST":

        cake_name = request.POST.get("cake_name")
        price = request.POST.get("price")
        weight = request.POST.get("weight")
        flavor = request.POST.get("flavor")
        description = request.POST.get("description")
        image = request.FILES.get("image")
        category = request.POST.get("category")
        availability = request.POST.get("availability")

        image_path = None

        if image:
            image_path = default_storage.save(
                f"cakes/{image.name}",
                image
            )

        cakes_collection.insert_one({
            "cake_name": cake_name,
            "category": category,
            "price": int(price),
            "weight": weight,
            "flavor": flavor,
            "description": description,
            "image": image_path,
            "availability": availability,
            "vendor_email": request.session.get("user_email"),
            "created_at": str(date.today())
        })

        return redirect("add_cake")
    return render(request, "add_cake.html")

def delete_cake(request, cake_id):

    vendor_email = request.session.get("user_email")

    cakes_collection.delete_one({
        "_id": ObjectId(cake_id),
        "vendor_email": vendor_email
    })

    messages.success(request, "Cake deleted successfully.")

    return redirect("manage_cakes")

def edit_cake(request, cake_id):

    vendor_email = request.session.get("user_email")

    cake = cakes_collection.find_one({
        "_id": ObjectId(cake_id),
        "vendor_email": vendor_email
    })

    if not cake:
        messages.error(request, "Cake not found.")
        return redirect("manage_cakes")

    cake["id"] = str(cake["_id"])

    if request.method == "POST":

        update_data = {

            "cake_name": request.POST.get("cake_name"),
            "price": int(request.POST.get("price")),
            "weight": request.POST.get("weight"),
            "flavor": request.POST.get("flavor"),
            "description": request.POST.get("description")

        }

        image = request.FILES.get("image")

        if image:

            image_path = default_storage.save(
                f"cakes/{image.name}",
                image
            )

            update_data["image"] = image_path

        cakes_collection.update_one(

            {
                "_id": ObjectId(cake_id)
            },

            {
                "$set": update_data
            }

        )

        messages.success(request, "Cake updated successfully.")

        return redirect("manage_cakes")

    return render(
        request,
        "edit_cake.html",
        {
            "cake": cake
        }
    )
    
def vendor_orders(request):

    vendor_email = request.session.get("user_email")

    orders = list(
        orders_collection.find({
            "vendor_email": vendor_email
        })
    )

    for order in orders:
        order["id"] = str(order["_id"])

    pending = 0

    for order in orders:
        if order["status"] == "Pending":
            pending += 1

    return render(
        request,
        "vendor_orders.html",
        {
            "orders": orders,
            "pending": pending
        }
    )
def update_order_status(request, order_id):

    if request.method == "POST":

        status = request.POST.get("status")

        orders_collection.update_one(
            {
                "_id": ObjectId(order_id)
            },
            {
                "$set": {
                    "status": status
                }
            }
        )

    return redirect("vendor_orders")


def custom_requests(request):

    requests = list(

        custom_requests_collection.find(

            {
                "status": "Pending"
            }

        ).sort("_id", -1)

    )

    for req in requests:
        req["id"] = str(req["_id"])

    return render(
        request,
        "custom_requests.html",
        {
            "requests": requests
        }
    )

def update_custom_request(request, request_id):

    if request.method == "POST":

        status = request.POST.get("status")
        price = request.POST.get("price")

        update_data = {
            "status": status,
            "vendor_price": int(price),
            "vendor_email": request.session.get("user_email")   # NEW
        }

        custom_requests_collection.update_one(
            {
                "_id": ObjectId(request_id)
            },
            {
                "$set": update_data
            }
        )

        messages.success(
            request,
            "Custom request updated successfully."
        )

    return redirect("vendor_dashboard")    

def respond_custom_request(request, request_id):

    action = request.POST.get("action")

    if action == "accept":
        status = "Accepted"
    else:
        status = "Rejected"

    custom_requests_collection.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": status}}
    )

    return redirect("my_custom_requests")

def checkout_custom(request, request_id):

    custom_request = custom_requests_collection.find_one(
        {
            "_id": ObjectId(request_id)
        }
    )

    if not custom_request:
        messages.error(request, "Custom request not found.")
        return redirect("my_custom_requests")

    custom_request["id"] = str(custom_request["_id"])

    subtotal = int(custom_request["vendor_price"])
    delivery = 0
    total = subtotal

    return render(
        request,
        "checkout.html",
        {
            "custom_request": custom_request,
            "subtotal": subtotal,
            "delivery": delivery,
            "total": total
        }
    )

def customers(request):
    return render(request,'customers.html')
def reviews(request):
    return render(request,'reviews.html')


def logout_user(request):

    request.session.flush()


    return redirect('home')

def admin_dashboard(request):

    # Counts
    total_users = users_collection.count_documents({"role": "customer"})
    total_vendors = users_collection.count_documents({"role": "vendor"})
    total_orders = orders_collection.count_documents({})
    total_cakes = cakes_collection.count_documents({})
    total_contacts = contacts_collection.count_documents({})

    # Revenue
    total_revenue = 0
    for order in orders_collection.find():
        total_revenue += order.get("total", 0)

    # Recent Orders
    recent_orders = list(
        orders_collection.find().sort("_id", -1).limit(5)
    )

    for order in recent_orders:
        order["id"] = str(order["_id"])

    # Recent Users
    recent_users = list(
        users_collection.find({"role": "customer"}).sort("_id", -1).limit(5)
    )

    for user in recent_users:
        user["id"] = str(user["_id"])

    # ---------- DATA FOR POPUPS ----------

    users = list(
        users_collection.find({"role": "customer"}).sort("_id", -1)
    )

    for user in users:
        user["id"] = str(user["_id"])
        user["orders"] = orders_collection.count_documents(
            {"email": user["email"]}
        )

    vendors = list(
        users_collection.find({"role": "vendor"}).sort("_id", -1)
    )

    for vendor in vendors:
        vendor["id"] = str(vendor["_id"])
        vendor["cakes"] = cakes_collection.count_documents(
            {"vendor_email": vendor["email"]}
        )

    orders = list(
        orders_collection.find().sort("_id", -1)
    )

    for order in orders:
        order["id"] = str(order["_id"])

    return render(
        request,
        "admin_dashboard.html",
        {
            "total_users": total_users,
            "total_vendors": total_vendors,
            "total_orders": total_orders,
            "total_cakes": total_cakes,
            "total_contacts": total_contacts,
            "total_revenue": total_revenue,

            "recent_orders": recent_orders,
            "recent_users": recent_users,

            # Popup Data
            "users": users,
            "vendors": vendors,
            "orders": orders,
        }
    )

def manage_users(request):

    search = request.GET.get("search", "").strip()

    query = {
        "role": "customer"
    }

    if search:
        query["$or"] = [
            {"fullname": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]

    users = list(users_collection.find(query).sort("_id", -1))

    total_users = users_collection.count_documents({"role": "customer"})

    active_users = total_users
    inactive_users = 0

    for user in users:

        user["id"] = str(user["_id"])

        user["orders"] = orders_collection.count_documents({
            "email": user["email"]
        })

    total_orders = orders_collection.count_documents({})

    return render(
        request,
        "manage_users.html",
        {
            "users": users,
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "total_orders": total_orders,
            "search": search
        }
    )

def edit_user(request, user_id):

    user = users_collection.find_one({
        "_id": ObjectId(user_id)
    })

    if not user:
        return redirect("manage_users")

    if request.method == "POST":

        users_collection.update_one(

            {
                "_id": ObjectId(user_id)
            },

            {
                "$set": {

                    "fullname": request.POST.get("fullname"),
                    "email": request.POST.get("email"),
                    "phone": request.POST.get("phone")

                }
            }

        )

        messages.success(request, "User Updated Successfully")

        return redirect("manage_users")

    return render(
        request,
        "edit_user.html",
        {
            "user": user
        }
    )


def delete_user(request, user_id):

    users_collection.delete_one({
        "_id": ObjectId(user_id)
    })

    messages.success(request, "User Deleted Successfully")

    return redirect("manage_users")

def manage_vendors(request):

    search = request.GET.get("search", "").strip()

    query = {"role": "vendor"}

    if search:
        query["$or"] = [
            {"fullname": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]

    vendors = list(users_collection.find(query).sort("_id", -1))

    total_vendors = len(vendors)
    approved_vendors = total_vendors      # change later if approval system added
    pending_vendors = 0

    for vendor in vendors:

        vendor["id"] = str(vendor["_id"])

        vendor["cake_count"] = cakes_collection.count_documents({
            "vendor_email": vendor["email"]
        })

        vendor["order_count"] = orders_collection.count_documents({
            "vendor_email": vendor["email"]
        })

    total_cakes = cakes_collection.count_documents({})

    return render(request, "manage_vendors.html", {

        "vendors": vendors,

        "total_vendors": total_vendors,

        "approved_vendors": approved_vendors,

        "pending_vendors": pending_vendors,

        "total_cakes": total_cakes,

        "search": search

    })

def edit_vendor(request, vendor_id):

    vendor = users_collection.find_one({
        "_id": ObjectId(vendor_id),
        "role": "vendor"
    })

    if not vendor:
        return redirect("manage_vendors")

    vendor["id"] = str(vendor["_id"])

    if request.method == "POST":

        users_collection.update_one(

            {
                "_id": ObjectId(vendor_id)
            },

            {
                "$set": {

                    "fullname": request.POST.get("fullname"),
                    "email": request.POST.get("email"),
                    "phone": request.POST.get("phone")

                }
            }

        )

        messages.success(request, "Vendor Updated Successfully")

        return redirect("manage_vendors")

    return render(
        request,
        "edit_vendor.html",
        {
            "vendor": vendor
        }
    )

def delete_vendor(request, vendor_id):

    users_collection.delete_one({
        "_id": ObjectId(vendor_id),
        "role": "vendor"
    })

    messages.success(
        request,
        "Vendor Deleted Successfully"
    )

    return redirect("manage_vendors")

def add_vendor(request):

    if request.method == "POST":

        fullname = request.POST.get("fullname")
        shop_name = request.POST.get("shop_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        status = request.POST.get("status")

        logo = request.FILES.get("logo")
        banner = request.FILES.get("banner")

        logo_path = ""
        banner_path = ""

        if logo:
            logo_path = default_storage.save(
                f"vendor_logos/{logo.name}",
                logo
            )

        if banner:
            banner_path = default_storage.save(
                f"vendor_banners/{banner.name}",
                banner
            )

        if not phone.isdigit() or len(phone) != 10:
            messages.error(request, "Phone number must be 10 digits.")
            return redirect("add_vendor")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("add_vendor")

        if users_collection.find_one({"email": email}):
            messages.error(request, "Email already exists.")
            return redirect("add_vendor")

        users_collection.insert_one({

            "fullname": fullname,
            "shop_name": shop_name,
            "email": email,
            "phone": phone,
            "address": address,
            "password": password,
            "role": "vendor",
            "status": status,
            "logo": logo_path,
            "banner": banner_path

        })

        messages.success(request, "Vendor added successfully.")

        return redirect("manage_vendors")

    return render(request, "add_vendor.html")

def admin_cakes(request):

    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "").strip()

    query = {}

    if search:
        query["cake_name"] = {
            "$regex": search,
            "$options": "i"
        }

    if category and category != "All Categories":
        query["category"] = category

    cakes = list(cakes_collection.find(query).sort("_id", -1))

    for cake in cakes:
        cake["id"] = str(cake["_id"])

    total_cakes = cakes_collection.count_documents({})
    birthday_cakes = cakes_collection.count_documents({"category": "Birthday"})
    custom_cakes = cakes_collection.count_documents({"category": "Custom Cake"})
    total_vendors = users_collection.count_documents({"role": "vendor"})

    return render(request, "admin_cakes.html", {
        "cakes": cakes,
        "search": search,
        "category": category,
        "total_cakes": total_cakes,
        "birthday_cakes": birthday_cakes,
        "custom_cakes": custom_cakes,
        "total_vendors": total_vendors
    })

def admin_edit_cake(request, cake_id):

    cake = cakes_collection.find_one({
        "_id": ObjectId(cake_id)
    })

    if not cake:
        messages.error(request, "Cake not found.")
        return redirect("admin_cakes")

    cake["id"] = str(cake["_id"])

    if request.method == "POST":

        update_data = {

            "cake_name": request.POST.get("cake_name"),
            "category": request.POST.get("category"),
            "price": int(request.POST.get("price")),
            "weight": request.POST.get("weight"),
            "flavor": request.POST.get("flavor"),
            "description": request.POST.get("description"),
            "availability": request.POST.get("availability")

        }

        image = request.FILES.get("image")

        if image:

            image_path = default_storage.save(
                f"cakes/{image.name}",
                image
            )

            update_data["image"] = image_path

        cakes_collection.update_one(
            {
                "_id": ObjectId(cake_id)
            },
            {
                "$set": update_data
            }
        )

        messages.success(request, "Cake Updated Successfully")

        return redirect("admin_cakes")

    return render(
        request,
        "admin_edit_cake.html",
        {
            "cake": cake
        }
    )

def admin_delete_cake(request, cake_id):

    cakes_collection.delete_one({
        "_id": ObjectId(cake_id)
    })

    messages.success(request, "Cake Deleted Successfully")

    return redirect("admin_cakes")



def admin_orders(request):

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()

    query = {}

    if search:
        query["$or"] = [
            {"customer_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]

    if status and status != "All Orders":
        query["status"] = status

    orders = list(
        orders_collection.find(query).sort("_id", -1)
    )

    for order in orders:
        order["id"] = str(order["_id"])

    total_orders = orders_collection.count_documents({})
    pending_orders = orders_collection.count_documents({"status": "Pending"})
    delivered_orders = orders_collection.count_documents({"status": "Delivered"})

    total_revenue = 0
    for order in orders_collection.find():
        total_revenue += order.get("total", 0)

    return render(request, "admin_orders.html", {

        "orders": orders,

        "total_orders": total_orders,

        "pending_orders": pending_orders,

        "delivered_orders": delivered_orders,

        "total_revenue": total_revenue,

        "search": search,

        "status": status

    })

def contact_messages(request):

    contacts = list(
        contacts_collection.find().sort("_id", -1)
    )

    total_messages = len(contacts)

    unread_messages = total_messages

    replied_messages = 0

    important_messages = 0

    for contact in contacts:
        contact["id"] = str(contact["_id"])

    return render(
        request,
        "contact_messages.html",
        {
            "contacts": contacts,
            "total_messages": total_messages,
            "unread_messages": unread_messages,
            "replied_messages": replied_messages,
            "important_messages": important_messages
        }
    )

def delete_contact(request, contact_id):

    contacts_collection.delete_one(
        {
            "_id": ObjectId(contact_id)
        }
    )

    messages.success(
        request,
        "Contact message deleted successfully."
    )

    return redirect("contact_messages")

def about(request):
    return render(request,'about.html')

from datetime import date
from django.contrib import messages

def contact(request):

    if request.method == "POST":

        contact_data = {

            "name": request.POST.get("name"),

            "email": request.POST.get("email"),

            "subject": request.POST.get("subject"),

            "message": request.POST.get("message"),

            "created_at": str(date.today())

        }

        contacts_collection.insert_one(contact_data)

        messages.success(
            request,
            "Your message has been sent successfully!"
        )

        return redirect("contact")

    return render(request, "contact.html")
def forgot_password(request):

    if request.method == "POST":

        email = request.POST.get("email")

        user = users_collection.find_one({
            "email": email
        })

        if not user:

            messages.error(
                request,
                "Email not found"
            )

            return render(
                request,
                "forgot_password.html"
            )

        return render(
            request,
            "reset_password.html",
            {"email": email}
        )

    return render(
        request,
        "forgot_password.html"
    )
def reset_password(request):

    if request.method == "POST":

        email = request.POST.get("email")

        password = request.POST.get("password")

        confirm_password = request.POST.get(
            "confirm_password"
        )

        if password != confirm_password:

            messages.error(
                request,
                "Passwords do not match"
            )

            return redirect(
                "forgot_password"
            )

        users_collection.update_one(

            {"email": email},

            {
                "$set": {
                    "password": password
                }
            }

        )

        messages.success(
            request,
            "Password Updated Successfully"
        )

        return redirect(
            "login"
        )

    return redirect(
        "forgot_password"
    )
def toggle_favorite(request, cake_id):

    email = request.session.get("user_email")

    if not email:
        return redirect("login")

    favorite = favorites_collection.find_one({
        "user_email": email,
        "cake_id": cake_id
    })

    if favorite:

        favorites_collection.delete_one({
            "_id": favorite["_id"]
        })

        messages.success(request, "Removed from favorites.")

    else:

        cake = cakes_collection.find_one({
            "_id": ObjectId(cake_id)
        })

        favorites_collection.insert_one({

            "user_email": email,

            "cake_id": cake_id,

            "cake_name": cake["cake_name"],

            "price": cake["price"],

            "image": cake.get("image"),

            "vendor_email": cake.get("vendor_email")

        })

        messages.success(request, "Added to favorites.")

    return redirect("shop")
