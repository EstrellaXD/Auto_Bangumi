import re

import requests

url = "http://192.168.200.2"
try:
    r = requests.get(url)
    print(r.content)
except ConnectionError:
    print("e")
except KeyboardInterrupt:
    print("end")

