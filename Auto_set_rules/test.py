import re
name = "Tate no Yuusha no Nariagari S02 "

season_rules = r'S(\d{0,3}|\d{1,3}\.\d{1,2})'
a = re.match(season_rules, name)
print(a)