#!/usr/bin/env python3
"""Pull foster-dog data from RescueGroups API v2 and write animals.csv
in the exact column format the UDR foster map already expects.

Secrets (GitHub Actions): RESCUEGROUPS_API_KEY, RESCUEGROUPS_USERNAME,
RESCUEGROUPS_PASSWORD, RESCUEGROUPS_ACCOUNT.
"""
import csv
import os
import sys
import time

import requests

sys.stdout.reconfigure(line_buffering=True)

URL = "https://api.rescuegroups.org/http/v2.json"
API_KEY = os.environ["RESCUEGROUPS_API_KEY"]
USERNAME = os.environ["RESCUEGROUPS_USERNAME"]
PASSWORD = os.environ["RESCUEGROUPS_PASSWORD"]
ACCOUNT = os.environ["RESCUEGROUPS_ACCOUNT"]

OUTPUT_PATH = "animals.csv"
STATUSES = {"Available", "Intake"}      # statuses your current report shows

# Same header, same order as your existing animals.csv (note the two "Name" columns).
# Each entry: (CSV column, API field or None).  None = left blank on purpose.
COLUMNS = [
    ("Name", "animalName"), ("Status", "animalStatus"), ("Species", "animalSpecies"),
    ("Sex", "animalSex"), ("Days in Foster", "animalDaysInFoster"),
    ("City", "fosterCity"),
    ("Name", None),                      # foster's name: blanked (file is public)
    ("State", "fosterState"), ("Zip/Postal Code", "fosterPostalcode"),
    ("Animal ID", "animalID"), ("Description", "animalDescriptionPlain"),
    ("Energy Level", "animalEnergyLevel"), ("General Age", "animalGeneralAge"),
    ("Good with farm animals", "animalOKWithFarmAnimals"),
    ("Needs companion animal", "animalNeedsCompanionAnimal"),
    ("Needs ongoing medical care", "animalOngoingMedical"),
    ("Not good with female dogs", "animalNoFemaleDogs"),
    ("Not good with large dogs", "animalNoLargeDogs"),
    ("Not good with male dogs", "animalNoMaleDogs"),
    ("Not good with small dogs", "animalNoSmallDogs"),
    ("Notes", None),                     # private notes: blanked (file is public)
    ("OK with Cats", "animalOKWithCats"), ("OK with Dogs", "animalOKWithDogs"),
    ("OK with Kids", "animalOKWithKids"),
    ("Older/ considerate kids only", "animalOlderKidsOnly"),
    ("Primary Breed", "animalPrimaryBreed"),
    ("Protective/ territorial", "animalProtective"),
    ("Reaction to New People", "animalNewPeople"),
    ("Requires a Home with Fence", "animalFence"),
    ("Requires a Yard", "animalYardRequired"),
    ("Secondary Breed", "animalSecondaryBreed"),
    ("Special Needs (description)", "animalSpecialneedsDescription"),
    ("Summary", "animalSummary"),
    ("Video URL 1", None),               # not available in v2 'search'
]
API_FIELDS = sorted({f for _, f in COLUMNS if f})


def post(payload, tries=4):
    # Retry a few times: RescueGroups sometimes drops a connection briefly.
    last_error = None
    for attempt in range(1, tries + 1):
        try:
            r = requests.post(URL, json=payload, timeout=30)
            try:
                return r.json()
            except ValueError:
                return {"status": "not-json",
                        "message": f"HTTP {r.status_code}: {r.text[:120]}"}
        except requests.exceptions.RequestException as e:
            last_error = type(e).__name__
            print(f"  (connection problem, attempt {attempt} of {tries}: {last_error})")
            time.sleep(5 * attempt)
    print(f"Gave up after {tries} attempt(s):", last_error)
    return {"status": "no-response", "message": last_error}


def msg(res):
    m = res.get("message") or res.get("messages")
    if isinstance(m, dict):
        texts = [g.get("messageText") for g in m.get("generalMessages", [])]
        return "; ".join(t for t in texts if t) or "(none)"
    return m or "(none)"


def main():
    login = post({
        "username": USERNAME,
        "password": PASSWORD,
        "accountNumber": int(ACCOUNT) if ACCOUNT.isdigit() else ACCOUNT,
        "action": "login",
    })
    print("Login status:", login.get("status"), "| message:", msg(login))
    data = login.get("data", login)
    token, token_hash = data.get("token"), data.get("tokenHash")
    if not token:
        sys.exit("Login did not work. Stopping.")
    auth = {"token": token, "tokenHash": token_hash}


    
    animals, start, limit = [], 0, 100
    while True:
        res = post({**auth, "objectType": "animals", "objectAction": "search",
                    "search": {"resultStart": start, "resultLimit": limit,
                               "resultSort": "animalID", "resultOrder": "asc",
                               "calcFoundRows": "Yes",
                               "fields": API_FIELDS}})
        if res.get("status") != "ok":
            sys.exit(f"Search failed: {res.get('status')} | {msg(res)}")
        rows = res.get("data", {})
        page = list(rows.values()) if isinstance(rows, dict) else list(rows)
        animals += [a for a in page if a.get("animalStatus") in STATUSES]
        start += limit
        if not page or start >= int(res.get("foundRows") or 0):
            break

    print("Animals kept (Available/Intake):", len(animals))
    if not animals:   # never replace a good file with an empty one
        sys.exit("No animals returned; leaving animals.csv untouched")
    animals.sort(key=lambda a: int(a.get("animalID") or 0))

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow([c for c, _ in COLUMNS])
        for a in animals:
            w.writerow(["" if k is None else a.get(k, "") for _, k in COLUMNS])
    print(f"Wrote {len(animals)} animals to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
