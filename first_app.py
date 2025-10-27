import json
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key"

# ---------- DATABASE SETUP ----------
def init_db():
    con = sqlite3.connect("orders.db")
    cur = con.cursor()

        # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            phone TEXT,
            first_name TEXT,
            middle_name TEXT,
            last_name TEXT
        )
    """)

    # Create products table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            category TEXT,
            description TEXT,
            image TEXT,
            stock INTEGER DEFAULT 0
        )
    """)

    # Create orders table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total_amount REAL,
            order_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Create order_items table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price_at_time REAL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)



    # Create cart_orders table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cart_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            phone TEXT,
            email TEXT,
            region TEXT,
            province TEXT,
            city TEXT,
            barangay TEXT,
            street TEXT,
            note TEXT,
            payment_method TEXT,
            items TEXT,
            order_date TEXT DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL
            )
        """)


    # Create monthly_sales table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monthly_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT UNIQUE,
            total_sales REAL DEFAULT 0
        )
    """)

    con.commit()
    con.close()

init_db()
# ---------- HELPERS ----------
def save_order(order):
    con = sqlite3.connect("orders.db")
    cur = con.cursor()
    cur.execute(
        "INSERT INTO orders (name, appliance, furniture, kitchen_essential) VALUES (?, ?, ?, ?)",
        (order["name"], order["appliance"], order["furniture"], order["kitchen_essential"])
    )
    con.commit()
    con.close()

def get_orders():
    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM orders")
    return cur.fetchall()

def get_cart_orders():
    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM cart_orders")
    rows = cur.fetchall()
    con.close()

    cart_orders = []
    for row in rows:
        order = dict(row)
        try:
            order["items"] = json.loads(order["items"])
        except json.JSONDecodeError:
            order["items"] = []
        cart_orders.append(order)
    return cart_orders

def save_cart_order(data):
    con = sqlite3.connect("orders.db")
    cur = con.cursor()

    # Save order
    cur.execute("""
        INSERT INTO cart_orders (
            customer_name, phone, email, region, province, city, barangay,
            street, note, payment_method, items
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["fullName"],
        data["phoneNumber"],
        data["email"],
        data["region"],
        data["province"],
        data["city"],
        data["barangay"],
        data["street"],
        data.get("note", ""),
        data["payment_method"],
        json.dumps(data["items"])
    ))

    # Deduct stock per product ordered
    for item in data["items"]:
        cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item["quantity"], item["id"]))

    con.commit()
    con.close()

# ---------- SYNC CART ORDERS ----------
def update_cart_orders_with_edited_product(product_id, updated_info):
    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("SELECT * FROM cart_orders")
    orders = cur.fetchall()

    for order in orders:
        try:
            items = json.loads(order["items"])
        except json.JSONDecodeError:
            items = []

        changed = False
        for item in items:
            if item["id"] == product_id:
                item["name"] = updated_info["name"]
                item["price"] = updated_info["price"]
                item["image"] = updated_info["image"]
                changed = True

        if changed:
            cur.execute("UPDATE cart_orders SET items = ? WHERE id = ?", (json.dumps(items), order["id"]))

    con.commit()
    con.close()

def update_stock_after_checkout(cart_items):
    con = sqlite3.connect("orders.db")
    cur = con.cursor()

    for item in cart_items:
        product_id = item["id"]
        quantity = item["quantity"]

        # Make sure we don’t go negative
        cur.execute("""
            UPDATE products
            SET stock = stock - ?
            WHERE id = ? AND stock >= ?
        """, (quantity, product_id, quantity))

    con.commit()
    con.close()

def remove_product_from_cart_orders(product_id):
    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("SELECT * FROM cart_orders")
    orders = cur.fetchall()

    for order in orders:
        try:
            items = json.loads(order["items"])
        except json.JSONDecodeError:
            items = []

        new_items = [item for item in items if item["id"] != product_id]

        if len(items) != len(new_items):
            cur.execute("UPDATE cart_orders SET items = ? WHERE id = ?", (json.dumps(new_items), order["id"]))

    con.commit()
    con.close()

def read_menu(filename):
    with open(filename) as f:
        return [line.strip() for line in f.readlines()]
# ---------- LOAD PRODUCT DATA ----------
appliances = read_menu("appliances.txt")
furnitures = read_menu("furniture.txt")
kitchen_essentials = read_menu("kitchen_essentials.txt")

# ---------- INVENTORY FUNCTION ----------
def get_inventory():
    return {
        "Appliances": appliances,
        "Furniture": furnitures,
        "Kitchen Essentials": kitchen_essentials
    }


# sales
def get_monthly_sales():
    conn = sqlite3.connect('orders.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT strftime('%Y-%m', date) AS month, SUM(total) AS total_sales
        FROM sales
        GROUP BY month
        ORDER BY month DESC
    """)

    sales_data = cur.fetchall()
    conn.close()
    return sales_data

