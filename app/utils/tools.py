from langchain_core.tools import tool
import json
import os
import logging
import tempfile # <--- Import tempfile

logger = logging.getLogger(__name__)

# --- Define ORDERS_FILE relative to this file's location ---
_current_dir = os.path.dirname(__file__)
ORDERS_FILE = os.path.abspath(os.path.join(_current_dir, "..", "..", "orders_db.json"))
ORDERS_DIR = os.path.dirname(ORDERS_FILE) # <--- Get the directory path
logger.info(f"Using orders database file at: {ORDERS_FILE}")

# --- load_orders function remains the same ---
def load_orders():
    logger.debug(f"Attempting to load orders from: {ORDERS_FILE}")
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding='utf-8') as f: # Added encoding
                data = json.load(f)
                logger.debug(f"Successfully loaded {len(data)} order(s)")
                return data
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {ORDERS_FILE}. File might be corrupted. Returning empty state.")
            # Optionally: backup the corrupted file here before returning empty
            # import shutil
            # try:
            #     shutil.copyfile(ORDERS_FILE, ORDERS_FILE + ".corrupted")
            # except Exception as backup_e:
            #     logger.error(f"Could not backup corrupted file: {backup_e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading orders from {ORDERS_FILE}: {e}", exc_info=True)
            return {} # Return empty dict on other errors too
    else:
        logger.warning(f"Orders file not found at {ORDERS_FILE}. Starting with empty state.")
        return {}

