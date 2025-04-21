import os
import random
import logging
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import (
    SystemMessage, HumanMessage, AIMessage,
    ToolMessage, BaseMessage
)

from app.utils.file_db import load_history, save_interaction
from app.utils.tools import (
    get_item_price, get_available_menu_items,
    add_item_to_order, get_current_order,
    calculate_order_total, clear_order,
    get_item_details, get_dietary_information,
    remove_item_from_order, get_daily_specials
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm = ChatGroq(
    temperature=0.7,
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant"
)

tool_map = {
    "get_item_price": get_item_price,
    "get_available_menu_items": get_available_menu_items,
    "add_item_to_order": add_item_to_order,
    "get_current_order": get_current_order,
    "calculate_order_total": calculate_order_total,
    "clear_order": clear_order,
    "get_item_details": get_item_details,
    "get_dietary_information": get_dietary_information,
    "remove_item_from_order": remove_item_from_order,
    "get_daily_specials": get_daily_specials,
}

ORDER_ID_TOOLS = {
    "add_item_to_order",
    "get_current_order",
    "calculate_order_total",
    "clear_order",
    "remove_item_from_order",
}

llm_with_tools = llm.bind_tools(list(tool_map.values()), tool_choice="auto")


async def ask_llm(user_input: str, order_id: str) -> dict:
    if order_id is None:
        order_id = str(random.randint(1000, 9999))
        logger.info(f"Generated new Order ID: {order_id}")

    messages: list[BaseMessage] = [
        SystemMessage(content=f"""
You are a friendly voice assistant at a restaurant managing Order ID: {order_id}.

Your responsibilities:
- Take food & drink orders clearly for Order ID {order_id}.
- Use tools to get item info, prices, dietary facts, and specials. When using tools that modify or read the order (like add, remove, get_current_order, calculate_total, clear), you MUST include the 'order_id': '{order_id}' in your arguments.
- Suggest close matches if item isn't found (e.g. “small soda” → “Soda”).
- Confirm items added/removed. Respond like: "Got it. I've added Margherita Pizza to order {order_id}."
- Repeat back current order and total when asked using the appropriate tool.

🧠 Important Instructions:
- You will be provided with the history of the conversation, alternating between user and assistant messages.
- The **last message** will **always** be the latest **user input**.
- Only respond to the **last user input**, do **not reinterpret** or **respond again** to your own earlier assistant messages.
- If a previous assistant message includes tool output (like total or confirmation), **do not re-confirm or question it again** unless the user does.

⚠️ When user says “order that”, resolve “that” to the last offered/mentioned item and use the add_item_to_order tool.
⚠️ Be concise and friendly.
        """)
    ]

    try:
        history = load_history(order_id)
        for turn in history:
            if turn.get("user"):
                messages.append(HumanMessage(content=turn["user"]))
            if turn.get("assistant") and turn["assistant"].strip():
                messages.append(AIMessage(content=turn["assistant"]))
    except Exception as e:
        logger.warning(f"Order {order_id}: Could not load history: {e}")

    messages.append(HumanMessage(content=user_input))
    final_response_content = "Sorry, I couldn't process that."

    try:
        ai_msg = await llm_with_tools.ainvoke(messages)
        if ai_msg.content and ai_msg.content.strip():
            messages.append(ai_msg)

        if ai_msg.tool_calls:
            logger.info(f"Order {order_id}: Tool calls: {[tc['name'] for tc in ai_msg.tool_calls]}")
            tool_outputs = []

            for tool_call in ai_msg.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_fn = tool_map.get(tool_name)
                output = f"⚠️ Tool '{tool_name}' not found."

                if tool_fn:
                    try:
                        if tool_name in ORDER_ID_TOOLS:
                            tool_args["order_id"] = str(order_id)
                        logger.info(f"Order {order_id}: Running '{tool_name}' with args: {tool_args}")
                        output = str(tool_fn.invoke(tool_args))
                    except Exception as e:
                        output = f"⚠️ Error running tool '{tool_name}': {e}"
                        logger.error(output)

                tool_outputs.append(ToolMessage(content=output, tool_call_id=tool_call["id"]))

            messages.extend(tool_outputs)
            final_msg = await llm.ainvoke(messages)
        else:
            final_msg = ai_msg

        final_response_content = final_msg.content.strip() if final_msg.content else final_response_content
        if final_response_content:
            save_interaction(order_id, user_input, final_response_content)
            logger.info(f"Order {order_id}: Interaction saved.")
        else:
            logger.warning(f"Order {order_id}: No valid response to save.")

    except Exception as e:
        logger.error(f"Order {order_id}: LLM interaction failed: {e}", exc_info=True)

    # 🧾 Fetch actual order from tool
    try:
        order_info = get_current_order({"order_id": order_id})
    except Exception as e:
        logger.warning(f"Order {order_id}: Could not fetch order details: {e}")
        order_info = {"items": [], "total": 0.0}

    return {
        "text": final_response_content,
        "order": order_info
    }