# ---------- USER LOGIN + REGISTER ----------
@app.route("/", methods=["GET", "POST"])
def user_login():
    show_login_modal = False

    # DO NOT auto-redirect here — always show login
    if request.method == "POST":
        action = request.form.get("action")
        con = sqlite3.connect("orders.db")
        cur = con.cursor()

        if action == "login":
            username = request.form.get("username")
            password = request.form.get("password")
            cur.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
            user = cur.fetchone()
            con.close()

            if user:
                session["user_logged_in"] = True
                session["username"] = user[1]
                session["email"] = user[3]
                session["phone"] = user[4]
                session["full_name"] = f"{user[5]} {user[6]} {user[7]}"  # first, middle, last
                return redirect(url_for("home"))

            else:
                flash("Invalid username or password!", "error")
                return redirect(url_for("user_login"))

        elif action == "register":
            username = request.form.get("new_username")
            password = request.form.get("new_password")
            email = request.form.get("email")
            phone = request.form.get("phone")
            first = request.form.get("first_name")
            middle = request.form.get("middle_name")
            last = request.form.get("last_name")

            try:
                cur.execute("""
                    INSERT INTO users (username, password, email, phone, first_name, middle_name, last_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (username, password, email, phone, first, middle, last)
                )
                con.commit()
                flash("Account created successfully. You can now log in.", "success")
                show_login_modal = True
            except sqlite3.IntegrityError:
                flash("Username already exists.", "error")

            con.close()

    return render_template("user_login.html", show_login_modal=show_login_modal)

@app.route("/user_dashboard")
def home():
    if not session.get("user_logged_in"):
        return redirect(url_for("user_login"))
    return render_template("home.html")

@app.route("/logout_user")
def logout_user():
    session.pop("user_logged_in", None)
    session.pop("username", None)
    session.pop("email", None)
    session.pop("phone", None)
    session.pop("full_name", None)
    flash("User logged out.", "info")
    return redirect(url_for("user_login"))


def get_all_users():
    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    con.close()
    return users


# ---------- ORDER FORM ----------
@app.route("/order", methods=["GET", "POST"])
def order():
    if not session.get("user_logged_in"):
        return redirect(url_for("user_login"))

    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("SELECT * FROM products WHERE category = 'Appliances'")
    appliances = cur.fetchall()

    cur.execute("SELECT * FROM products WHERE category = 'Furniture'")
    furnishings = cur.fetchall()

    cur.execute("SELECT * FROM products WHERE category = 'Kitchen Essentials'")
    kitchen_essentials = cur.fetchall()

    con.close()

    return render_template(
        "forms.html",
        appliances=appliances,
        furnishings=furnishings,
        kitchen_essentials=kitchen_essentials
    )


@app.route("/submit_order", methods=["POST"])
def submit_order():
    data = request.json

    try:
        con = sqlite3.connect("orders.db")
        cur = con.cursor()

        user_id = None  # Optional: use session['user_id'] if logged in
        total_amount = data.get("total_amount", 0)

        # Insert into orders table
        cur.execute("""
            INSERT INTO orders (user_id, total_amount)
            VALUES (?, ?)
        """, (user_id, total_amount))
        order_id = cur.lastrowid

        # Insert ordered items
        ordered_items = json.loads(data.get("items", "[]"))
        for item in ordered_items:
            product_id = item.get("id")
            quantity = int(item.get("quantity", 1))
            price_at_time = float(item.get("price", 0))

            cur.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price_at_time)
                VALUES (?, ?, ?, ?)
            """, (order_id, product_id, quantity, price_at_time))

            # Decrease product stock
            cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))

        # Save full order to cart_orders (for reference)
        cur.execute("""
            INSERT INTO cart_orders (
                customer_name, phone, email,
                region, province, city, barangay, street, note,
                payment_method, items, order_date, total_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("name"),
            data.get("phone"),
            data.get("email"),
            data.get("region"),
            data.get("province"),
            data.get("city"),
            data.get("barangay"),
            data.get("street"),
            data.get("note"),
            data.get("payment_method"),
            data.get("items"),
            data.get("order_date"),
            total_amount
        ))

        con.commit()
        return jsonify({"status": "success"})

    except Exception as e:
        print("❌ Error in submit_order:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        con.close()


@app.route("/list", methods=["GET"])
def list_orders():
    form_orders = get_orders()
    cart_orders = get_cart_orders()
    return render_template("list.html", orders=form_orders, cart_orders=cart_orders)


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', [])
    subtotal = sum(item['price'] * item['quantity'] for item in cart)
    delivery_fee = 199.00 if cart else 0
    total = subtotal + delivery_fee

    step = 1

    if request.method == 'POST':
        # If triggered by JS fetch:
        if request.is_json:
            data = request.get_json()
            cart_items = data.get('cartItems', [])
        else:
            cart_items = cart  # fallback if regular POST

        try:
            conn = sqlite3.connect('orders.db')
            cur = conn.cursor()

            for item in cart_items:
                product_id = item['id']
                quantity = item['quantity']

                cur.execute("SELECT stock FROM products WHERE id = ?", (product_id,))
                row = cur.fetchone()
                if row:
                    current_stock = row[0]
                    if quantity > current_stock:
                        flash(f"Not enough stock for {item['name']}", 'error')
                        conn.close()
                        return redirect(url_for('checkout'))

                    new_stock = current_stock - quantity
                    cur.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))

                    from datetime import datetime

                    # Compute today's month in YYYY-MM format
                    month_now = datetime.now().strftime("%Y-%m")

                    # Check if that month exists
                    cur.execute("SELECT total_sales FROM monthly_sales WHERE month = ?", (month_now,))
                    row = cur.fetchone()

                    if row:
                        # If month exists, update it
                        new_total = row[0] + total
                        cur.execute("UPDATE monthly_sales SET total_sales = ? WHERE month = ?", (new_total, month_now))
                    else:
                        # If month doesn't exist, insert a new row
                        cur.execute("INSERT INTO monthly_sales (month, total_sales) VALUES (?, ?)", (month_now, total))

                    # 🧠 Only proceed if data is from JSON (via fetch)
                    if request.is_json:
                        name = data.get("name", "")
                        phone = data.get("phone", "")
                        email = data.get("email", "")
                        region = data.get("region", "")
                        province = data.get("province", "")
                        city = data.get("city", "")
                        barangay = data.get("barangay", "")
                        street = data.get("street", "")
                        note = data.get("note", "")
                        payment = data.get("payment_method", "")

                        import json
                        from datetime import datetime

                        cur.execute("""
                            INSERT INTO cart_orders (
                                customer_name, phone, email,
                                region, province, city, barangay, street, note,
                                payment_method, items, order_date, total_amount
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            name, phone, email,
                            region, province, city, barangay, street, note,
                            payment, json.dumps(cart_items),
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            total
                        ))

            conn.commit()
            conn.close()
            session['cart'] = []

        except Exception as e:
            print("Checkout Error:", e)
            flash("Checkout failed. Please try again.", 'error')
            return redirect(url_for('checkout'))

        step = 2

    return render_template(
        'checkout.html',
        subtotal=f"{subtotal:,.2f}",
        delivery_fee=f"{delivery_fee:,.2f}",
        total=f"{total:,.2f}",
        current_step=step
    )


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    try:
        item = {
            'id': int(request.form.get('id', '0')),
            'name': request.form.get('name', '').strip(),
            'price': float(request.form.get('price', '0')),
            'quantity': int(request.form.get('quantity', '1')),
            'image': request.form.get('image', '').strip()
        }
    except ValueError as e:
        flash(f"Invalid form data: {e}", 'error')
        return redirect(request.referrer or url_for('home'))

    cart = session.get('cart', [])

    # Update existing item or add new
    for existing_item in cart:
        if existing_item['name'] == item['name']:
            existing_item['quantity'] += item['quantity']
            break
    else:
        cart.append(item)

    session['cart'] = cart
    session.modified = True
    flash('Item added to cart!', 'success')
    return redirect(request.referrer or url_for('home'))


