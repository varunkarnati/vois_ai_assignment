import json
import os
from threading import Lock

DB_FILE = "app/utils/session_db.json"
_lock = Lock()

# Ensure file exists
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

def load_history(order_id):
    with _lock:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        return db.get(order_id, [])

def save_interaction(order_id, user_input, model_output):
    with _lock:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                db = json.load(f)
        else:
            db = {}

        history = db.get(order_id, [])
        history.append({
            "user": user_input,
            "assistant": model_output
        })
        db[order_id] = history

        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=2)
