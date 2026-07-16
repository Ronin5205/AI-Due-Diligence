"""Google Trends via PyTrends."""
from __future__ import annotations

import threading

from sources.base import RawDocumentRecord


class GoogleTrendsSource:
    name = "google_trends"

    def __init__(self):
        self._pytrends = None
        self._lock = threading.Lock()

    def is_configured(self) -> bool:
        try:
            import pytrends  # noqa: F401
            return True
        except ImportError:
            return False

    def _client(self):
        if self._pytrends is None:
            from pytrends.request import TrendReq
            self._pytrends = TrendReq(hl="en-US", tz=360)
        return self._pytrends

    def search(self, query: str, limit: int = 5) -> list[RawDocumentRecord]:
        if not self.is_configured():
            return []

        try:
            with self._lock:
                client = self._client()
                kw = query[:100]
                client.build_payload([kw], timeframe="today 12-m")
                interest = client.interest_over_time()
                related = client.related_queries()

            content_parts = [f"Search interest for: {kw}"]
            if not interest.empty and kw in interest.columns:
                avg = float(interest[kw].mean())
                peak = int(interest[kw].max())
                content_parts.append(f"Average interest (12m): {avg:.1f}")
                content_parts.append(f"Peak interest (12m): {peak}")

            rising = related.get(kw, {}).get("rising")
            top = related.get(kw, {}).get("top")
            if rising is not None and not rising.empty:
                content_parts.append(
                    "Rising queries: " + ", ".join(rising["query"].head(5).tolist())
                )
            if top is not None and not top.empty:
                content_parts.append(
                    "Top queries: " + ", ".join(top["query"].head(5).tolist())
                )

            return [
                RawDocumentRecord(
                    source=self.name,
                    external_id=f"trends-{kw.lower().replace(' ', '-')}",
                    title=f"Google Trends: {kw}",
                    content="\n".join(content_parts),
                    url=f"https://trends.google.com/trends/explore?q={kw.replace(' ', '%20')}",
                    metadata={"query": kw},
                )
            ]
        except Exception:
            return []
