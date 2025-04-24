import os
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.utils.tools import (
    get_item_price,
    get_item_details,

    get_available_menu_items,

    add_item_to_order,
    remove_item_from_order,
    get_current_order,
    calculate_order_total,

)

load_dotenv()

# === OpenAI/Groq Configuration ===
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    # base_url=os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
)

MODEL = "gpt-4.1"  # use a Groq-supported one like llama3 if needed

# === Function Schemas ===
functions = [
    {
        "name": "get_item_price",
        "description": "Returns the price of a specific menu item.",
        "parameters": {
            "type": "object",
            "properties": {"item_name": {"type": "string"}},
            "required": ["item_name"]
        }
    },
    {
        "name": "get_item_details",
        "description": "Returns a description of a menu item.",
        "parameters": {
            "type": "object",
            "properties": {"item_name": {"type": "string"}},
            "required": ["item_name"]
        }
    },
    
    {
        "name": "get_available_menu_items",
        "description": "Lists all available menu items.",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}}
    },
    {
        "name": "add_item_to_order",
        "description": "Adds an item to the current order.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string"},
                "quantity": {"type": "integer", "default": 1},
                "order_id": {"type": "string"}
            },
            "required": ["item_name", "order_id"]
        }
    },
    {
        "name": "remove_item_from_order",
        "description": "Removes an item from the current order.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string"},
                "quantity": {"type": "integer", "default": 1},
                "order_id": {"type": "string"}
            },
            "required": ["item_name", "order_id"]
        }
    },
    {
        "name": "get_current_order",
        "description": "Returns the current order items and total.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"]
        }
    },
    {
        "name": "calculate_order_total",
        "description": "Returns the total price for the current order.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"]
        }
    },

]

# === Local Dispatch Map ===
function_map = {
    "get_item_price": get_item_price,
    "get_item_details": get_item_details,

    "get_available_menu_items": get_available_menu_items,

    "add_item_to_order": add_item_to_order,
    "remove_item_from_order": remove_item_from_order,
    "get_current_order": get_current_order,
    "calculate_order_total": calculate_order_total,

}

# === Main Handler ===
async def ask_llm(user_input: str, order_id: str) -> dict:
    messages = [
        {"role": "system", "content": f"""
You are OrderBot, a restaurant ordering assistant for Order ID: {order_id}. Your job is to help customers place and review their food orders using the provided tools. You should always confirm additions immediately and avoid repeating already confirmed orders unless asked.

RULES YOU MUST FOLLOW:
-----------------------
1. **NEVER assume prices or menu items.** You must always use the provided tools like `get_item_price`, `get_available_menu_items`, etc.
2. **ALWAYS confirm added items** right after adding them. Do not delay confirmation or re-summarize unless asked.
3. **NEVER repeat the entire menu** unless the user specifically asks "what’s on the menu" or "list everything".
4. If the user re-mentions items already added, assume they are **confirming** and politely acknowledge without re-adding.
5. If the user says something vague like "the usual", "order that", or "get me one", clarify **which item** they're referring to based on conversation history.
6. Always keep track of confirmed items. If the user says "that's it", summarize what’s in the order using `get_current_order`.
7. If the assistant message begins with a list of menu items but an order has already been placed, assume it’s a mistake and respond naturally, e.g., "Looks like you've already ordered — would you like to add more?"
8. **Ignore non-food phrases, sound cues, or background noise** that might appear in transcripts (like “music”, “crinkling paper”, “uh”, “hmm”, etc.). These are NOT valid items. Only consider known food items when modifying the order.

9. **NEVER add items that aren’t found in the menu or specials** via the tools. If a word or phrase is not recognized through `get_available_menu_items` or `get_daily_specials`, ask for clarification.

TONE & STYLE:
-------------
- Be friendly, casual, and helpful.
- Use variations when confirming (e.g., “Got it! Added your cheeseburger.” or “Sure thing! 1 Margherita coming up.”).
- When asked for price or item info, acknowledge: “Let me check that...”
- Do not sound robotic. Avoid overly formal confirmations like "You have ordered".

Remember: always use the tools to **read or modify** the order. Do not assume or store order info yourself.
"""},
        {"role": "user", "content": user_input}
    ]

    # 1. Ask model to see if it wants to use a function
    initial = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        functions=functions,
        function_call="auto"
    )

    choice = initial.choices[0].message

    if choice.function_call:
        fn_name = choice.function_call.name.strip().split()[0].split("/")[0]

        raw_args = choice.function_call.arguments
        args = json.loads(raw_args)

        # Auto-inject order_id if needed
        

        result = function_map[fn_name](**args)  # ✅ correct


        # 2. Send tool result back to model
        messages.append({"role": "assistant", "function_call": {
            "name": fn_name,
            "arguments": raw_args
        }})
        messages.append({"role": "function", "name": fn_name, "content": str(result)})

        followup = await client.chat.completions.create(
            model=MODEL,
            messages=messages
        )

        final_response = followup.choices[0].message.content
    else:
        final_response = choice.content

    
    order_summary = get_current_order(order_id)
    

    return {
        "text": final_response,
        "order": order_summary
    }