# --- MODIFIED save_orders function for atomic writes ---
def save_orders(data):
    logger.debug(f"Attempting to atomically save {len(data)} order(s) to {ORDERS_FILE}")
    # Ensure the target directory exists
    try:
        os.makedirs(ORDERS_DIR, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create directory {ORDERS_DIR}: {e}", exc_info=True)
        # Decide if you want to raise or just log and potentially fail the save
        return # Or raise e

    # Use NamedTemporaryFile for atomic write pattern
    temp_file_path = None
    try:
        # Create temp file in the same directory as the target file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=ORDERS_DIR, encoding='utf-8', suffix='.tmp') as tmp_f:
            temp_file_path = tmp_f.name
            logger.debug(f"Writing to temporary file: {temp_file_path}")
            json.dump(data, tmp_f, indent=2)
            # tmp_f is automatically flushed and closed upon exiting 'with'

        # If write to temp file succeeded, atomically replace the original file
        logger.debug(f"Replacing {ORDERS_FILE} with {temp_file_path}")
        os.replace(temp_file_path, ORDERS_FILE) # os.replace is atomic on most systems
        logger.info(f"Successfully saved {len(data)} order(s) to {ORDERS_FILE}")

    except Exception as e:
        logger.error(f"Failed to save orders to {ORDERS_FILE}: {e}", exc_info=True)
        # Clean up the temporary file if it exists and an error occurred
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                logger.warning(f"Cleaning up temporary file due to error: {temp_file_path}")
                os.remove(temp_file_path)
            except OSError as remove_e:
                logger.error(f"Failed to remove temporary file {temp_file_path}: {remove_e}")
        # Optionally re-raise the exception if the caller needs to know
        # raise

# --- MENU DATA ---
# (rest of the menu_items and daily_specials remain the same)
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
# (Tool definitions remain the same, they rely on the corrected load/save functions)
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
    """Use this tool ONLY when the user explicitly asks to add a specific item (like 'margherita pizza' or 'soda') to their current order. Provide the item_name, quantity (default is 1), and the required order_id.""" # <--- IMPROVED DESCRIPTION
    logger.info(f"Attempting to add {quantity} x {item_name} to order {order_id}")
    orders = load_orders() # Load all orders
    item_key = item_name.lower()
    item_data = None
    display_name = item_name.title()

    # Find item details
    if item_key in menu_items:
        item_data = menu_items[item_key]
    else:
        for special in daily_specials:
            if item_key == special["name"].lower():
                item_data = special
                display_name = special["name"]
                break

    if not item_data:
        logger.warning(f"Item '{item_name}' not found in menu for order {order_id}.")
        return f"{item_name} not found."

    # Get or create the specific order list
    order_id_str = str(order_id)
    order = orders.setdefault(order_id_str, [])

    # Add items
    items_added_this_call = []
    for _ in range(quantity):
        new_item = {"name": display_name, "price": item_data["price"]}
        order.append(new_item)
        items_added_this_call.append(new_item)

    # Ensure the updated list is in the main dictionary (good practice)
    orders[order_id_str] = order

    # --- Added Logging ---
    logger.debug(f"Order {order_id}: State before saving: {orders.get(order_id_str)}")
    save_orders(orders) # Save the entire updated orders dictionary
    # --- End Added Logging ---

    return f"Added {quantity} {display_name}(s) to order {order_id}."
@tool
def remove_item_from_order(item_name: str, quantity: int = 1, order_id: str = "default") -> str:
    """removes an item from the order"""
    logger.info(f"Attempting to remove {quantity} x {item_name} from order {order_id}")
    orders = load_orders() # Load all orders
    order_id_str = str(order_id)
    item_display = item_name.title() # Match how items are added

    if order_id_str not in orders:
        logger.warning(f"Attempted to remove item from non-existent order {order_id}.")
        return f"No active order {order_id}."

    order = orders[order_id_str]
    initial_count = len(order)
    removed_count = 0
    new_order = []
    items_to_skip = quantity

    # Iterate backwards to safely remove
    for item in reversed(order):
        if item["name"] == item_display and items_to_skip > 0:
            removed_count += 1
            items_to_skip -= 1
        else:
            new_order.append(item)

    # Reverse back to original order and update the main dictionary
    orders[order_id_str] = list(reversed(new_order))

    # --- Added Logging ---
    if removed_count > 0:
        logger.debug(f"Order {order_id}: State before saving after removal: {orders.get(order_id_str)}")
        save_orders(orders) # Save the entire updated orders dictionary
    else:
        logger.debug(f"Order {order_id}: No items removed, skipping save.")
    # --- End Added Logging ---

    # Return appropriate message
    if removed_count == 0:
         logger.warning(f"Item '{item_display}' not found in order {order_id} for removal.")
         return f"{item_display} not found in order {order_id}."
    elif removed_count < quantity:
         logger.warning(f"Removed {removed_count} of {quantity} requested {item_display}(s) from order {order_id}.")
         return f"Removed {removed_count} {item_display}(s) (fewer than requested found)."
    else:
         return f"Removed {removed_count} {item_display}(s) from order {order_id}."

@tool
def get_current_order(order_id: str = "default") -> dict:
    """returns the current order"""
    logger.debug(f"Getting current order for {order_id}")
    orders = load_orders() # Uses the corrected load_orders
    order = orders.get(str(order_id), []) # Ensure order_id is string key
    summary = {}
    for item in order:
        summary[item["name"]] = summary.get(item["name"], 0) + 1
    item_list = [f"{qty} x {name}" for name, qty in summary.items()]
    total = round(sum(item["price"] for item in order), 2)
    logger.debug(f"Order {order_id} summary: Items={item_list}, Total={total}")
    return {"items": item_list, "total": total}

@tool
def calculate_order_total(order_id: str = "default") -> float:
    """Returns the total cost of the specified order_id by summing the prices of all items currently in it."""
    logger.debug(f"Calculating total for order {order_id}")
    try:
        # Use invoke to ensure correct argument passing for the tool
        current_order_details = get_current_order.invoke({"order_id": str(order_id)})
        total = current_order_details.get("total", 0.0)
        logger.debug(f"Calculated total for order {order_id}: {total}")
        return total
    except Exception as e:
        logger.error(f"Error calculating total for order {order_id}: {e}", exc_info=True)
        # Return 0.0 or raise the exception depending on desired behavior
        return 0.0

@tool
def clear_order(order_id: str = "default") -> str:
    """clears the current order"""
    logger.info(f"Clearing order {order_id}")
    orders = load_orders() # Uses the corrected load_orders
    order_id_str = str(order_id) # Ensure order_id is string key
    if order_id_str in orders:
        orders[order_id_str] = []
        save_orders(orders) # Uses the corrected save_orders
        return f"Order {order_id} cleared."
    else:
        logger.warning(f"Attempted to clear non-existent order {order_id}.")
        return f"Order {order_id} not found to clear."

