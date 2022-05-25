import json

with open("AutoBangumi/config/rule.json") as f:
    print(json.load(f))