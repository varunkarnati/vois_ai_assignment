import os
import json
import logging
import tempfile
import os
from pprint import pprint
from langchain_core.tools import tool

# === Logger Setup ===
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# === Paths ===
_current_dir = os.path.dirname(__file__)
ORDERS_FILE = os.path.abspath(os.path.join(_current_dir, "..", "..", "orders_db.json"))
ORDERS_DIR = os.path.dirname(ORDERS_FILE)

# === Menu Items & Specials ===
menu_items = {
    "margherita pizza": {"price": 12.99, "description": "Classic pizza with tomato sauce, mozzarella, and basil.", "dietary": "Vegetarian. Contains gluten, dairy."},
    "pepperoni pizza": {"price": 14.50, "description": "Pizza topped with spicy pepperoni slices.", "dietary": "Contains gluten, dairy, meat."},
    "cheeseburger": {"price": 9.99, "description": "Beef patty with cheddar, lettuce, tomato, and onion.", "dietary": "Contains gluten, dairy, meat."},
    "veggie burger": {"price": 9.50, "description": "Plant-based patty with lettuce and tomato.", "dietary": "Vegetarian. Vegan option available. Contains gluten."},
    "caesar salad": {"price": 8.50, "description": "Romaine, croutons, parmesan, Caesar dressing.", "dietary": "Contains gluten, dairy, anchovies."},
    "french fries": {"price": 3.99, "description": "Crispy golden fries.", "dietary": "Vegetarian, Vegan, Gluten-Free (shared fryer)."},
    "soda": {"price": 1.99, "description": "Coke, Diet Coke, or Sprite.", "dietary": "Vegan, Gluten-Free."}
}

daily_specials = [
    {"name": "Soup of the Day - Tomato Basil", "price": 5.50, "description": "Creamy tomato soup with basil.", "dietary": "Vegetarian, Gluten-Free"},
    {"name": "Chef's Special Pasta", "price": 16.00, "description": "Penne pasta with grilled chicken in pesto cream.", "dietary": "Contains gluten, dairy, meat."}
]

# === Order Storage ===
def load_orders():
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                orders = json.load(f)
                logger.debug(f"[load_orders] Loaded: {orders}")
                return orders
    except Exception as e:
        logger.error(f"[load_orders] Error: {e}", exc_info=True)
    return {}

def save_orders(orders):
    try:
        os.makedirs(ORDERS_DIR, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=ORDERS_DIR, suffix='.tmp')
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(orders, f, indent=2)
            os.replace(tmp_path, ORDERS_FILE)
            logger.info(f"[save_orders] Saved {len(orders)} orders to {ORDERS_FILE}")
        except Exception as e:
            logger.error(f"[save_orders] Write failed: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise e
    except Exception as e:
        logger.error(f"[save_orders] Failed: {e}", exc_info=True)

# === Tool Functions ===
 
def get_item_price(item_name: str) -> float:
    item = item_name.lower()
    if item in menu_items:
        return menu_items[item]["price"]
    for special in daily_specials:
        if item == special["name"].lower():
            return special["price"]
    raise ValueError(f"Item '{item_name}' not found in menu.")

 
def get_item_details(item_name: str) -> str:
    item = item_name.lower()
    if item in menu_items:
        return menu_items[item]["description"]
    for special in daily_specials:
        if item == special["name"].lower():
            return special["description"]
    raise ValueError(f"Item '{item_name}' not found.")


 
def get_available_menu_items(order_id: str = "default") -> list:
    return [{"name": name.title(), "price": data["price"]} for name, data in menu_items.items()]




def add_item_to_order(item_name: str, quantity: int = 1, order_id: str = "default") -> str:
    orders = load_orders()
    item_key = item_name.lower()
    item_data = menu_items.get(item_key) or next((s for s in daily_specials if s["name"].lower() == item_key), None)

    if not item_data:
        return f"Item '{item_name}' not found."

    display_name = item_data.get("name", item_name.title())
    orders.setdefault(order_id, []).extend([{"name": display_name, "price": item_data["price"]}] * quantity)

    save_orders(orders)
    return f"✅ Added {quantity} x {display_name} to order {order_id}."


def remove_item_from_order(item_name: str, quantity: int = 1, order_id: str = "default") -> str:
    orders = load_orders()
    order = orders.get(order_id, [])
    display_name = item_name.title()

    removed = 0
    updated_order = []

    for item in reversed(order):
        if item["name"] == display_name and removed < quantity:
            removed += 1
        else:
            updated_order.insert(0, item)

    orders[order_id] = updated_order
    if removed > 0:
        save_orders(orders)

    return f"🗑️ Removed {removed} x {display_name} from order {order_id}." if removed else f"❌ Item '{display_name}' not found."


def get_current_order(order_id: str = "default") -> dict:
    orders = load_orders()
    order = orders.get(order_id, [])
    summary = {}
    for item in order:
        summary[item["name"]] = summary.get(item["name"], 0) + 1
    total = round(sum(i["price"] for i in order), 2)

    pprint(summary)
    pprint(total)

    return {
        "items": [f"{qty} x {name}" for name, qty in summary.items()],
        "total": total
    }


def calculate_order_total(order_id: str = "default") -> float:
    return get_current_order(order_id)["total"]


