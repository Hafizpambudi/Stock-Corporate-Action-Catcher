import json
import sys
from datetime import datetime
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


def get_result_files(output_dir: str) -> list[Path]:
    output_path = Path(output_dir)
    if not output_path.exists():
        print(f"Output directory not found: {output_dir}")
        return []
    files = sorted(output_path.glob("results_*.json"))
    print(f"Found {len(files)} result files")
    return files


def parse_date_from_filename(filename: str) -> str:
    basename = Path(filename).stem
    date_str = basename.replace("results_", "")
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.isoformat()
    except ValueError:
        return datetime.now().date().isoformat()


def load_results(file_path: Path) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pull_date = parse_date_from_filename(file_path.name)

    for item in data:
        item["pull_date"] = pull_date

    return data


def ingest_to_mongodb(
    mongo_uri: str,
    data: list[dict],
    db_name: str = "idx_news",
    collection_name: str = "Daily_News",
):
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]

    if not data:
        print("No data to ingest")
        return

    result = collection.insert_many(data)
    print(
        f"Inserted {len(result.inserted_ids)} documents into {db_name}.{collection_name}"
    )

    client.close()


def main():
    env_vars = load_env()
    mongo_uri = env_vars.get("MONGO_URI")

    if not mongo_uri:
        print("MONGO_URI not found in .env")
        sys.exit(1)

    output_dir = env_vars.get("OUTPUT_DIR", "data/output")

    files = get_result_files(output_dir)

    all_data = []
    for file_path in files:
        print(f"Loading {file_path.name}...")
        data = load_results(file_path)
        all_data.extend(data)
        print(
            f"  Added {len(data)} documents (pull_date: {data[0]['pull_date'] if data else 'N/A'})"
        )

    if not all_data:
        print("No data found to ingest")
        sys.exit(1)

    print(f"\nTotal documents to ingest: {len(all_data)}")
    ingest_to_mongodb(mongo_uri, all_data)
    print("Done!")


if __name__ == "__main__":
    main()