@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    name = request.form.get('name')
    cart = session.get('cart', [])
    updated_cart = [item for item in cart if item['name'] != name]

    session['cart'] = updated_cart
    session.modified = True
    flash(f"{name} removed from cart.", "info")
    return redirect(url_for('checkout'))


@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    session.pop('cart', None)
    return '', 204


# ---------- ADMIN LOGIN ----------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "admin123":
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials!", "error")
            return redirect(url_for("admin_login"))
    return render_template("admin_login.html")

@app.route("/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")

@app.route("/dashboard/products")
def dashboard_products():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    products = get_all_products()
    return render_template("admin_inventory.html", products=products)

@app.route("/dashboard/users")
def dashboard_users():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    users = get_all_users()
    return render_template("admin_users.html", users=users)

@app.route("/dashboard/addresses")
def dashboard_addresses():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    addresses = get_cart_orders()
    return render_template("admin_addresses.html", checkout_addresses=addresses)

# @app.route("/dashboard/sales")
# def dashboard_sales():
#     if not session.get("admin_logged_in"):
#         return redirect(url_for("admin_login"))

#     conn = sqlite3.connect("orders.db")
#     conn.row_factory = sqlite3.Row
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM monthly_sales ORDER BY month DESC")
#     sales = cur.fetchall()
#     conn.close()

