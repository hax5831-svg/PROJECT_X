"""Asynchronous weather telemetry fetching from wttr.in with local caching."""

import threading
import time
import urllib.request


class WeatherManager:
    """Fetches and caches weather conditions asynchronously without blocking."""

    def __init__(self, cache_ttl_seconds: float = 1800.0):
        self.cache_ttl = cache_ttl_seconds
        self._cached_weather = "Fetching..."
        self._last_fetch_time = 0.0
        self._is_fetching = False

    def get_weather(self) -> str:
        now = time.time()
        if now - self._last_fetch_time > self.cache_ttl and not self._is_fetching:
            self._is_fetching = True
            threading.Thread(target=self._fetch_async, daemon=True).start()
        return self._cached_weather

    def _fetch_async(self):
        try:
            req = urllib.request.Request(
                "https://wttr.in/?format=%c+%t+%w&m",
                headers={"User-Agent": "curl/7.68.0"},
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = resp.read().decode("utf-8").strip()
                if data:
                    self._cached_weather = data
                    self._last_fetch_time = time.time()
        except Exception:
            if self._cached_weather == "Fetching...":
                self._cached_weather = "Offline"
        finally:
            self._is_fetching = False
