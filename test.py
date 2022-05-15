import re
import os

file_name = '[Sakurato] Machikado Mazoku 2-choume [06][AVC-8bit 1080P AAC][CHS]'
episode_rules = [r'(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                 r'(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                 r'(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)',
                 r'(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)',
                 r'(.*)第(\d*\.*\d*)话(?:END)?(.*)',
                 r'(.*)第(\d*\.*\d*)話(?:END)?(.*)',
                 r'(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)']


def new_name(name):
    n = re.split(r'\[|\]', name)
    file_name = name.replace(f'[{n[1]}]', '')
    for rule in episode_rules:
        matchObj = re.match(rule, file_name, re.I)
        if matchObj is not None:
            new_name = f'{matchObj.group(1)}E{matchObj.group(2)} {matchObj.group(3)}'
    return new_name


print(new_name(file_name))