#     return render_template("admin_sales.html", monthly_sales=sales)
@app.route("/dashboard/sales")
def dashboard_sales():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # 1. Monthly Sales
    cur.execute("SELECT * FROM monthly_sales ORDER BY month DESC")
    monthly_sales = cur.fetchall()

    # 2. Total Orders
    cur.execute("SELECT COUNT(*) FROM cart_orders")
    total_orders = cur.fetchone()[0]

    # 3. Total Revenue
    cur.execute("SELECT SUM(total_amount) FROM cart_orders")
    total_revenue = cur.fetchone()[0] or 0

    # 4. Top 5 Best-Selling Products
    import json
    cur.execute("SELECT items FROM cart_orders")
    product_counter = {}
    for row in cur.fetchall():
        try:
            items = json.loads(row["items"])
            for item in items:
                product_counter[item["name"]] = product_counter.get(item["name"], 0) + item["quantity"]
        except:
            continue
    top_products = sorted(product_counter.items(), key=lambda x: x[1], reverse=True)[:5]

    # 5. Top Customers (by name)
    cur.execute("""
        SELECT customer_name, COUNT(*) as order_count
        FROM cart_orders
        GROUP BY customer_name
        ORDER BY order_count DESC
        LIMIT 5
    """)
    top_customers = cur.fetchall()

    con.close()

    return render_template("admin_sales.html",
        monthly_sales=monthly_sales,
        total_orders=total_orders,
        total_revenue=total_revenue,
        top_products=top_products,
        top_customers=top_customers
    )


