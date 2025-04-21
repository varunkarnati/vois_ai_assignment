from langchain_core.tools import tool
import json
import os

ORDERS_FILE = "orders_db.json"

# Load current order state
def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    return {}

# Save order state
def save_orders(data):
    with open(ORDERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --- MENU DATA ---
menu_items = {
    "margherita pizza": {
        "price": 12.99,
        "description": "Classic pizza with tomato sauce, fresh mozzarella, and basil.",
        "dietary": "Vegetarian. Contains gluten, dairy."
    },
    "pepperoni pizza": {
        "price": 14.50,
        "description": "Pizza topped with spicy pepperoni slices.",
        "dietary": "Contains gluten, dairy, meat."
    },
    "cheeseburger": {
        "price": 9.99,
        "description": "Beef patty with cheddar, lettuce, tomato, onion on a brioche bun.",
        "dietary": "Contains gluten, dairy, meat."
    },
    "veggie burger": {
        "price": 9.50,
        "description": "Plant-based patty with lettuce, tomato, and onion.",
        "dietary": "Vegetarian. Vegan option available. Contains gluten."
    },
    "caesar salad": {
        "price": 8.50,
        "description": "Romaine, croutons, parmesan, Caesar dressing.",
        "dietary": "Contains gluten, dairy, anchovies."
    },
    "french fries": {
        "price": 3.99,
        "description": "Crispy golden french fries.",
        "dietary": "Vegetarian, Vegan, Gluten-Free (shared fryer)."
    },
    "soda": {
        "price": 1.99,
        "description": "Coke, Diet Coke, Sprite.",
        "dietary": "Vegan, Gluten-Free."
    }
}

daily_specials = [
    {"name": "Soup of the Day - Tomato Basil", "price": 5.50, "description": "Creamy tomato soup with basil.", "dietary": "Vegetarian, Gluten-Free"},
    {"name": "Chef's Special Pasta", "price": 16.00, "description": "Penne with grilled chicken and pesto cream.", "dietary": "Contains gluten, dairy, meat."}
]

# --- TOOLS ---
@tool
def get_item_price(item_name: str) -> float:
    """returns the item price"""
    item = item_name.lower()
    if item in menu_items:
        return menu_items[item]['price']
    for special in daily_specials:
        if item == special['name'].lower():
            return special['price']
    raise ValueError(f"{item_name} not found.")

@tool
def get_item_details(item_name: str) -> str:
    """returns the item description"""
    item = item_name.lower()
    if item in menu_items:
        return menu_items[item]['description']
    for special in daily_specials:
        if item == special['name'].lower():
            return special['description']
    raise ValueError(f"{item_name} not found.")

@tool
def get_dietary_information(item_name: str) -> str:
    """returns the item dietary information"""
    item = item_name.lower()
    if item in menu_items:
        return menu_items[item]['dietary']
    for special in daily_specials:
        if item == special['name'].lower():
            return special['dietary']
    raise ValueError(f"{item_name} not found.")

@tool
def get_available_menu_items() -> list:
    """returns a list of available menu items"""
    return [{"name": name.title(), "price": data["price"]} for name, data in menu_items.items()]

@tool
def get_daily_specials() -> list:
    """returns a list of daily specials"""
    return daily_specials

@tool
def add_item_to_order(item_name: str, quantity: int = 1, order_id: str = "default") -> str:
    """adds an item to the order"""
    orders = load_orders()
    item_key = item_name.lower()
    item_data = None
    display_name = item_name.title()

    if item_key in menu_items:
        item_data = menu_items[item_key]
    else:
        for special in daily_specials:
            if item_key == special["name"].lower():
                item_data = special
                display_name = special["name"]
                break

    if not item_data:
        return f"{item_name} not found."

    order = orders.setdefault(order_id, [])
    for _ in range(quantity):
        order.append({"name": display_name, "price": item_data["price"]})
    orders[order_id] = order
    save_orders(orders)

    return f"Added {quantity} {display_name}(s) to order {order_id}."

@tool
def remove_item_from_order(item_name: str, quantity: int = 1, order_id: str = "default") -> str:
    """removes an item from the order"""
    orders = load_orders()
    item_display = item_name.title()
    if order_id not in orders:
        return f"No active order {order_id}."
    order = orders[order_id]
    removed = 0
    new_order = []
    for item in order:
        if item["name"] == item_display and removed < quantity:
            removed += 1
        else:
            new_order.append(item)
    orders[order_id] = new_order
    save_orders(orders)
    return f"Removed {removed} {item_display}(s)."

@tool
def get_current_order(order_id: str = "default") -> dict:
    """returns the current order"""
    orders = load_orders()
    order = orders.get(order_id, [])
    summary = {}
    for item in order:
        summary[item["name"]] = summary.get(item["name"], 0) + 1
    item_list = [f"{qty} x {name}" for name, qty in summary.items()]
    total = round(sum(item["price"] for item in order), 2)
    return {"items": item_list, "total": total}

@tool
def calculate_order_total(order_id: str = "default") -> float:
    """returns the total of the current order"""
    return get_current_order(order_id)["total"]

@tool
def clear_order(order_id: str = "default") -> str:
    """clears the current order"""
    orders = load_orders()
    orders[order_id] = []
    save_orders(orders)
    return f"Order {order_id} cleared."
