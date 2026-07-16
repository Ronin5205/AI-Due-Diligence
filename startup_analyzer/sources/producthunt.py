"""Product Hunt GraphQL search."""
from __future__ import annotations

import httpx

from sources.base import RawDocumentRecord

_SEARCH_QUERY = """
query SearchPosts($query: String!, $first: Int!) {
  posts(search: $query, first: $first) {
    edges {
      node {
        id
        name
        tagline
        description
        url
        votesCount
        commentsCount
        createdAt
      }
    }
  }
}
"""


class ProductHuntSource:
    name = "product_hunt"
    API_URL = "https://api.producthunt.com/v2/api/graphql"

    def __init__(self, token: str = "", timeout: float = 30.0):
        self.token = token
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.token)

    def search(self, query: str, limit: int = 10) -> list[RawDocumentRecord]:
        if not self.is_configured():
            return []

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                self.API_URL,
                json={
                    "query": _SEARCH_QUERY,
                    "variables": {"query": query, "first": min(limit, 20)},
                },
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (401, 403):
                return []
            resp.raise_for_status()
            data = resp.json()

        docs: list[RawDocumentRecord] = []
        edges = data.get("data", {}).get("posts", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            external_id = str(node.get("id", ""))
            title = node.get("name", "")
            url = node.get("url") or f"https://www.producthunt.com/posts/{external_id}"
            content = "\n".join(
                filter(
                    None,
                    [
                        node.get("tagline") or "",
                        node.get("description") or "",
                        f"Votes: {node.get('votesCount', 0)}",
                        f"Comments: {node.get('commentsCount', 0)}",
                    ],
                )
            )
            docs.append(
                RawDocumentRecord(
                    source=self.name,
                    external_id=external_id,
                    title=title,
                    content=content,
                    url=url,
                    metadata={
                        "votes": node.get("votesCount"),
                        "comments": node.get("commentsCount"),
                        "created_at": node.get("createdAt"),
                    },
                )
            )
        return docs
