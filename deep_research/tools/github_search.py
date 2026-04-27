"""GitHub search tool using the gh CLI."""
from __future__ import annotations

import json
import subprocess


def github_search(query: str, mode: str = "code", max_results: int = 5) -> str:
    """Search GitHub for code, repositories, or issues using the gh CLI."""
    endpoint_map = {
        "code": "search/code",
        "repos": "search/repositories",
        "issues": "search/issues",
    }
    endpoint = endpoint_map.get(mode)
    if not endpoint:
        return json.dumps({"error": f"Invalid mode '{mode}'. Use code, repos, or issues."})

    try:
        cmd = [
            "gh", "api", endpoint,
            "-X", "GET",
            "-f", f"q={query}",
            "-f", f"per_page={max_results}",
        ]
        if mode == "code":
            cmd.extend(["-H", "Accept: application/vnd.github.text-match+json"])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return json.dumps({"error": result.stderr.strip() or "gh CLI command failed"})

        data = json.loads(result.stdout)
        items = data.get("items", [])

        if mode == "code":
            formatted = [
                {
                    "repo": item.get("repository", {}).get("full_name", ""),
                    "path": item.get("path", ""),
                    "url": item.get("html_url", ""),
                    "snippet": _extract_code_snippet(item),
                }
                for item in items
            ]
        elif mode == "repos":
            formatted = [
                {
                    "name": item.get("full_name", ""),
                    "description": (item.get("description") or "")[:200],
                    "stars": item.get("stargazers_count", 0),
                    "url": item.get("html_url", ""),
                    "language": item.get("language", ""),
                }
                for item in items
            ]
        else:  # issues
            formatted = [
                {
                    "title": item.get("title", ""),
                    "body": (item.get("body") or "")[:300],
                    "url": item.get("html_url", ""),
                    "state": item.get("state", ""),
                    "repo": item.get("repository_url", "").replace(
                        "https://api.github.com/repos/", ""
                    ),
                }
                for item in items
            ]

        return json.dumps({"results": formatted})
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "GitHub search timed out"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _extract_code_snippet(item: dict) -> str:
    """Extract text matches from a code search result."""
    matches = item.get("text_matches", [])
    if matches:
        fragments = [m.get("fragment", "") for m in matches[:2]]
        return "\n---\n".join(fragments)
    return item.get("name", "")
