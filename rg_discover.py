#!/usr/bin/env python3
"""
DISCOVERY ONLY (step 5). Logs in to the RescueGroups v2 API and prints ONLY
summaries: which object types/actions exist for this login, and how many
DISTINCT values the location fields have. It never prints animal names,
foster names, emails, phones, addresses, passwords, or tokens.
"""
import os
import sys

import requests

URL = "https://api.rescuegroups.org/http/v2.json"
API_KEY = os.environ["RESCUEGROUPS_API_KEY"]
USERNAME = os.environ["RESCUEGROUPS_USERNAME"]
PASSWORD = os.environ["RESCUEGROUPS_PASSWORD"]
ACCOUNT = os.environ["RESCUEGROUPS_ACCOUNT"]


def post(payload):
    r = requests.post(URL, json=payload, timeout=120)
    try:
        return r.json()
    except ValueError:
        return {"status": "not-json", "message": f"HTTP {r.status_code}: {r.text[:120]}"}


def msg(res):
    m = res.get("message") or res.get("messages")
    if isinstance(m, dict):
        texts = [g.get("messageText") for g in m.get("generalMessages", [])]
        return "; ".join(t for t in texts if t) or "(none)"
    return m or "(none)"


login = post({
    "username": USERNAME,
    "password": PASSWORD,
    "accountNumber": int(ACCOUNT) if ACCOUNT.isdigit() else ACCOUNT,
    "action": "login",
})
print("Login status:", login.get("status"), "| message:", login.get("message"))
data = login.get("data", login)
token, token_hash = data.get("token"), data.get("tokenHash")
if not token:
    print("Login did not work. Stopping.")
    sys.exit(1)
auth = {"apikey": API_KEY, "token": token, "tokenHash": token_hash}

# Part A: which object types exist, and what actions does this login have?
print("\nPart A: object types and the actions this login can use")
types = [
    "animals", "contacts", "fosters", "fosterHomes", "persons", "people",
    "reports", "exports", "views", "orgs", "adopters", "foster",
    "animalFosters", "animalContacts", "users", "tasks", "journals",
]
for t in types:
    res = post({**auth, "objectType": t, "objectAction": "define"})
    d = res.get("data")
    if res.get("status") == "ok" and isinstance(d, dict):
        print(f"  {t}: actions = {sorted(d.keys())}")
    else:
        print(f"  {t}: status={res.get('status')} | {msg(res)}")

# Part B: do the location fields hold one value (the rescue's address) or many?
print("\nPart B: distinct value counts for non-adopted animals (counts only)")
records, start = [], 0
while True:
    res = post({**auth, "objectType": "animals", "objectAction": "publicSearch",
                "search": {"resultStart": start, "resultLimit": 250,
                           "resultSort": "animalID", "resultOrder": "asc",
                           "calcFoundRows": "Yes",
                           "filters": [{"fieldName": "animalOrgID", "operation": "equals", "criteria": ACCOUNT}],
                           "fields": ["animalID", "animalStatus", "animalLocation",
                                      "animalLocationCitystate", "animalLocationState"]}})
    if res.get("status") != "ok":
        print("Search error:", msg(res))
        sys.exit(1)
    rows = res.get("data", {})
    page = list(rows.values()) if isinstance(rows, dict) else list(rows)
    records.extend(page)
    start += 250
    if not page or len(records) >= int(res.get("foundRows") or 0):
        break

active = [r for r in records if r.get("animalStatus") != "Adopted"]
print("Non-adopted animals:", len(active))
for f in ["animalLocation", "animalLocationCitystate", "animalLocationState"]:
    print(f"  {f}: {len({str(r.get(f)) for r in active})} distinct value(s)")
