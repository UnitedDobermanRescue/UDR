#!/usr/bin/env python3
"""
DISCOVERY ONLY. Logs in to the RescueGroups v2 API, then prints the STRUCTURE
of what comes back (field names only). It never prints animal data, names,
addresses, passwords, or tokens.
"""
import json
import os
import sys
import requests

URL = "https://api.rescuegroups.org/http/v2.json"
API_KEY = os.environ["RESCUEGROUPS_API_KEY"]
USERNAME = os.environ["RESCUEGROUPS_USERNAME"]
PASSWORD = os.environ["RESCUEGROUPS_PASSWORD"]
ACCOUNT = os.environ["RESCUEGROUPS_ACCOUNT"]


def post(payload):
    r = requests.post(URL, json=payload, timeout=60)
    print("HTTP status:", r.status_code)
    try:
        return r.json()
    except ValueError:
        print("Response was not JSON. First 200 characters:", r.text[:200])
        sys.exit(1)


def key_tree(obj, depth=0, max_depth=3):
    """Return only the key names (and value types), never the values."""
    if isinstance(obj, dict) and depth < max_depth:
        return {k: key_tree(v, depth + 1, max_depth) for k, v in obj.items()}
    if isinstance(obj, list):
        return "list"
    return type(obj).__name__


# Step 1: log in
login = post({
    "username": USERNAME,
    "password": PASSWORD,
    "accountNumber": int(ACCOUNT) if ACCOUNT.isdigit() else ACCOUNT,
    "action": "login",
})
print("Login status:", login.get("status"), "| message:", login.get("message"))
data = login.get("data", login)
token = data.get("token")
token_hash = data.get("tokenHash")
if not token:
    print("No token came back, so login did not work. Stopping.")
    sys.exit(1)
print("Login worked.\n")

auth = {"apikey": API_KEY, "token": token, "tokenHash": token_hash}

# Step 2: what does the 'define' action say? (structure only)
define = post({**auth, "objectType": "animals", "objectAction": "define"})
print("Define status:", define.get("status"), "| message:", define.get("message"))
print("Define structure (key names only):")
print(json.dumps(key_tree(define.get("data", {})), indent=1))

# Step 3: try a PRIVATE search for 1 animal and print only its field names
variants = [
    {"resultStart": 0, "resultLimit": 1, "resultSort": "animalID", "resultOrder": "asc"},
    {"resultStart": 0, "resultLimit": 1, "resultSort": "animalID", "resultOrder": "asc",
     "filters": [{"fieldName": "animalStatus", "operation": "notblank", "criteria": ""}]},
]
for i, search in enumerate(variants, 1):
    print(f"\nPrivate search attempt {i}:")
    res = post({**auth, "objectType": "animals", "objectAction": "search", "search": search})
    print("Status:", res.get("status"), "| message:", res.get("message") or res.get("messages"))
    if res.get("status") != "ok":
        continue
    print("Rows found:", res.get("foundRows"))
    rows = res.get("data", {})
    first = None
    if isinstance(rows, dict) and rows:
        first = next(iter(rows.values()))
    elif isinstance(rows, list) and rows:
        first = rows[0]
    if isinstance(first, dict):
        print(f"\n{len(first)} field names on a private animal record:")
        for name in sorted(first.keys()):
            print(name)
    else:
        print("No animal record came back to inspect.")
    break
