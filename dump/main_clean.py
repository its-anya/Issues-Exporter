import requests, json

OWNER = "its-anya"
REPO = "Cinezy"
TOKEN = ""  # optional – leave empty for public repos
OUTPUT = "issues_clean.json"

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

    # stop if no more data
    if not data or len(data) == 0:
        break

    for issue in data:
        # skip pull requests (they also appear in issues)
        if "pull_request" in issue:
            continue

        issues.append({
            "title": issue.get("title"),
            "body": issue.get("body")
        })

    page += 1

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(issues, f, indent=2, ensure_ascii=False)

print(f"✅ Saved {len(issues)} cleaned issues to {OUTPUT}")
