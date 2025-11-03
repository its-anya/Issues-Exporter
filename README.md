# GitHub Issues Exporter (JSON + CSV)

Ek simple tool jo GitHub repo ke issues (aur unke saare comments) export karta hai — JSON aur Excel-friendly CSV dono formats mein.

- No hardcoded username/repo: pass via flags or environment variables
- Exports all issues or filter by state (open/closed/all)
- Optionally include/exclude Pull Requests
- Grabs ALL comments for every issue
- CSV includes UTF-8 BOM for Excel on Windows

## Quick start (Windows PowerShell)

```powershell
# 1) Optional: create virtualenv
python -m venv .venv; .\.venv\Scripts\Activate.ps1

# 2) Install dependency
pip install -r requirements.txt

# 3) Set env vars (optional) for convenience
$env:GITHUB_OWNER = "owner-or-org"
$env:GITHUB_REPO  = "repo-name"
# Optional: to increase rate limits or access private repos
$env:GITHUB_TOKEN = "ghp_...personal_access_token..."

# 4) Export full issues (with comments) to JSON + CSV
python .\main.py --state all --include-prs --out-json issues.json --out-csv issues.csv

# 5) Export a simplified/clean version (no PRs) to JSON + CSV
python .\main_clean.py --state all --out-json issues_clean.json --out-csv issues_clean.csv
```

Notes:
- If you don’t set env vars, pass flags: `--owner <owner> --repo <repo> [--token <token>]`.
- For some Excel locales, use semicolon as delimiter: `--csv-delimiter ";"`.
- Rate limits: unauthenticated = 60 req/hr; with token = 5000 req/hr.

## What gets exported?

- `main.py` (full):
  - All issues (and optionally PRs) with all original fields from the API
  - Plus `comments_data`: array of every comment on that issue
  - CSV fields: number, title, state, author, labels, assignees, counts, dates, URL, and a combined comments text column

- `main_clean.py` (clean):
  - Skips PRs
  - Keeps: number, title, body, state, labels, assignees, dates
  - Comments included as: author, created_at, body
  - Also writes a compact CSV with combined comments text

## CLI examples

- Public repo, open issues only, skip PRs:
```powershell
python .\main_clean.py --owner numpy --repo numpy --state open --out-json open_clean.json --out-csv open_clean.csv
```

- Private repo or high-volume export (requires token):
```powershell
python .\main.py --owner my-org --repo enterprise-repo --token $env:GITHUB_TOKEN --state all --out-json issues.json --out-csv issues.csv
```

- CSV with semicolon delimiter (common in EU locales):
```powershell
python .\main.py --csv-delimiter ';' --out-csv issues_semicolon.csv
```

## How it works

- Issues are fetched from: `GET /repos/{owner}/{repo}/issues`
- Comments are fetched for each issue from: `GET /repos/{owner}/{repo}/issues/{number}/comments`
- Pagination is handled automatically at 100 items/page for both issues and comments
- PRs are represented as issues by the API; use `--include-prs` to include them in `main.py` (they’re excluded in `main_clean.py`)

## Tips for Excel users

- Files are written with `utf-8-sig` BOM for better Excel import on Windows
- If Excel shows all data in one column, pick your delimiter during import (comma by default) or run with `--csv-delimiter ';'`

## Alternative: GitHub CLI (handy for quick CSVs)

If you prefer the official GitHub CLI, you can get a quick CSV of issues:

```powershell
# Install gh from https://cli.github.com/ and login first: gh auth login
# Comma-separated CSV
gh issue list --limit 1000 --state all | % { $_ -replace "`t", "," } | Out-File issues_cli.csv -Encoding utf8
```

To include more fields or JSON:

```powershell
gh issue list --limit 1000 --state all --json number,title,assignees,state,url |
  gh api --method GET -H "Accept: application/vnd.github+json" repos/$env:GITHUB_OWNER/$env:GITHUB_REPO/issues --paginate > issues_cli.json
```

## References and acknowledgements

- "Export all issues and all comments in every GitHub issue" — reminder: comments must be fetched separately via `GET /repos/:owner/:repo/issues/:number/comments`.
- "How can I export GitHub issues to Excel?" — multiple approaches exist; this repo includes JSON+CSV Python exporters and shows a GitHub CLI option.

Useful docs and posts:
- GitHub REST API v3: Issues — https://docs.github.com/rest/issues/issues
- GitHub REST API v3: Issue comments — https://docs.github.com/rest/issues/comments
- GitHub CLI `gh issue list` — https://cli.github.com/manual/gh_issue_list

The referenced Stack Overflow content is licensed under CC BY-SA; see their posts for full context and attributions.

## Troubleshooting

- 404 Not Found: check `--owner`/`--repo` values and that your token has access (for private repos)
- 403 Rate limit exceeded: set `--token` or wait for reset
- Corporate proxies/firewalls: set HTTPS proxy env vars if needed

## License

MIT — do as you like. Contributions welcome.
