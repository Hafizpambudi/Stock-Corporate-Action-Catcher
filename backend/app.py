import os
from datetime import date as date_type
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pymongo import MongoClient
from pydantic import BaseModel


app = FastAPI(title="IDX News API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def get_mongo_client():
    env_vars = load_env()
    return MongoClient(env_vars["MONGO_URI"])


class NewsItem(BaseModel):
    Ticker: str
    analysis: str
    source: str
    pull_date: str


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(
        Path(__file__).parent.parent / "frontend/templates/index.html",
        "r",
        encoding="utf-8",
    ) as f:
        return f.read()


@app.get("/api/dates")
async def get_dates():
    client = get_mongo_client()
    db = client["idx_news"]
    col = db["Daily_News"]

    dates = col.distinct("pull_date")
    client.close()

    date_list = sorted([d[:10] for d in dates], reverse=True)
    return date_list


@app.get("/api/news/{date}")
async def get_news_by_date(date: str):
    client = get_mongo_client()
    db = client["idx_news"]
    col = db["Daily_News"]

    query_date = f"{date}T00:00:00"
    news = list(col.find({"pull_date": query_date}, {"_id": 0}))
    client.close()

    return news


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)
