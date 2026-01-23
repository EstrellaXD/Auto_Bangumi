import json

import httpx


def load(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save(filename, obj):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4, separators=(",", ": "), ensure_ascii=False)


async def get(url):
    async with httpx.AsyncClient() as client:
        req = await client.get(url)
        return req.json()
