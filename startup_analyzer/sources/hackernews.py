"""Hacker News search via Algolia API."""
from __future__ import annotations

import httpx

from sources.base import RawDocumentRecord


class HackerNewsSource:
    name = "hackernews"
    BASE_URL = "https://hn.algolia.com/api/v1/search"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def is_configured(self) -> bool:
        return True

    def search(self, query: str, limit: int = 10) -> list[RawDocumentRecord]:
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": min(limit, 20),
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        docs: list[RawDocumentRecord] = []
        for hit in data.get("hits", []):
            object_id = str(hit.get("objectID", ""))
            title = hit.get("title") or hit.get("story_title") or ""
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
            content_parts = [
                title,
                hit.get("story_text") or "",
                f"Points: {hit.get('points', 0)}",
                f"Comments: {hit.get('num_comments', 0)}",
            ]
            docs.append(
                RawDocumentRecord(
                    source=self.name,
                    external_id=object_id,
                    title=title,
                    content="\n".join(p for p in content_parts if p),
                    url=url,
                    metadata={
                        "points": hit.get("points"),
                        "num_comments": hit.get("num_comments"),
                        "author": hit.get("author"),
                        "created_at": hit.get("created_at"),
                    },
                )
            )
        return docs
