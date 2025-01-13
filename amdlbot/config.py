import json
import os
from os import getenv
from dotenv import load_dotenv
from amdlbot.logging import LOGGER

# Load .env file if it exists (local development)
if os.path.exists("config.env"):
    load_dotenv("config.env")

def get_list_from_env(key: str, default=None):
    value = getenv(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            LOGGER(__name__).error(f"Failed to parse {key} as JSON")
    return default or []

# Core Configuration
API_ID = int(getenv("API_ID", "23028247"))
API_HASH = getenv("API_HASH", "659c5f1124a81ad789a6ea021da73f4d")
BOT_TOKEN = getenv("BOT_TOKEN")
DATABASE_URL = getenv("DATABASE_URL")

# User IDs Configuration
OWNER_USERID = get_list_from_env("OWNER_USERID", [6383913878])
SUDO_USERID = OWNER_USERID.copy()

# Add additional sudo users if configured
additional_sudos = get_list_from_env("SUDO_USERID", [])
if additional_sudos:
    SUDO_USERID.extend(additional_sudos)
    SUDO_USERID = list(set(SUDO_USERID))  # Remove duplicates
