#!/usr/bin/env python3
"""Pull foster-dog data from RescueGroups API v2 and write animals.csv
in the exact column format the UDR foster map already expects.

Env vars (GitHub Actions secrets): RG_API_KEY, RG_USER, RG_PASS, optional RG_ACCOUNT.
Test locally:  RG_API_KEY=... RG_USER=... RG_PASS=... python3 update_animals_csv.py
"""
import csv, json, os, sys, time, urllib.request

URL = "https://api.rescuegroups.org/http/v2.json"
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

def post(payload):
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json",
               "Accept": "application/json",
               "User-Agent": "UDR-foster-map/1.0 (github.com/UnitedDobermanRescue/UDR)"}
    last = None
    for attempt in range(1, 5):
        try:
            req = urllib.request.Request(URL, data, headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:           # dropped connection, timeout, etc.
            last = e
            print(f"  (connection problem, attempt {attempt} of 4: {type(e).__name__})")
            time.sleep(5 * attempt)
    sys.exit(f"Gave up after 4 attempts: {type(last).__name__}")

def main():
    key, user, pw = (os.environ.get(k) for k in ("RG_API_KEY", "RG_USER", "RG_PASS"))
    if not (key and user and pw):
        sys.exit("Missing RG_API_KEY / RG_USER / RG_PASS")
    login_req = {"apikey": key, "action": "login",
                 "username": user, "password": pw}
    if os.environ.get("RG_ACCOUNT"):
        login_req["accountNumber"] = os.environ["RG_ACCOUNT"]

    login = post(login_req)
    if login.get("status") != "ok":
        sys.exit(f"Login failed: {login.get('generalMessages')}")
    token, token_hash = login["data"]["token"], login["data"]["tokenHash"]

    animals, start, limit = [], 0, 100
    while True:
        res = post({"apikey": key, "token": token, "tokenHash": token_hash,
                    "objectType": "animals", "objectAction": "search",
                    "search": {"resultStart": start, "resultLimit": limit,
                               "resultSort": "animalID", "resultOrder": "asc",
                               "fields": API_FIELDS}})
        if res.get("status") != "ok":
            sys.exit(f"Search failed: {res.get('generalMessages')}")
        animals += [a for a in res.get("data", {}).values()
                    if a.get("animalStatus") in STATUSES]
        start += limit
        if start >= int(res.get("foundRows", 0)):
            break

    if not animals:   # never replace a good file with an empty one
        sys.exit("No animals returned; leaving animals.csv untouched")
    animals.sort(key=lambda a: int(a.get("animalID") or 0))

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow([c for c, _ in COLUMNS])
        for a in animals:
            w.writerow(["" if f is None else a.get(f, "") for _, f in COLUMNS])
    print(f"Wrote {len(animals)} animals to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
