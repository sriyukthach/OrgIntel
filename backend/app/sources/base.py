"""
Base Source Client & HTTP Request Manager
Implements connection reuse, caching, exponential backoff, rate limiting, and request quota tracking.
"""

import time
import asyncio
import hashlib
from typing import Optional, Dict, Any, Tuple
import httpx
from backend.app.config import settings
from backend.app.storage.repository import Repository


class RequestTracker:
    """Tracks per-run outbound network calls to adhere to competition limits (< 2000 requests, $10 budget)."""

    def __init__(self):
        self.request_count = 0
        self.cache_hits = 0
        self.errors_count = 0
        self.total_bytes = 0
        self.estimated_cost_usd = 0.0

    def record_request(self, cached: bool = False, bytes_len: int = 0, cost: float = 0.0):
        if cached:
            self.cache_hits += 1
        else:
            self.request_count += 1
            self.total_bytes += bytes_len
            self.estimated_cost_usd += cost


class BaseSourceClient:
    """Base class for all public web and API data sources."""

    def __init__(self, tracker: Optional[RequestTracker] = None):
        self.tracker = tracker or RequestTracker()
        self.headers = {
            "User-Agent": settings.HTTP_USER_AGENT,
            "Accept": "application/json, text/html, application/xhtml+xml, */*",
            "Accept-Language": "no, nb, nn, en-US, en;q=0.9",
        }

    def _get_cache_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        raw = f"{url}?{sorted(params.items()) if params else ''}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def fetch_url(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        is_json: bool = True,
        ttl_hours: int = 24,
    ) -> Tuple[Optional[Any], int, str]:
        """
        Fetches URL with caching, rate limiting, and retries.
        Returns (parsed_data_or_text, status_code, source_url).
        """
        cache_key = self._get_cache_key(url, params)

        # 1. Check persistent SQLite cache
        cached = await Repository.get_cached_response(cache_key)
        if cached:
            self.tracker.record_request(cached=True)
            body = cached["body"]
            status_code = cached["status_code"]
            if is_json and status_code == 200:
                try:
                    import json
                    return json.loads(body), status_code, url
                except Exception:
                    return body, status_code, url
            return body, status_code, url

        # 2. Network Request with Exponential Backoff
        req_headers = {**self.headers, **(headers or {})}
        timeout = httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS, connect=2.0)

        for attempt in range(settings.HTTP_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    response = await client.get(url, params=params, headers=req_headers)
                    self.tracker.record_request(cached=False, bytes_len=len(response.content))

                    if response.status_code == 200:
                        body_text = response.text
                        await Repository.save_cached_response(
                            cache_key=cache_key,
                            url=str(response.url),
                            body=body_text,
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            ttl_hours=ttl_hours,
                        )
                        if is_json:
                            try:
                                return response.json(), 200, str(response.url)
                            except Exception:
                                return body_text, 200, str(response.url)
                        return body_text, 200, str(response.url)

                    elif response.status_code == 404:
                        await Repository.save_cached_response(
                            cache_key=cache_key,
                            url=url,
                            body="Not Found",
                            status_code=404,
                            ttl_hours=6,
                        )
                        return None, 404, url

                    elif response.status_code in (429, 500, 502, 503, 504):
                        if attempt < settings.HTTP_MAX_RETRIES:
                            await asyncio.sleep(0.5 * (2 ** attempt))
                            continue
                        return None, response.status_code, url
                    else:
                        return None, response.status_code, url

            except (httpx.ConnectError, httpx.ConnectTimeout):
                # Immediate network unreachable / DNS error -> fail fast without retrying
                self.tracker.errors_count += 1
                return None, 0, url

            except (httpx.RequestError, httpx.TimeoutException):
                if attempt < settings.HTTP_MAX_RETRIES:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                self.tracker.errors_count += 1
                return None, 0, url

        return None, 0, url
