import re
import sys
import time

import requests
from bs4 import BeautifulSoup
import json

url = "https://raw.githubusercontent.com/EstrellaXD/Bangumi_Auto_Collector/main/AutoBangumi2.0/app/rule.json"
try:
    r = requests.get(url)
except ConnectionError:
    print("e")

print(r.text)