"""Reddit search via OAuth API."""
from __future__ import annotations

import threading

import httpx

from sources.base import RawDocumentRecord


class RedditSource:
    name = "reddit"
    AUTH_URL = "https://www.reddit.com/api/v1/access_token"
    SEARCH_URL = "https://oauth.reddit.com/search"

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        user_agent: str = "startup-analyzer/1.0",
        timeout: float = 30.0,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.timeout = timeout
        self._token: str | None = None
        self._token_lock = threading.Lock()

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _get_token(self, client: httpx.Client) -> str:
        with self._token_lock:
            if self._token:
                return self._token
            resp = client.post(
                self.AUTH_URL,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                headers={"User-Agent": self.user_agent},
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
            return self._token

    def search(self, query: str, limit: int = 10) -> list[RawDocumentRecord]:
        if not self.is_configured():
            return []

        docs: list[RawDocumentRecord] = []
        with httpx.Client(timeout=self.timeout) as client:
            token = self._get_token(client)
            params = {
                "q": query,
                "sort": "relevance",
                "limit": min(limit, 25),
                "type": "link",
            }
            resp = client.get(
                self.SEARCH_URL,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": self.user_agent,
                },
            )
            resp.raise_for_status()
            for child in resp.json().get("data", {}).get("children", []):
                post = child.get("data", {})
                external_id = post.get("id", "")
                title = post.get("title", "")
                url = f"https://reddit.com{post.get('permalink', '')}"
                content = "\n".join(
                    filter(
                        None,
                        [
                            title,
                            (post.get("selftext") or "")[:3000],
                            f"Subreddit: r/{post.get('subreddit', '')}",
                            f"Score: {post.get('score', 0)}",
                            f"Comments: {post.get('num_comments', 0)}",
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
                            "subreddit": post.get("subreddit"),
                            "score": post.get("score"),
                            "num_comments": post.get("num_comments"),
                        },
                    )
                )
        return docs
