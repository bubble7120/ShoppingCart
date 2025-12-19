from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
print("🔍 使用中的資料庫路徑：", os.path.abspath("shop.db"))

app = Flask(__name__)
app.secret_key = "思穎的購物車密鑰"  

products = [
    {"name": "玫瑰保濕面霜", "price": 3200},
    {"name": "絲絨護手霜", "price": 2800},
    {"name": "玻尿酸精華液", "price": 1800}
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/category")
def category():
    return render_template("category.html", products=products)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    product_name = request.form["name"]
    product_price = int(request.form["price"])
    cart = session.get("cart", [])

    for item in cart:
        if item["name"] == product_name:
            item["quantity"] += 1
            break
    else:
        cart.append({
            "name": product_name,
            "price": product_price,
            "quantity": 1
        })

    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    cart_items = session.get("cart", [])
    total = sum(item["price"] * item["quantity"] for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)

@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    name = request.form["name"]
    cart = session.get("cart", [])
    cart = [item for item in cart if item["name"] != name]
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form["name"]
        price = int(request.form["price"])
        products.append({"name": name, "price": price})
        return redirect(url_for("category"))
    return render_template("add_product.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("shop.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "帳號已存在，請重新輸入"
        conn.close()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("shop.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session["user"] = username
            return redirect(url_for("category"))
        else:
            return "登入失敗，請檢查帳號密碼"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

import traceback

@app.route("/checkout", methods=["POST"])
def checkout():
    try:
        if "user" not in session:
            return redirect(url_for("login"))

        cart_items = session.get("cart", [])
        total = sum(item["price"] * item["quantity"] for item in cart_items)
        username = session["user"]

        conn = sqlite3.connect("shop.db")
        conn.execute("PRAGMA foreign_keys = ON")  
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id_result = cursor.fetchone()
        if not user_id_result:
            conn.close()
            return "找不到會員資料，請重新登入"

        user_id = user_id_result[0]
        cursor.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (user_id, total))
        order_id = cursor.lastrowid

        for item in cart_items:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_name, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (order_id, item["name"], item["quantity"], item["price"]))

        conn.commit()
        conn.close()

        session.pop("cart", None)
        return render_template("checkout.html", total=total, order_id=order_id)

    except Exception as e:
        traceback.print_exc()
        return f"⚠️ 發生錯誤：{e}"


@app.route("/admin_orders")
def admin_orders():
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT users.username, orders.id, orders.total, orders.timestamp,
               order_items.product_name, order_items.quantity, order_items.price
        FROM orders
        JOIN users ON orders.user_id = users.id
        JOIN order_items ON orders.id = order_items.order_id
        ORDER BY orders.timestamp DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return render_template("admin_orders.html", orders=rows)



if __name__ == "__main__":
    app.run(debug=True)