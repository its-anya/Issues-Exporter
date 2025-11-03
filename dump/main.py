import requests, json

OWNER = "its-anya"
REPO = "Cinezy"
TOKEN = ""  # optional – leave empty for public repos
OUTPUT = "issues.json"

headers = {"Accept": "application/vnd.github+json"}
if TOKEN:
    headers["Authorization"] = f"token {TOKEN}"

issues = []
page = 1
per_page = 100

while True:
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/issues"
    params = {"state": "all", "per_page": per_page, "page": page}
    print(f"Fetching page {page}...")
    r = requests.get(url, headers=headers, params=params)
    data = r.json()

    # Stop when no more issues
    if not data or len(data) == 0:
        break

    issues.extend(data)
    page += 1

# Save all issues to a file
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(issues, f, indent=2)

print(f"✅ Saved {len(issues)} issues to {OUTPUT}")
