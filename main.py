import os
import csv
import argparse
import requests
import json
from typing import List, Dict, Any, Optional


def build_headers(token: str | None) -> Dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def paged_get(url: str, headers: Dict[str, str], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    page = 1
    while True:
        paged_params = dict(params)
        paged_params["page"] = page
        r = requests.get(url, headers=headers, params=paged_params, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"GitHub API error {r.status_code} at {url}: {r.text[:500]}")
        data = r.json()
        if not data:
            break
        if not isinstance(data, list):
            # Some endpoints may return objects; normalize to list
            data = [data]
        results.extend(data)
        print(f"Fetched page {page}: {len(data)} items")
        if len(data) < params.get("per_page", 100):
            break
        page += 1
    return results


def fetch_issue_comments(comments_url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    return paged_get(comments_url, headers, {"per_page": 100})


def fetch_issues(
    owner: str,
    repo: str,
    token: Optional[str],
    state: str = "all",
    include_prs: bool = False,
) -> List[Dict[str, Any]]:
    """Fetch all issues for a repo, optionally skipping PRs, including all comments."""
    headers = build_headers(token)
    base_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    issues: List[Dict[str, Any]] = []
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
            # Skip pull requests if requested
            if not include_prs and "pull_request" in issue:
                continue
            # Fetch comments for this issue (if any)
            comments_url = issue.get("comments_url")
            comments_count = issue.get("comments", 0) or 0
            comments_data: List[Dict[str, Any]] = []
            if comments_url and comments_count > 0:
                comments_data = fetch_issue_comments(comments_url, headers)
            issue_with_comments = dict(issue)
            issue_with_comments["comments_data"] = comments_data
            issues.append(issue_with_comments)

        page += 1
        if len(batch) < per_page:
            break
    return issues


def to_csv(
    issues: List[Dict[str, Any]],
    csv_path: str,
    delimiter: str = ",",
) -> None:
    """Write a simple CSV for Excel with key issue fields and concatenated comments."""
    def join_list(values: List[str]) -> str:
        return "; ".join(values) if values else ""

    rows = []
    for it in issues:
        labels = [l.get("name", "") for l in (it.get("labels") or [])]
        assignees = [a.get("login", "") for a in (it.get("assignees") or [])]
        author = (it.get("user") or {}).get("login", "")
        comments_data = it.get("comments_data") or []
        comments_text = "\n---\n".join([(c.get("user") or {}).get("login", "") + ": " + (c.get("body") or "") for c in comments_data])
        rows.append(
            {
                "number": it.get("number"),
                "title": it.get("title"),
                "state": it.get("state"),
                "author": author,
                "labels": join_list(labels),
                "assignees": join_list(assignees),
                "comments_count": it.get("comments", 0),
                "created_at": it.get("created_at"),
                "updated_at": it.get("updated_at"),
                "closed_at": it.get("closed_at"),
                "url": it.get("html_url"),
                "comments": comments_text,
            }
        )

    fieldnames = [
        "number",
        "title",
        "state",
        "author",
        "labels",
        "assignees",
        "comments_count",
        "created_at",
        "updated_at",
        "closed_at",
        "url",
        "comments",
    ]
    # Write with BOM for Excel on Windows
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Export GitHub issues (with all comments) to JSON/CSV.")
    parser.add_argument("--owner", default=os.getenv("GITHUB_OWNER"), help="GitHub owner/org (or set GITHUB_OWNER)")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPO"), help="GitHub repository name (or set GITHUB_REPO)")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub token for higher rate limits (optional)")
    parser.add_argument("--state", choices=["all", "open", "closed"], default="all", help="Issue state filter")
    parser.add_argument("--include-prs", action="store_true", help="Include pull requests (treated as issues by API)")
    parser.add_argument("--out-json", default="issues.json", help="Path to write full JSON output")
    parser.add_argument("--out-csv", default="issues.csv", help="Path to write CSV for Excel")
    parser.add_argument("--csv-delimiter", default=",", help="CSV delimiter, e.g., ';' for some locales")
    args = parser.parse_args()

    if not args.owner or not args.repo:
        raise SystemExit("--owner and --repo are required (or set GITHUB_OWNER/GITHUB_REPO)")

    print(f"Exporting issues for {args.owner}/{args.repo} (state={args.state}, include_prs={args.include_prs})")
    issues = fetch_issues(args.owner, args.repo, args.token, args.state, include_prs=args.include_prs)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)
    print(f"Saved JSON: {args.out_json} ({len(issues)} issues)")

    to_csv(issues, args.out_csv, delimiter=args.csv_delimiter)
    print(f"Saved CSV:  {args.out_csv}")


if __name__ == "__main__":
    main()
