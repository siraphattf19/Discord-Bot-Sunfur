import json
import datetime
import os

LOG_FILE = "user_log.json"

def _load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _save_log(data):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=str)

def log_action(user_id, username, action_type, detail):
    logs = _load_log()
    logs.append({
        "user_id": user_id,
        "username": username,
        "action_type": action_type,
        "detail": detail,
        "timestamp": datetime.datetime.now().isoformat()
    })
    _save_log(logs)

def get_all_user_logs(user_id):
    logs = _load_log()
    return [log for log in logs if log["user_id"] == user_id]