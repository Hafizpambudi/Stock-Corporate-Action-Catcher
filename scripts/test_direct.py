#!/usr/bin/env python
"""Test MongoDB direct connection."""

from pymongo import MongoClient
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
with open(env_path) as f:
    for line in f:
        if line.strip().startswith("MONGO_URI="):
            uri = line.split("=", 1)[1].strip().strip('"')

print(f"URI: {uri}")

client = MongoClient(uri, serverSelectionTimeoutMS=15000)
client.admin.command("ping")
print("SUCCESS! Connected")
print("Databases:", client.list_database_names())
client.close()
