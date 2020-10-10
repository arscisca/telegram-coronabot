import json
import re

bot_username = r'@Italia\_CoronaBot'

with open('assets/locations.json', 'r') as f:
    locations = json.load(f)
    country = locations['country']
    regions = set(locations['regions'])
    provinces = set(locations['provinces'])
    location_aliases = locations['aliases']

with open('assets/stats.json', 'r') as f:
    stats = json.load(f)

# Patterns
location = r"[a-z][a-z \-']*?"
date = r"(?:[0-9]+[a-z0-9 \-\\/]+?(?:[0-9]{2,4})?|[a-z' ]+?)"
interval = date + r"\s?-\s?" + date
stat = r"[a-z ]+"

report_request = re.compile(
    "^(" + location + r")(?:,\s?(" + date + "))?$", re.IGNORECASE
)
trend_request = re.compile(
    "^(" + stat + ")" + r"(?:,\s?(" + location + "))?" + r"(?:,\s?(" + interval + "))?$", re.IGNORECASE
)
