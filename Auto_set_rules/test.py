import re
name = "Tate no Yuusha no Nariagari S02"

season_rules = r'(.*)(S.\d)'
a = re.match(season_rules, name, re.I)
if a is not None:
    print(a.group(1))
    print(a.group(2))
else:
    print(name)