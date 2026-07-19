# Centralized configuration settings for Coke Can Inspection AI PC Receiver Node
import os

# Application Info
VERSION = "1.0"
APP_NAME = "Coke Can Inspection AI PC Node"

# Network settings
HOST = "0.0.0.0"
PORT = 8000
API_PREFIX = "/api/v1"

# Security (Authentication placeholder)
API_KEYS_ENABLED = False
ALLOWED_API_KEYS = []

# Paths
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# Structured output subdirectories
REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")
DIGITAL_TWINS_DIR = os.path.join(OUTPUT_DIR, "digital_twins")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")
PAYLOADS_DIR = os.path.join(OUTPUT_DIR, "payloads")
INSPECTIONS_DIR = os.path.join(OUTPUT_DIR, "inspections")
CROPS_DIR = os.path.join(OUTPUT_DIR, "crops")

# Create all folders
for folder in [REPORTS_DIR, DIGITAL_TWINS_DIR, LOGS_DIR, PAYLOADS_DIR, INSPECTIONS_DIR, CROPS_DIR]:
    os.makedirs(folder, exist_ok=True)

# Application Settings
ACCEPTANCE_MAX_SCRATCHES = 3
ACCEPTANCE_CRITICAL_DENT_CONF = 0.80
DATABASE_FILE = os.path.join(INSPECTIONS_DIR, "inspection_history.json")
LOG_FILE = os.path.join(LOGS_DIR, "app.log")
