#!/usr/bin/env python
"""Interactive MongoDB Atlas connection test - uses Atlas-provided connection string."""

import sys
import os
from pathlib import Path


def main():
    print("=" * 60)
    print("MongoDB Atlas Connection Diagnostic")
    print("=" * 60)
    print("\nSince TLS handshake keeps failing, let's test with the")
    print("EXACT connection string from your Atlas console.\n")

    print("INSTRUCTIONS:")
    print("1. Go to https://cloud.mongodb.com")
    print("2. Navigate to: Database > Connect > Drivers")
    print("3. Copy the connection string (starts with mongodb+srv://...)")
    print("4. Paste it below when prompted\n")

    # Try to load existing for reference
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().startswith("MONGO_URI="):
                    current = line.split("=", 1)[1].strip()
                    print(f"Current .env MONGO_URI: {current[:60]}...")

    # Ask user for input
    print("\n" + "=" * 60)
    new_uri = input("Paste NEW mongodb+srv:// connection string here:\n> ").strip()

    if not new_uri:
        print("No input provided, exiting.")
        sys.exit(1)

    # Save to .env
    print(f"\nSaving new MONGO_URI to .env...")

    # Read existing .env
    env_lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            env_lines = f.readlines()

    # Replace MONGO_URI line
    new_env_lines = []
    for line in env_lines:
        if line.strip().startswith("MONGO_URI="):
            new_env_lines.append(f'MONGO_URI="{new_uri}"\n')
        else:
            new_env_lines.append(line)

    # Write back
    with open(env_path, "w") as f:
        f.writelines(new_env_lines)

    print("Saved! Now testing connection...")

    # Test with pymongo
    try:
        from pymongo import MongoClient
        from pymongo.errors import ServerSelectionTimeoutError

        client = MongoClient(
            new_uri,
            serverSelectionTimeoutMS=15000,
            connectTimeoutMS=15000,
            retryWrites=True,
        )
        # Ping
        client.admin.command("ping")
        print("\n✓ SUCCESS! Connected to MongoDB!")

        # Show databases
        dbs = client.list_database_names()
        print(f"Databases: {dbs}")

        client.close()

    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nCommon fixes:")
        print("- Check username/password in connection string")
        print("- Make sure IP is whitelisted in Atlas")
        print("- Check cluster status in Atlas console")


if __name__ == "__main__":
    main()
