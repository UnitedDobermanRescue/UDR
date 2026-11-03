#!/usr/bin/env python3
"""
DISCOVERY ONLY. Logs in to the RescueGroups v2 API and prints the NAMES of the
animal fields available to your account. It never prints any animal data,
names, addresses, or credentials.
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
    r = requests.post(URL, json=payload, timeout=60)
    print("HTTP status:", r.status_code)
    try:
        return r.json()
    except ValueError:
        print("Response was not JSON. First 200 characters:", r.text[:200])
        sys.exit(1)


# Step 1: log in
# Request format taken from RescueGroups' "v2 API login action" guide.
login = post({
    "username": USERNAME,
    "password": PASSWORD,
    "accountNumber": int(ACCOUNT) if ACCOUNT.isdigit() else ACCOUNT,
    "action": "login",
})
print("Login status:", login.get("status"), "| message:", login.get("message") or login.get("messages"))

data = login.get("data", login)
token = data.get("token")
token_hash = data.get("tokenHash")
if not token:
    print("No token came back, so login did not work. Stopping.")
    sys.exit(1)
print("Login worked.")

# Step 2: ask which animal fields exist (names only)
define = post({
    "apikey": API_KEY,
    "token": token,
    "tokenHash": token_hash,
    "objectType": "animals",
    "objectAction": "define",
})
print("Define status:", define.get("status"))

fields = define.get("data", {})
if isinstance(fields, dict):
    names = sorted(fields.keys())
else:
    names = sorted(str(f.get("fieldName", f)) if isinstance(f, dict) else str(f) for f in fields)

print(f"\n{len(names)} animal fields available:")
for n in names:
    print(n)
