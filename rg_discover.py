#!/usr/bin/env python3
"""
DISCOVERY ONLY (step 3). Logs in to the RescueGroups v2 API, runs a
publicSearch for your organization's animals using the login token, and
prints ONLY summaries: counts, status names, and field names.
It never prints animal names, foster names, emails, phones, addresses,
passwords, or tokens (this repo's logs may be public).
"""
import os
import sys
from collections import Counter

import requests

URL = "https://api.rescuegroups.org/http/v2.json"
API_KEY = os.environ["RESCUEGROUPS_API_KEY"]
USERNAME = os.environ["RESCUEGROUPS_USERNAME"]
PASSWORD = os.environ["RESCUEGROUPS_PASSWORD"]
ACCOUNT = os.environ["RESCUEGROUPS_ACCOUNT"]

FIELDS = [
    "animalID", "animalName", "animalSpecies", "animalSex",
    "animalStatus", "animalStatusID", "animalNeedsFoster",
    "animalAvailableDate", "animalUpdatedDate",
    "animalLocation", "animalLocationCitystate", "animalLocationState",
    "locationName", "locationCity", "locationState", "locationPostalcode",
    "fosterName",
]


def post(payload):
    r = requests.post(URL, json=payload, timeout=120)
    print("HTTP status:", r.status_code)
    try:
        return r.json()
    except ValueError:
        print("Response was not JSON. First 200 characters:", r.text[:200])
        sys.exit(1)


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
print("Login worked.\n")

res = post({
    "apikey": API_KEY,
    "token": token,
    "tokenHash": token_hash,
    "objectType": "animals",
    "objectAction": "publicSearch",
    "search": {
        "resultStart": 0,
        "resultLimit": 500,
        "resultSort": "animalID",
        "resultOrder": "asc",
        "calcFoundRows": "Yes",
        "filters": [
            {"fieldName": "animalOrgID", "operation": "equals", "criteria": ACCOUNT}
        ],
        "fields": FIELDS,
    },
})
print("Search status:", res.get("status"), "| message:", res.get("message") or res.get("messages"))
if res.get("status") != "ok":
    sys.exit(1)

print("Rows found (total):", res.get("foundRows"))
rows = res.get("data", {})
records = list(rows.values()) if isinstance(rows, dict) else list(rows)
print("Records returned in this call:", len(records))
if not records:
    sys.exit(0)


def filled(rec, key):
    v = rec.get(key)
    return v not in (None, "", [], {})


print("\nStatuses (count of animals):")
for status, n in Counter(str(r.get("animalStatus")) for r in records).most_common():
    print(f"  {status}: {n}")

print("\nanimalNeedsFoster values (count):")
for val, n in Counter(str(r.get("animalNeedsFoster")) for r in records).most_common():
    print(f"  {val}: {n}")

print("\nHow many records have each field filled in (counts only):")
for f in FIELDS:
    print(f"  {f}: {sum(1 for r in records if filled(r, f))} of {len(records)}")

print("\nField names present on the first record:")
for name in sorted(records[0].keys()):
    print(" ", name)
