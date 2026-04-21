from pymongo import MongoClient
from pathlib import Path


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

    dates = col.distinct("pull_date")
    print("Available dates:", sorted(dates))

    sample = col.find_one()
    if sample:
        print("\nFields:", list(sample.keys())[:10])
        print("Sample ticker:", sample.get("Ticker"))
        print("Sample source:", sample.get("source", "")[:60])

    client.close()


if __name__ == "__main__":
    main()
