"""Build configured search source instances."""
from __future__ import annotations

from config import AnalyzerConfig, DEFAULT_SOURCES
from sources.base import SearchSource
from sources.github import GitHubSource
from sources.google_trends import GoogleTrendsSource
from sources.hackernews import HackerNewsSource
from sources.producthunt import ProductHuntSource
from sources.reddit import RedditSource


def build_sources(config: AnalyzerConfig) -> dict[str, SearchSource]:
    all_sources: dict[str, SearchSource] = {
        "hackernews": HackerNewsSource(timeout=config.http_timeout),
        "github": GitHubSource(token=config.github_token, timeout=config.http_timeout),
        "reddit": RedditSource(
            client_id=config.reddit_client_id,
            client_secret=config.reddit_client_secret,
            user_agent=config.reddit_user_agent,
            timeout=config.http_timeout,
        ),
        "product_hunt": ProductHuntSource(
            token=config.product_hunt_token,
            timeout=config.http_timeout,
        ),
        "google_trends": GoogleTrendsSource(),
    }
    enabled = config.sources or DEFAULT_SOURCES
    return {k: v for k, v in all_sources.items() if k in enabled}
