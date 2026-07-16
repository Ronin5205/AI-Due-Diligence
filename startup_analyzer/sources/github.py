"""GitHub repository and issue search."""
from __future__ import annotations

import httpx

from sources.base import RawDocumentRecord


class GitHubSource:
    name = "github"
    BASE_URL = "https://api.github.com/search"

    def __init__(self, token: str = "", timeout: float = 30.0):
        self.token = token
        self.timeout = timeout

    def is_configured(self) -> bool:
        return True

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def search(self, query: str, limit: int = 10) -> list[RawDocumentRecord]:
        docs: list[RawDocumentRecord] = []
        per_type = max(1, limit // 2)

        with httpx.Client(timeout=self.timeout, headers=self._headers()) as client:
            for endpoint, kind in (("repositories", "repo"), ("issues", "issue")):
                params = {"q": query, "per_page": min(per_type, 10), "sort": "stars"}
                resp = client.get(f"{self.BASE_URL}/{endpoint}", params=params)
                if resp.status_code == 403:
                    break
                resp.raise_for_status()
                for item in resp.json().get("items", []):
                    if kind == "repo":
                        external_id = str(item.get("id", ""))
                        title = item.get("full_name", "")
                        url = item.get("html_url", "")
                        content = "\n".join(
                            filter(
                                None,
                                [
                                    item.get("description") or "",
                                    f"Stars: {item.get('stargazers_count', 0)}",
                                    f"Language: {item.get('language') or 'unknown'}",
                                    f"Topics: {', '.join(item.get('topics') or [])}",
                                ],
                            )
                        )
                    else:
                        external_id = f"issue-{item.get('id', '')}"
                        title = item.get("title", "")
                        url = item.get("html_url", "")
                        content = (item.get("body") or "")[:4000]
                    docs.append(
                        RawDocumentRecord(
                            source=self.name,
                            external_id=external_id,
                            title=title,
                            content=content,
                            url=url,
                            metadata={"kind": kind, "query": query},
                        )
                    )
        return docs[:limit]
