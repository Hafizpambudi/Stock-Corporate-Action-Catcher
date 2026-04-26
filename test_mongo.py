import os
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

MONGO_URI = os.getenv("MONGO_URI")
print(f"MONGO_URI: {MONGO_URI}")

if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
        client.admin.command("ping")
        print("✓ SUCCESS! Connected to MongoDB!")

        # Show databases
        dbs = client.list_database_names()
        print(f"Databases: {dbs}")

        # Check if idx_news exists
        if "idx_news" in dbs:
            db = client["idx_news"]
            collections = db.list_collection_names()
            print(f"Collections in idx_news: {collections}")
            if "Daily_News" in collections:
                count = db["Daily_News"].count_documents({})
                print(f"Documents in Daily_News: {count}")
        else:
            print("idx_news database does not exist")

        client.close()

    except Exception as e:
        print(f"✗ Connection failed: {e}")
else:
    print("MONGO_URI not set")