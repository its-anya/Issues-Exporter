import os
import csv
import argparse
import requests
import json
from typing import Dict, Any, List, Optional


def build_headers(token: Optional[str]) -> Dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def paged_get(url: str, headers: Dict[str, str], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    page = 1
    while True:
        p = dict(params)
        p["page"] = page
        r = requests.get(url, headers=headers, params=p, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"GitHub API error {r.status_code} at {url}: {r.text[:500]}")
        data = r.json()
        if not data:
            break
        out.extend(data)
        if len(data) < params.get("per_page", 100):
            break
        page += 1
    return out


def fetch_clean(owner: str, repo: str, token: Optional[str], state: str = "all") -> List[Dict[str, Any]]:
    headers = build_headers(token)
    base_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    cleaned: List[Dict[str, Any]] = []
    page = 1
    per_page = 100
    while True:
        params = {"state": state, "per_page": per_page, "page": page}
        print(f"Fetching issues page {page}…")
        r = requests.get(base_url, headers=headers, params=params, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"GitHub API error {r.status_code}: {r.text[:500]}")
        batch = r.json()
        if not batch:
            break
        for issue in batch:
            # Skip PRs
            if "pull_request" in issue:
                continue
            comments = []
            if issue.get("comments", 0):
                comments = paged_get(issue["comments_url"], headers, {"per_page": 100})
            cleaned.append(
                {
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "body": issue.get("body"),
                    "state": issue.get("state"),
                    "labels": [l.get("name") for l in (issue.get("labels") or [])],
                    "assignees": [a.get("login") for a in (issue.get("assignees") or [])],
                    "created_at": issue.get("created_at"),
                    "updated_at": issue.get("updated_at"),
                    "closed_at": issue.get("closed_at"),
                    "comments": [
                        {
                            "author": (c.get("user") or {}).get("login"),
                            "created_at": c.get("created_at"),
                            "body": c.get("body"),
                        }
                        for c in (comments or [])
                    ],
                }
            )
        page += 1
        if len(batch) < per_page:
            break
    return cleaned


def write_csv(cleaned: List[Dict[str, Any]], path: str, delimiter: str = ",") -> None:
    fields = [
        "number",
        "title",
        "state",
        "labels",
        "assignees",
        "created_at",
        "updated_at",
        "closed_at",
        "comments_count",
        "comments_joined",
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=delimiter)
        w.writeheader()
        for it in cleaned:
            comments = it.get("comments") or []
            w.writerow(
                {
                    "number": it.get("number"),
                    "title": it.get("title"),
                    "state": it.get("state"),
                    "labels": "; ".join(it.get("labels") or []),
                    "assignees": "; ".join(it.get("assignees") or []),
                    "created_at": it.get("created_at"),
                    "updated_at": it.get("updated_at"),
                    "closed_at": it.get("closed_at"),
                    "comments_count": len(comments),
                    "comments_joined": "\n---\n".join(
                        [f"{c.get('author')}: {c.get('body') or ''}" for c in comments]
                    ),
                }
            )


def main():
    parser = argparse.ArgumentParser(description="Export cleaned GitHub issues (no PRs) with comments")
    parser.add_argument("--owner", default=os.getenv("GITHUB_OWNER"), help="GitHub owner/org (or set GITHUB_OWNER)")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPO"), help="GitHub repository name (or set GITHUB_REPO)")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub token (optional)")
    parser.add_argument("--state", choices=["all", "open", "closed"], default="all")
    parser.add_argument("--out-json", default="issues_clean.json")
    parser.add_argument("--out-csv", default="issues_clean.csv")
    parser.add_argument("--csv-delimiter", default=",", help="CSV delimiter, e.g., ';'")
    args = parser.parse_args()

    if not args.owner or not args.repo:
        raise SystemExit("--owner and --repo are required (or set GITHUB_OWNER/GITHUB_REPO)")

    data = fetch_clean(args.owner, args.repo, args.token, state=args.state)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    write_csv(data, args.out_csv, delimiter=args.csv_delimiter)
    print(f"✅ Saved {len(data)} cleaned issues to {args.out_json} and {args.out_csv}")


if __name__ == "__main__":
    main()
