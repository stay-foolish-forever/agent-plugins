---
name: check-github-issues
description: Scan all open issues in a user-specified GitHub repository and generate a structured report. Use when the user asks to check, list, or summarize open issues for a GitHub repo.
license: MIT
metadata:
  author: everlearner
  version: "1.0.0"
---

# Check GitHub Issues

Scan all open issues in a specified GitHub repository and generate a comprehensive report.

## Usage

When the user asks to check GitHub issues for a repository, follow these steps:

### 1. Determine the Repository

Ask the user for the repository in `owner/repo` format if not already provided (e.g., `facebook/react`, `vercel/next.js`).

### 2. Fetch Open Issues

Use the GitHub CLI (`gh`) to fetch all open issues:

```bash
gh issue list --repo <owner/repo> --state open --limit 100 --json number,title,author,labels,createdAt,updatedAt,assignees,comments,url
```

If `gh` is not available or not authenticated, fall back to the GitHub REST API:

```bash
curl -s "https://api.github.com/repos/<owner/repo>/issues?state=open&per_page=100" | python3 -c "
import sys, json
issues = json.load(sys.stdin)
# Filter out pull requests (GitHub API includes PRs in issues endpoint)
issues = [i for i in issues if 'pull_request' not in i]
for i in issues:
    labels = ', '.join([l['name'] for l in i.get('labels', [])])
    assignees = ', '.join([a['login'] for a in i.get('assignees', [])])
    print(json.dumps({
        'number': i['number'],
        'title': i['title'],
        'author': i['user']['login'],
        'labels': labels,
        'created_at': i['created_at'],
        'updated_at': i['updated_at'],
        'assignees': assignees,
        'comments': i['comments'],
        'url': i['html_url']
    }))
"
```

### 3. Generate the Report

Produce a well-structured report with the following sections:

#### Report Structure

1. **Summary** — Total number of open issues, date of report, repository name
2. **Label Distribution** — Breakdown of issues by label (e.g., bug: 12, enhancement: 8, documentation: 3)
3. **Issues Table** — A table listing all open issues with columns:
   - `#` (issue number, linked to URL)
   - Title
   - Author
   - Labels
   - Assignees
   - Comments count
   - Age (how long ago the issue was created)
4. **Stale Issues** — Highlight issues with no activity in the last 30 days
5. **Unassigned Issues** — List issues that have no assignees
6. **Most Active Issues** — Top 5 issues by comment count

## Notes

- If the repository has more than 100 open issues, note the total count and mention that only the first 100 are shown in the report.
- Respect GitHub API rate limits. If unauthenticated, the limit is 60 requests/hour.
- If the repository is private, `gh` CLI with proper authentication is required.
- Always filter out pull requests from the results (GitHub's issues API includes PRs).

## Example Output

```
# GitHub Issues Report: facebook/react

**Generated:** 2025-01-15
**Total Open Issues:** 87

## Label Distribution

| Label         | Count |
|---------------|-------|
| bug           | 23    |
| enhancement   | 31    |
| documentation | 8     |
| good first issue | 12 |
| unlabeled     | 13    |

## Open Issues

| #     | Title                          | Author   | Labels        | Assignees | Comments | Age     |
|-------|--------------------------------|----------|---------------|-----------|----------|---------|
| #1234 | Fix hydration mismatch error   | user123  | bug           | dev1      | 5        | 3 days  |
| #1230 | Add support for new API        | user456  | enhancement   | —         | 12       | 1 week  |
| ...   | ...                            | ...      | ...           | ...       | ...      | ...     |

## Stale Issues (no activity in 30+ days)

- #1100 — Old rendering bug (45 days inactive)
- #1050 — Docs update needed (60 days inactive)

## Unassigned Issues

- #1230 — Add support for new API
- #1220 — Improve error messages

## Most Active Issues (by comments)

1. #1230 — Add support for new API (12 comments)
2. #1210 — Performance regression (9 comments)
3. #1205 — TypeScript types incorrect (7 comments)
```
