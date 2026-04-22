import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (optional - won't fail if missing)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-70b-instruct")

# IDX Configuration
IDX_BASE_URL = os.getenv(
    "IDX_BASE_URL", "https://www.idx.co.id/id/perusahaan-tercatat/keterbukaan-informasi"
)

# Output Configuration
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "data/output")
RAW_DIR = os.getenv("RAW_DIR", "data/output/raw")

# Scheduler Configuration
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "8"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
