# Logger utility for application events and raw payloads
import os
import json
import logging
from datetime import datetime
from .config import LOG_FILE, PAYLOADS_DIR

# Configure python standard logger
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_info(msg: str):
    print(f"[*] {msg}")
    logging.info(msg)

def log_warn(msg: str):
    print(f"[!] WARNING: {msg}")
    logging.warning(msg)

def log_error(msg: str):
    print(f"[X] ERROR: {msg}")
    logging.error(msg)

def log_raw_payload(request_id: str, payload_data: dict) -> str:
    """
    Saves the raw JSON payload to a dedicated file named after the request_id.
    """
    filename = f"payload_{request_id}.json"
    filepath = os.path.join(PAYLOADS_DIR, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload_data, f, indent=4)
        log_info(f"Saved raw payload for request {request_id} to {filepath}")
        return filepath
    except Exception as e:
        log_error(f"Failed to save raw payload for request {request_id}: {e}")
        return ""
