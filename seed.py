import sqlite3
from first_app import init_db
from datetime import datetime, timedelta
import random
import json

# ---------- INITIALIZE DB ----------
init_db()

# ---------- PRODUCT DATA ----------
appliances = [
    ("TELEVISION", "Appliances", "Smart 4K UHD TV with streaming capabilities", "television.jpg", 30000.00, 10),
    ("DISHWASHER", "Appliances", "Automatic dishwasher with multiple wash cycles", "dishwasher.png", 18999.00, 10),
    ("MICROWAVE", "Appliances", "Compact microwave with defrost and timer functions", "microwave.jpg", 2500.00, 10),
    ("TOASTER", "Appliances", "4-slice toaster with browning control", "toaster.jpg", 3499.00, 10),
    ("AIR FRYER", "Appliances", "Oil-less air fryer with digital presets", "air_fryer.jpg", 5000.00, 10),
    ("RICE COOKER", "Appliances", "Multi-function rice cooker with keep-warm mode", "rice_cooker.jpeg", 2999.00, 10)
]

furnitures = [
    ("SOFA", "Furniture", "Comfortable 3-seater fabric sofa", "sofa.jpg", 12000.00, 10),
    ("MIRROR", "Furniture", "Full-length decorative wall mirror", "mirror.jpg", 6000.00, 10),
    ("OFFICE CHAIR", "Furniture", "Ergonomic office chair with adjustable height", "office_chair.jpg", 5000.00, 10),
    ("BAR STOOL", "Furniture", "Modern bar stool with metal frame", "bar_stool.jpg", 2800.00, 10),
    ("DINING TABLE", "Furniture", "Wooden dining table that seats six", "dining_table.jpg", 15000.00, 10),
    ("BED FRAME", "Furniture", "Queen-sized wooden bed frame with headboard", "bed_frame.jpg", 9999.00, 10)
]

kitchen_essentials = [
    ("PAN", "Kitchen Essentials", "Non-stick frying pan for everyday cooking", "pan.jpg", 800.00, 10),
    ("SPATULA", "Kitchen Essentials", "Heat-resistant silicone spatula", "spatula.jpg", 300.00, 10),
    ("CUTTING BOARD", "Kitchen Essentials", "Durable wooden cutting board", "cutting_board.jpg", 600.00, 10),
    ("GRATER", "Kitchen Essentials", "Multi-surface stainless steel grater", "grater.jpg", 450.00, 10),
    ("KNIFE", "Kitchen Essentials", "Sharp chef’s knife with ergonomic handle", "knife.jpg", 900.00, 10),
    ("MIXING BOWL", "Kitchen Essentials", "Stainless steel mixing bowl for prep work", "mixing_bowl.jpg", 650.00, 10)
]

all_products = appliances + furnitures + kitchen_essentials

# ---------- USERS ----------
users = [
    ("juan123", "pass123", "juan@example.com", "09171234567", "Juan", "Santos", "Dela Cruz"),
    ("maria456", "pass123", "maria@example.com", "09182345678", "Maria", "Reyes", "Lopez"),
    ("pedro789", "pass123", "pedro@example.com", "09183456789", "Pedro", "M.", "Reyes"),
]

# ---------- SEED FUNCTION ----------
def seed_data():
    con = sqlite3.connect("orders.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Insert Users
    for user in users:
        cur.execute("""
            INSERT OR IGNORE INTO users (username, password, email, phone, first_name, middle_name, last_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, user)

    # Insert Products
    for product in all_products:
        cur.execute("""
            INSERT INTO products (name, category, description, image, price, stock)
            VALUES (?, ?, ?, ?, ?, ?)
        """, product)

    # Get product IDs from DB
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    # Insert Random Order History (past 12 months)
    for months_back in range(12):  # simulate 12 months
        for user in users:
            full_name = f"{user[4]} {user[5]} {user[6]}"
            phone = user[3]
            email = user[2]

            for _ in range(random.randint(1, 3)):  # 1–3 orders per user per month
                order_date = datetime.now() - timedelta(days=30 * months_back + random.randint(0, 27))
                order_date_str = order_date.strftime("%Y-%m-%d %H:%M:%S")

                ordered_items = []
                order_total = 0

                selected_items = random.sample(products, k=random.randint(2, 4))
                for item in selected_items:
                    qty = random.randint(1, 3)
                    subtotal = item["price"] * qty
                    order_total += subtotal
                    ordered_items.append({
                        "id": item["id"],
                        "name": item["name"],
                        "price": item["price"],
                        "quantity": qty,
                        "image": item["image"]
                    })

                    # Deduct stock
                    cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, item["id"]))

                # Insert into cart_orders
                cur.execute("""
                    INSERT INTO cart_orders (
                        customer_name, phone, email,
                        region, province, city, barangay, street, note,
                        payment_method, items, order_date, total_amount
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    full_name,
                    phone,
                    email,
                    "Region IV-A", "Batangas", "Talisay", "Barangay Uno", "Street 123", "Auto-generated test order",
                    "Cash on Delivery",
                    json.dumps(ordered_items),
                    order_date_str,
                    order_total
                ))

    con.commit()
    con.close()
    print("✅ Seed data with users, products, and past order history inserted!")

# ---------- MAIN ----------
if __name__ == "__main__":
    seed_data()