@app.route("/dashboard/orders")
def dashboard_orders():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("SELECT * FROM cart_orders ORDER BY order_date DESC")
    rows = cur.fetchall()
    con.close()

    import json
    orders = []
    for row in rows:
        order = dict(row)
        try:
            order["items"] = json.loads(order["items"])

        except:
            order["items"] = []
        orders.append(order)

    return render_template("orders-history.html", orders=orders)

# @app.route("/dashboard/orders")
# def dashboard_orders():
#     if not session.get("admin_logged_in"):
#         return redirect(url_for("admin_login"))

#     con = sqlite3.connect("orders.db")
#     con.row_factory = sqlite3.Row
#     cur = con.cursor()

#     cur.execute("SELECT * FROM cart_orders ORDER BY order_date DESC")
#     rows = cur.fetchall()
#     con.close()

#     import json
#     orders = []
#     for row in rows:
#         order = dict(row)
#         try:
#             order["items"] = json.loads(order["items"])
#         except:
#             order["items"] = []
#         orders.append(order)

#     return render_template("order-history.html", orders=orders)


@app.route("/admin/address_details/<int:address_id>")
def admin_address_details(address_id):
    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM cart_orders WHERE id = ?", (address_id,))
    row = cur.  one()
    con.close()

    if row:
        order = dict(row)
        try:
            order["items"] = json.loads(order["items"])
        except:
            order["items"] = []
        return jsonify(order)
    else:
        return jsonify({"error": "Order not found"}), 404

@app.route("/logout", endpoint="admin_logout")
def logout():
    session.pop("admin_logged_in", None)
    flash("Admin logged out.", "info")
    return redirect(url_for("admin_login"))

def get_all_products():
    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    con.close()
    return products

