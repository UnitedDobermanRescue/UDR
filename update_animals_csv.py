#!/usr/bin/env python3
"""
Pulls current foster animal data from the RescueGroups.org API and writes it
to animals.csv in the same column format the UDR foster map already expects.

Run manually to test:
    RESCUEGROUPS_API_KEY=xxxx python3 update_animals_csv.py

In CI (GitHub Actions), the API key is read from a repo secret.

TODO once the test API response is available:
  1. Confirm the exact endpoint and org ID.
  2. Confirm which filters reproduce your current report (view 844261).
  3. Map the API's response field names to the CSV columns below
     (to_row() is where that translation happens).
"""

import csv
import os
import sys
import requests

API_KEY = os.environ["RESCUEGROUPS_API_KEY"]
API_URL = "https://api.rescuegroups.org/v5/public/animals/search/available"  # TODO: confirm
OUTPUT_PATH = "animals.csv"  # TODO: confirm actual path/filename in the repo

# Columns must match the map's expected CSV header exactly, in this order.
CSV_COLUMNS = [
    "Name", "Status", "Species", "Sex", "Days in Foster", "City", "Name",
    "State", "Zip/Postal Code", "Animal ID", "Description", "Energy Level",
    "General Age", "Good with farm animals", "Needs companion animal",
    "Needs ongoing medical care", "Not good with female dogs",
    "Not good with large dogs", "Not good with male dogs",
    "Not good with small dogs", "Notes", "OK with Cats", "OK with Dogs",
    "OK with Kids", "Older/ considerate kids only", "Primary Breed",
    "Protective/ territorial", "Reaction to New People",
    "Requires a Home with Fence", "Requires a Yard", "Secondary Breed",
    "Special Needs (description)", "Summary", "Video URL 1",
]


def fetch_animals():
    """Call the RescueGroups API and return the parsed JSON response."""
    headers = {"Authorization": API_KEY, "Content-Type": "application/vnd.api+json"}
    resp = requests.get(API_URL, headers=headers, params={"include": "locations"}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def to_row(animal):
    """Map one API animal record to a CSV row matching CSV_COLUMNS. TODO fill in."""
    raise NotImplementedError("Map API fields to CSV_COLUMNS once response shape is known")


def main():
    data = fetch_animals()
    rows = [to_row(a) for a in data.get("data", [])]

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(CSV_COLUMNS)
        writer.writerows(rows)

    print(f"Wrote {len(rows)} animals to {OUTPUT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
