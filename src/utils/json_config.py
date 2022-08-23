import json
import requests


def load(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save(filename, obj):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4, separators=(",", ": "), ensure_ascii=False)
    pass


def get(url):
    req = requests.get(url)
    return req.json()