"""GitHub file reader tool using the gh CLI."""
from __future__ import annotations

import base64
import json
import subprocess
from typing import Annotated

from agent_framework import tool


@tool
def github_read(
    repo: Annotated[str, "Repository in owner/repo format"],
    path: Annotated[str, "File path within the repository"],
    ref: Annotated[str, "Branch or commit ref"] = "HEAD",
) -> str:
    """Fetch and return the content of a file from a GitHub repository."""
    try:
        result = subprocess.run(
            [
                "gh", "api",
                f"repos/{repo}/contents/{path}",
                "-X", "GET",
                "-f", f"ref={ref}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return json.dumps({
                "repo": repo,
                "path": path,
                "error": result.stderr.strip() or "gh CLI command failed",
            })

        data = json.loads(result.stdout)
        encoding = data.get("encoding", "")
        raw_content = data.get("content", "")

        if encoding == "base64":
            content = base64.b64decode(raw_content).decode("utf-8", errors="replace")
        else:
            content = raw_content

        # Truncate to avoid exceeding context limits
        if len(content) > 8000:
            content = content[:8000] + "\n... [truncated]"

        return json.dumps({
            "repo": repo,
            "path": path,
            "url": data.get("html_url", ""),
            "content": content,
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"repo": repo, "path": path, "error": "Request timed out"})
    except Exception as e:
        return json.dumps({"repo": repo, "path": path, "error": str(e)})
