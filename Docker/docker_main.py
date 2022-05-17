import os
import time
from collect_bangumi_info import collect_info
from rename_qb import rename_main
from auto_set_rule import SetRule

sleep_time = os.environ["TIME"]

if __name__ == "__main__":
    while True:
        collect_info()
        rename_main()
        rule = SetRule()
        rule.set_rule_main()
        time.sleep(float(sleep_time))
