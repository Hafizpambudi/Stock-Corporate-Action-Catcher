from pathlib import Path
from pymongo import MongoClient


def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    env_vars = {}
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    env_vars[key] = value.strip('"')
    return env_vars


def main():
    env_vars = load_env()
    client = MongoClient(env_vars["MONGO_URI"])
    db = client["idx_news"]
    col = db["Daily_News"]

    # Check all unique dates
    dates = col.distinct("pull_date")
    print("All dates in DB:", sorted(dates))

    # Test different query formats
    test_dates = [
        "2026-04-21",
        "2026-04-21T00:00:00",
        "2026-04-21T00:00:00.000000",
    ]

    for d in test_dates:
        count = col.count_documents({"pull_date": d})
        print(f"Query '{d}': {count} documents")

    # Try prefix match
    count = col.count_documents({"pull_date": {"$regex": "2026-04-21"}})
    print(f"Regex '2026-04-21': {count} documents")

    client.close()


if __name__ == "__main__":
    main()
