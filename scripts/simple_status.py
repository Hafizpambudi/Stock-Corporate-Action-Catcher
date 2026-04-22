#!/usr/bin/env python
"""Simple MongoDB status check - prints what's happening."""

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from pathlib import Path


def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().startswith("MONGO_URI="):
                    return line.split("=", 1)[1].strip().strip('"')
    return None


def main():
    uri = load_env()
    if not uri:
        print("MONGO_URI not found")
        return

    print(f"Testing connection to: {uri[:50]}...")

    # Different connection options to try
    options_list = [
        {"serverSelectionTimeoutMS": 10000},
        {"serverSelectionTimeoutMS": 10000, "directConnection": True},
    ]

    for opts in options_list:
        try:
            print(f"\nTrying: {opts}")
            client = MongoClient(uri, **opts)

            # Get topology info
            topology = client._topology
            print(f"  Topology type: {topology.description.topology_type.name}")

            # List servers
            for sd in topology.description.server_descriptions.values():
                print(f"  {sd.address}: {sd.server_type.name} - {sd.error or 'OK'}")

            client.close()
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    main()
