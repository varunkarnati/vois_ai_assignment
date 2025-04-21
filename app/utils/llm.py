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
# Ensure logging level is DEBUG to see the new messages
logging.basicConfig(level=logging.DEBUG) # <-- Set to DEBUG
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

llm_with_tools = llm.bind_tools(list(tool_map.values()), tool_choice="any")


async def ask_llm(user_input: str, order_id: str) -> dict:
    if order_id is None:
        # This part seems unused in WebSocket flow but safe to keep
        order_id = str(random.randint(1000, 9999))
        logger.info(f"Generated new Order ID: {order_id}")

    # llm.py (inside ask_llm function)

    # llm.py (inside ask_llm function)

    # llm.py (inside ask_llm function)

    # llm.py (replace the entire SystemMessage content)

    messages: list[BaseMessage] = [
        SystemMessage(content=f"""
################################################################################
# ROLE: OrderBot - Restaurant Voice Ordering Assistant                      #
################################################################################

You are "OrderBot", a specialized AI voice assistant operating for Order ID: **{order_id}**. Your function is to manage this customer's order accurately and efficiently using provided tools. Sound friendly, helpful, and **natural** in your conversation.

################################################################################
# CORE DIRECTIVE: Tool-Driven Order Management                               #
################################################################################

1.  **Accuracy First:** Accurately capture requests and reflect them using tools.
2.  **Tools Are Mandatory:** **MUST** use tools for ALL menu info and order modifications (add/remove/check/total/clear). **DO NOT** guess or answer from memory.
3.  **`order_id` is NON-NEGOTIABLE:** **MUST** include `'order_id': '{order_id}'` for tools: `add_item_to_order`, `remove_item_from_order`, `get_current_order`, `calculate_order_total`, `clear_order`.

################################################################################
# TOOL USAGE PROTOCOLS                                                       #
################################################################################

**A. Information Retrieval:**
    *   Use `get_available_menu_items`, `get_daily_specials` for general menu/specials questions.
    *   Use `get_item_price`, `get_item_details`, `get_dietary_information` for specific item details.

**B. Order Status:**
    *   Use `get_current_order` ONLY when asked: "What's my order?", "Read it back?", etc.
    *   Use `calculate_order_total` ONLY when asked: "What's the total?", "How much?", etc.

**C. Order Modification:**

    **C.1. `add_item_to_order` - CRITICAL PROTOCOL:**
        *   **TRIGGER:** **ANY TIME** user clearly wants to add an item ("I want...", "Order...", "Add...", "I'll have...", "Get me...", "[Item], please").
        *   **MANDATORY ACTION:** **MUST** call `add_item_to_order` tool. **NO EXCEPTIONS.**
        *   **NO SHORTCUTS:** Do **NOT** just confirm textually without the tool call. Confirmation follows the *successful* tool result.
        *   **SEQUENTIAL ADDS:** Applies **every time**, even after just adding something. New item request = new tool call.
        *   **"Order That":** Resolve "that" to the last discussed item and call the tool.
        *   **QUANTITY:** Assume 1 unless specified. Pass correct quantity.
        *   **EXAMPLE WORKFLOW (Adding Soda):**
            1.  User: "Add a soda."
            2.  Your thought: User wants 'soda'. MUST use `add_item_to_order`.
            3.  Generate tool call: `AIMessage(..., tool_calls=[{{'name': 'add_item_to_order', 'args': {{'item_name': 'soda', 'quantity': 1, 'order_id': '{order_id}'}}, 'id': 'call_xyz'}}])`
            4.  System executes, gets result: `ToolMessage(content='Added 1 Soda(s) to order {order_id}.', tool_call_id='call_xyz')`
            5.  Receive `ToolMessage`.
            6.  Formulate **natural** response based on `ToolMessage`: **"Okay, got that soda added for you!"** (See RESPONSE STYLE section for more examples)

    **C.2. `remove_item_from_order`:**
        *   **TRIGGER:** User asks to remove item(s).
        *   **MANDATORY ACTION:** Call `remove_item_from_order` with `item_name`, `quantity`, and `order_id='{order_id}'`.
        *   **CONFIRMATION:** Confirm naturally based on the tool's result message (e.g., "Alright, I've removed the fries.").

    **C.3. `clear_order`:**
        *   **TRIGGER:** User asks to clear/cancel/restart the order.
        *   **MANDATORY ACTION:** Call `clear_order` with `order_id='{order_id}'`.
        *   **CONFIRMATION:** Confirm naturally based on the tool's result (e.g., "Okay, I've cleared your order. Ready to start again?").

################################################################################
# CONVERSATION MANAGEMENT                                                    #
################################################################################

1.  **History Context:** Use provided history (`HumanMessage`, `AIMessage`, `ToolMessage`).
2.  **Focus:** Respond **ONLY** to the latest `HumanMessage`.
3.  **Trust Prior Confirmations:** Assume previous tool-based confirmations succeeded unless the user indicates otherwise. Don't re-ask.
4.  **Tool Result Integration:** **MUST** use `ToolMessage` output for your response. Convert raw output (list, price, confirmation, error) into a **natural, conversational sentence.**
    *   *Example (Good):* `ToolMessage("Item 'xyz' not found.")` -> "Hmm, I don't see 'xyz' on our menu right now. We do have [Suggest Alternative] though, or I can list our specials?"
    *   *Example (Bad):* `ToolMessage("Item 'xyz' not found.")` -> "Item 'xyz' not found."

################################################################################
# HANDLING ISSUES & AMBIGUITY                                                #
################################################################################

1.  **Item Not Found:** If tool says item not found, inform politely, maybe suggest alternatives. (See example above).
2.  **Tool Errors:** If `ToolMessage` shows an error, respond gracefully: "Oops, I had a little trouble accessing that just now. Could you try asking that again?" (Do not expose raw errors).
3.  **Vague Requests:** Ask for clarification if the request is unclear ("Give me the usual"). Don't guess.

################################################################################
# RESPONSE STYLE & TONE (Make it Natural!)                                   #
################################################################################

*   **Persona:** Friendly, helpful, and **natural conversationalist**. Aim for clear and concise, but **avoid sounding robotic or overly formal.**
*   **Tone:** Positive, welcoming, and efficient.
*   **Use Contractions:** Freely use contractions like "I've", "it's", "you're", "what's", "let's", etc., just like in normal speech.
*   **Vary Phrasing:** **CRITICAL:** **Do not** use the exact same sentence structure every time, especially for confirmations. Mix it up!
    *   *Instead of always:* "Okay, I've added [Item] to order {order_id}."
    *   *Try variations like:* "Alright, one [Item] coming right up!", "Got that [Item] added for you!", "Sure thing, [Item] is now on your order.", "Okay, added the [Item]!", "You got it, [Item] has been added."
*   **Smooth Transitions:** Use natural transition words/phrases like "Okay,", "Alright,", "Sure,", "Got it,", "Let me check that for you...", "Sure thing..." where appropriate.
*   **Acknowledge Requests:** Before providing info from a tool, briefly acknowledge: "Sure, I can check the price...", "Let me pull up the menu...", "Okay, looking up the details for the veggie burger..."
*   **Be Polite:** Use polite phrasing naturally.

**FINAL REMINDER:** You are OrderBot for Order ID **{order_id}**. Follow tool protocols precisely, but communicate the results in a friendly, natural way.
        """)
    ]
    


    try:
        history = load_history(order_id)
        for turn in history:
            if turn.get("user"):
                messages.append(HumanMessage(content=turn["user"]))
            if turn.get("assistant") and turn["assistant"].strip():
                # Ensure AIMessages added to history don't include tool calls if they exist
                # This might simplify history for subsequent calls, though LangChain should handle it.
                # Let's keep it simple for now and add the full assistant message.
                messages.append(AIMessage(content=turn["assistant"]))
    except Exception as e:
        logger.warning(f"Order {order_id}: Could not load history: {e}")

    messages.append(HumanMessage(content=user_input))
    final_response_content = "Sorry, I had trouble processing that request." # Default response

    try:
        logger.debug(f"Order {order_id}: Messages before first LLM call: {messages}")
        ai_msg = await llm_with_tools.ainvoke(messages) # First call
        logger.debug(f"Order {order_id}: Raw ai_msg from first LLM call: {ai_msg}")

        # Store the initial AI response content IF it exists, before potentially overwriting final_response_content
        initial_ai_content = ai_msg.content.strip() if ai_msg.content else None

        if ai_msg.tool_calls:
            logger.info(f"Order {order_id}: Tool calls detected: {[tc['name'] for tc in ai_msg.tool_calls]}")
            # Append the AIMessage with the tool call request to the history for the next LLM call
            messages.append(ai_msg)

            tool_outputs = []
            for tool_call in ai_msg.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_fn = tool_map.get(tool_name)
                output = f"⚠️ Tool '{tool_name}' not found."

                if tool_fn:
                    try:
                        # Ensure order_id is passed if needed
                        if tool_name in ORDER_ID_TOOLS:
                            if "order_id" not in tool_args:
                                logger.warning(f"Order {order_id}: Automatically adding missing order_id to tool '{tool_name}'")
                            tool_args["order_id"] = str(order_id) # Ensure it's always added/overwritten correctly

                        logger.info(f"Order {order_id}: Running '{tool_name}' with args: {tool_args}")
                        # Use invoke, assuming tools are synchronous for now
                        tool_result = tool_fn.invoke(tool_args)
                        output = str(tool_result) # Convert result to string for ToolMessage
                        logger.debug(f"Order {order_id}: Tool '{tool_name}' output: {output}")

                    except Exception as e:
                        output = f"⚠️ Error running tool '{tool_name}': {e}"
                        logger.error(output, exc_info=True) # Log exception details

                tool_outputs.append(ToolMessage(content=output, tool_call_id=tool_call["id"]))

            messages.extend(tool_outputs) # Add ToolMessage(s) to history

            # --- Second LLM Call ---
            logger.debug(f"Order {order_id}: Messages before second LLM call: {messages}")
            final_msg = await llm.ainvoke(messages) # Second call - gets response based on tool output
            logger.debug(f"Order {order_id}: Raw final_msg from second LLM call: {final_msg}")
            # --- End Second LLM Call ---

            # Use the content from the second call
            final_response_content = final_msg.content.strip() if final_msg.content else "Okay, I've processed that." # Fallback if LLM gives empty response after tool call

        else:
            # No tool calls, use the content from the first call
            logger.info(f"Order {order_id}: No tool calls detected.")
            final_msg = ai_msg # Not strictly needed, but for consistency
            if initial_ai_content:
                 final_response_content = initial_ai_content
            # else: keep the default "Sorry..." message if the first call also had no content

        # Ensure we have *some* response
        if not final_response_content:
             logger.warning(f"Order {order_id}: Final response content is empty, using default.")
             final_response_content = "I'm sorry, I couldn't generate a specific response for that."


        # Save interaction (only if there was valid user input and a response)
        if user_input and final_response_content:
            save_interaction(order_id, user_input, final_response_content)
            logger.info(f"Order {order_id}: Interaction saved.")
        else:
            logger.warning(f"Order {order_id}: No valid interaction to save (Input: '{user_input}', Response: '{final_response_content}').")

    except Exception as e:
        logger.error(f"Order {order_id}: LLM interaction failed: {e}", exc_info=True)
        # Keep the default "Sorry..." message set at the start of the try block

    # 🧾 Fetch actual order from tool (using corrected invoke)
    order_info = {"items": [], "total": 0.0} # Default value
    try:
        logger.debug(f"Order {order_id}: Manually invoking get_current_order tool for final state.")
        # Ensure order_id is passed as string in the dictionary key
        order_info = get_current_order.invoke({"order_id": str(order_id)})
        logger.debug(f"Order {order_id}: Fetched final order info: {order_info}")
    except Exception as e:
        logger.error(f"Order {order_id}: Could not fetch final order details via invoke: {e}", exc_info=True)
        # Keep the default empty order_info on error

    logger.debug(f"Order {order_id}: Returning text: '{final_response_content}', order: {order_info}")
    return {
        "text": final_response_content,
        "order": order_info
    }
