#!/usr/bin/env python3
"""
Sisyphus Academica: HTTP helper with retry and exponential backoff.

Retries 429 and 5xx responses and network errors. Honors Retry-After.
Returns None when every attempt fails so callers can degrade per source.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, Optional

USER_AGENT = "SisyphusAcademica/0.3 (+https://github.com/argahv/sisyphus-academica)"
RETRYABLE_CODES = {429, 500, 502, 503, 504}
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0
MAX_RETRY_AFTER = 30.0


def _log(label: str, message: str) -> None:
    print(f"  {label}: {message}", file=sys.stderr)


def fetch(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    label: str = "http",
) -> Optional[bytes]:
    """GET a URL. Returns the body, or None after all retries fail."""
    merged = {"User-Agent": USER_AGENT}
    merged.update(headers or {})
    req = urllib.request.Request(url, headers=merged)
    for attempt in range(max_retries):
        last = attempt == max_retries - 1
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in RETRYABLE_CODES and not last:
                delay = base_delay * (2**attempt)
                retry_after = e.headers.get("Retry-After") if e.headers else None
                if retry_after and retry_after.strip().isdigit():
                    delay = min(float(retry_after), MAX_RETRY_AFTER)
                time.sleep(delay)
                continue
            _log(label, f"HTTP {e.code}")
            return None
        except (urllib.error.URLError, OSError) as e:
            if not last:
                time.sleep(base_delay * (2**attempt))
                continue
            _log(label, f"request failed ({getattr(e, 'reason', e)})")
            return None
    return None


def fetch_json(url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> Optional[Dict]:
    merged = {"Accept": "application/json"}
    merged.update(headers or {})
    body = fetch(url, headers=merged, **kwargs)
    if body is None:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        _log(kwargs.get("label", "http"), "invalid JSON response")
        return None


def fetch_text(url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> Optional[str]:
    body = fetch(url, headers=headers, **kwargs)
    return body.decode("utf-8", errors="replace") if body is not None else None