@app.route("/admin/add_product", methods=["POST"])
def add_product():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    name = request.form["name"]
    category = request.form["category"]
    description = request.form["description"]
    image = request.form["image"]
    price = float(request.form["price"])
    stock = int(request.form["stock"])

    con = sqlite3.connect("orders.db")
    cur = con.cursor()
    cur.execute("""
        INSERT INTO products (name, category, description, image, price, stock)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (name, category, description, image, price, stock)
    )
    con.commit()
    con.close()

    flash("Product added successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete_product", methods=["POST"])
def delete_product():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    product_id = request.form["product_id"]
    con = sqlite3.connect("orders.db")
    cur = con.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    con.commit()
    con.close()

    flash("Product deleted successfully.", "info")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/edit_product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        description = request.form["description"]
        image = request.form["image"]
        price = float(request.form["price"])
        stock = int(request.form["stock"])

        cur.execute("""
            UPDATE products
            SET name=?, category=?, description=?, image=?, price=?, stock=?
            WHERE id=?
        """, (name, category, description, image, price, stock, product_id))
        con.commit()
        con.close()

        # ✅ Sync updated product info to cart_orders
        update_cart_orders_with_edited_product(product_id, {
            "name": name,
            "price": price,
            "image": image
        })

        flash("Product updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    # GET: Show edit form
    cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cur.fetchone()
    con.close()
    return render_template("edit_product.html", product=product)

#USER PROFILE
@app.route("/profile")
def user_profile():
    if not session.get("user_logged_in"):
        flash("You must be logged in to view your profile.", "error")
        return redirect(url_for("user_login"))

    user = {
        "full_name": session.get("full_name"),
        "username": session.get("username"),
        "email": session.get("email"),
        "phone": session.get("phone"),
        "address": "N/A"  # Replace with actual address lookup if needed
    }

    # Example dummy data; replace with DB lookups later
    orders = []
    reviews = []

    return render_template("profile.html", user=user, orders=orders, reviews=reviews)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    # You can extend this to update DB if you store profile data
    session['phone'] = request.form['phone']
    flash("Profile updated successfully.", "success")
    return redirect(url_for('user_profile'))

@app.route('/change_password', methods=['POST'])
def change_password():
    # Simulated check — replace with hashed password validation if needed
    current = request.form['current_password']
    new = request.form['new_password']
    confirm = request.form['confirm_password']

    if new != confirm:
        flash("New passwords do not match.", "error")
    elif current != "your_password":  # Replace with a check from DB
        flash("Current password incorrect.", "error")
    else:
        flash("Password changed successfully.", "success")
    return redirect(url_for('user_profile'))


from collections import defaultdict
from datetime import datetime

def get_monthly_sales():
    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Fetch order_date and items from cart_orders
    cur.execute("SELECT order_date, items FROM cart_orders")
    rows = cur.fetchall()
    con.close()

    monthly_sales = defaultdict(float)

    for row in rows:
        try:
            # Parse items and compute total for this order
            items = json.loads(row["items"])
            order_total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)

            # Format order_date to YYYY-MM
            order_date = row["order_date"]
            order_month = datetime.strptime(order_date, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m")

            # Add to monthly total
            monthly_sales[order_month] += order_total
        except (json.JSONDecodeError, ValueError, KeyError):
            continue  # Skip problematic rows

    # Convert to list of dicts for template use
    return [{"month": month, "total_sales": total} for month, total in sorted(monthly_sales.items(), reverse=True)]
def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(col[1] == column for col in cursor.fetchall())

def add_order_date_column():
    con = sqlite3.connect("orders.db")
    cur = con.cursor()
    if not column_exists(cur, "cart_orders", "order_date"):
        cur.execute("ALTER TABLE cart_orders ADD COLUMN order_date TEXT DEFAULT CURRENT_TIMESTAMP")
        con.commit()
        print("✅ 'order_date' column added to cart_orders.")
    else:
        print("⚠️ 'order_date' column already exists. Skipping add.")
    con.close()

def add_total_amount_column():
    con = sqlite3.connect("orders.db")
    cur = con.cursor()
    if not column_exists(cur, "cart_orders", "total_amount"):
        cur.execute("ALTER TABLE cart_orders ADD COLUMN total_amount REAL DEFAULT 0")
        con.commit()
        print("✅ 'total_amount' column added to cart_orders.")
    else:
        print("⚠️ 'total_amount' column already exists. Skipping add.")
    con.close()

# def add_order_date_column():
#     con = sqlite3.connect("orders.db")
#     cur = con.cursor()
#     try:
#         cur.execute("ALTER TABLE cart_orders ADD COLUMN order_date TEXT DEFAULT CURRENT_TIMESTAMP")
#         con.commit()
#         print("✅ 'order_date' column added to cart_orders.")
#     except sqlite3.OperationalError as e:
#         print("⚠️ Skipping column add — it may already exist:", e)
#     con.close()

# def add_total_amount_column():
#     con = sqlite3.connect("orders.db")
#     cur = con.cursor()
#     try:
#         cur.execute("ALTER TABLE cart_orders ADD COLUMN total_amount REAL DEFAULT 0")
#         con.commit()
#         print("✅ 'total_amount' column added to cart_orders.")
#     except sqlite3.OperationalError as e:
#         print("⚠️ Skipping column add — it may already exist:", e)
#     con.close()

# ---------- MAIN ----------
if __name__ == "__main__":
    init_db()
    # add_order_date_column()
    # add_total_amount_column()
    app.run(debug=True)
    con = sqlite3.connect("orders.db")
    cur = con.cursor()

    cur.execute("PRAGMA table_info(cart_orders)")
    columns = cur.fetchall()

    for column in columns:
        print(column)

    con.close()