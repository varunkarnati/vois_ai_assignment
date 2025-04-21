from langchain_core.tools import tool
import random

# --- Menu Data ---
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
        "description": "Juicy beef patty with cheddar cheese, lettuce, tomato, and onion on a brioche bun.",
        "dietary": "Contains gluten, dairy, meat. Bun can be substituted for gluten-free option."
    },
    "veggie burger": {
        "price": 9.50,
        "description": "Plant-based patty with lettuce, tomato, and onion on a whole wheat bun.",
        "dietary": "Vegetarian. Vegan option available. Contains gluten."
    },
    "caesar salad": {
        "price": 8.50,
        "description": "Romaine lettuce, croutons, parmesan cheese, and Caesar dressing.",
        "dietary": "Contains gluten, dairy, anchovies. Gluten-free without croutons."
    },
    "french fries": {
        "price": 3.99,
        "description": "Crispy golden french fries.",
        "dietary": "Vegetarian, Vegan, Gluten-Free (shared fryer)."
    },
    "soda": {
        "price": 1.99,
        "description": "Choice of Coke, Diet Coke, Sprite.",
        "dietary": "Vegan, Gluten-Free."
    }
}

daily_specials = [
    {"name": "Soup of the Day - Tomato Basil", "price": 5.50, "description": "Creamy tomato soup with fresh basil.", "dietary": "Vegetarian, Gluten-Free"},
    {"name": "Chef's Special Pasta", "price": 16.00, "description": "Penne pasta with grilled chicken and pesto cream sauce.", "dietary": "Contains gluten, dairy, meat."}
]

current_order = []

@tool
def get_item_price(item_name: str) -> float:
    """returns the price of an item from the menu"""
    item_name_lower = item_name.lower()
    if item_name_lower in menu_items:
        return menu_items[item_name_lower]['price']
    for special in daily_specials:
        if item_name_lower == special['name'].lower():
            return special['price']
    raise ValueError(f"{item_name} not found.")

@tool
def get_item_details(item_name: str) -> str:
    """returns the description of an item from the menu"""
    item_name_lower = item_name.lower()
    if item_name_lower in menu_items:
        return menu_items[item_name_lower]['description']
    for special in daily_specials:
        if item_name_lower == special['name'].lower():
            return special['description']
    raise ValueError(f"{item_name} not found.")

@tool
def get_dietary_information(item_name: str) -> str:
    """returns the dietary information of an item from the menu"""
    item_name_lower = item_name.lower()
    if item_name_lower in menu_items:
        return menu_items[item_name_lower]['dietary']
    for special in daily_specials:
        if item_name_lower == special['name'].lower():
            return special['dietary']
    raise ValueError(f"{item_name} not found.")

@tool
def get_available_menu_items() -> list:
    """returns a list of available menu items and their prices"""
    return [{"name": name.title(), "price": data['price']} for name, data in menu_items.items()]

@tool
def get_daily_specials() -> list:
    """returns a list of daily specials and their prices"""
    return daily_specials

@tool
def add_item_to_order(item_name: str, quantity: int = 1) -> str:
    """adds an item to the order and returns a confirmation message"""
    item_name_lower = item_name.lower()
    item_to_add = None
    if item_name_lower in menu_items:
        item_to_add = menu_items[item_name_lower]
        item_display_name = item_name.title()
    else:
        for special in daily_specials:
            if item_name_lower == special['name'].lower():
                item_to_add = special
                item_display_name = special['name']
                break
    if not item_to_add:
        return f"{item_name} not found."
    for _ in range(quantity):
        current_order.append({"name": item_display_name, "price": item_to_add['price']})
    return f"Added {quantity} {item_display_name}(s) to your order."

@tool
def remove_item_from_order(item_name: str, quantity: int = 1) -> str:
    """removes an item from the order and returns a confirmation message"""
    global current_order
    target_display_name = None
    item_name_lower = item_name.lower()
    if item_name_lower in menu_items:
        target_display_name = item_name.title()
    else:
        for special in daily_specials:
            if item_name_lower == special['name'].lower():
                target_display_name = special['name']
                break
    if not target_display_name:
        return f"{item_name} not found in order."
    removed = 0
    new_order = []
    for item in current_order:
        if item['name'] == target_display_name and removed < quantity:
            removed += 1
        else:
            new_order.append(item)
    current_order = new_order
    return f"Removed {removed} {target_display_name}(s)."

@tool
def get_current_order(order_id: str = "default") -> dict:
    """returns the current order and its total"""
    order = ORDERS.get(order_id, [])
    summary = {}
    for item in order:
        summary[item["name"]] = summary.get(item["name"], 0) + 1
    return {
        "items": [f"{qty} x {name}" for name, qty in summary.items()],
        "total": round(sum(item["price"] for item in order), 2)
    }

@tool
def calculate_order_total() -> float:
    """calculates the total of the current order"""
    return round(sum(item['price'] for item in current_order), 2)

@tool
def clear_order() -> str:
    """clears the current order and returns a confirmation message"""
    global current_order
    current_order = []
    return "Order cleared."
