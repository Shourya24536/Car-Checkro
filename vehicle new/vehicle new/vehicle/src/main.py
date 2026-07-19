# AI PC Receiver Bootloader (Entry Point)
import os
import sys
import time
import threading
import webbrowser

# Resolve paths
src_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(src_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.config import HOST, PORT
from src.logger import log_info, log_error
from src.inspection_manager import InspectionManager
from src.http_receiver import app

def open_dashboard():
    """
    Waits briefly for Flask to bind to port and launches default browser.
    """
    time.sleep(1.5)
    url = f"http://127.0.0.1:{PORT}/dashboard"
    log_info(f"Launching Chrome dashboard at: {url}")
    webbrowser.open(url)

def main():
    log_info("==================================================")
    log_info("   Coke Can Inspection AI PC Receiver Node PoC    ")
    log_info("==================================================")
    
    # 1. Initialize Event Coordinator
    try:
        manager = InspectionManager()
    except Exception as e:
        log_error(f"Failed to initialize InspectionManager: {e}")
        sys.exit(1)

    # 2. Register coordinator inside Flask app context
    app.config["INSPECTION_MANAGER"] = manager

    # 3. Spawn background browser launcher thread
    threading.Thread(target=open_dashboard, daemon=True).start()

    # 4. Start Flask HTTP Receiver on primary thread (blocks)
    log_info(f"Starting Flask Receiver Node on http://{HOST}:{PORT}")
    try:
        app.run(host=HOST, port=PORT, debug=False, threaded=True)
    except KeyboardInterrupt:
        log_info("Shutdown signal received. Exiting...")
    except Exception as run_err:
        log_error(f"Server runtime error: {run_err}")

if __name__ == "__main__":
    main()