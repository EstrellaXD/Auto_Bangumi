import re
import sys
import time
import json

import requests
from bs4 import BeautifulSoup
import json

rules = requests.get("https://raw.githubusercontent.com/EstrellaXD/Bangumi_Auto_Collector/main/AutoBangumi2.0/app/rule.json").json()
print(rules)