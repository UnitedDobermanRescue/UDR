#!/usr/bin/env python3
"""
DISCOVERY ONLY (step 4). Logs in to the RescueGroups v2 API, fetches ALL of
your organization's animals (in pages), and prints ONLY summaries: counts,
status names, and field names.
It never prints animal names, foster names, emails, phones, addresses,
passwords, or tokens (this repo's logs may be public).
"""
import os
import sys
from collections import Counter, defaultdict

import requests

URL = "https://api.rescuegroups.org/http/v2.json"
API_KEY = os.environ["RESCUEGROUPS_API_KEY"]
USERNAME = os.environ["RESCUEGROUPS_USERNAME"]
PASSWORD = os.environ["RESCUEGROUPS_PASSWORD"]
ACCOUNT = os.environ["RESCUEGROUPS_ACCOUNT"]

PAGE = 250
FIELDS = [
    "animalID", "animalName", "animalSpecies", "animalSex",
    "animalStatus", "animalStatusID", "animalNeedsFoster",
    "animalAvailableDate", "animalUpdatedDate",
    "animalLocation", "animalLocationCitystate", "animalLocationState",
    "locationName", "locationCity", "locationState", "locationPostalcode",
    "fosterName",
]
CHECK = [
    "animalNeedsFoster", "animalAvailableDate", "animalLocationCitystate",
    "locationCity", "locationState", "locationPostalcode", "fosterName",
]


def post(payload):
    r = requests.post(URL, json=payload, timeout=120)
    try:
        return r.json()
    except ValueError:
        print("Response was not JSON. HTTP", r.status_code, r.text[:200])
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

records, start, total = [], 0, None
while True:
    res = post({
        "apikey": API_KEY,
        "token": token,
        "tokenHash": token_hash,
        "objectType": "animals",
        "objectAction": "publicSearch",
        "search": {
            "resultStart": start,
            "resultLimit": PAGE,
            "resultSort": "animalID",
            "resultOrder": "asc",
            "calcFoundRows": "Yes",
            "filters": [
                {"fieldName": "animalOrgID", "operation": "equals", "criteria": ACCOUNT}
            ],
            "fields": FIELDS,
        },
    })
    if res.get("status") != "ok":
        print("Search error:", res.get("message") or res.get("messages"))
        sys.exit(1)
    total = res.get("foundRows", total)
    rows = res.get("data", {})
    page = list(rows.values()) if isinstance(rows, dict) else list(rows)
    records.extend(page)
    start += PAGE
    if not page or len(records) >= int(total or 0):
        break

print(f"\nTotal animals fetched: {len(records)} (RescueGroups says {total})")


def filled(rec, key):
    return rec.get(key) not in (None, "", [], {})


print("\nStatuses (count of animals):")
for status, n in Counter(str(r.get("animalStatus")) for r in records).most_common():
    print(f"  {status}: {n}")

groups = defaultdict(list)
for r in records:
    groups[str(r.get("animalStatus"))].append(r)

print("\nFor each status EXCEPT Adopted: how many records have each field filled in")
for status, recs in sorted(groups.items()):
    if status == "Adopted":
        continue
    print(f"\n[{status}] {len(recs)} animals")
    for f in CHECK:
        print(f"  {f}: {sum(1 for r in recs if filled(r, f))} of {len(recs)}")
    needs = Counter(str(r.get("animalNeedsFoster")) for r in recs)
    print("  animalNeedsFoster values:", dict(needs))
