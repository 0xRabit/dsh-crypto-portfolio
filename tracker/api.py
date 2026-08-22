# -*- coding: utf-8 -*-
"""HTTP helpers with retry / backoff, shared by all fetchers."""
import random
import time

import requests

from . import config

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def _sleep_backoff(attempt, base=1.6):
    time.sleep(base * (2 ** attempt) + random.random() * 0.6)


def http_get_json(url, headers=None, params=None, timeout=None, retries=None, session=None):
    """GET and return parsed JSON. Raises on final failure."""
    timeout = timeout or config.REQUEST_TIMEOUT
    retries = retries if retries is not None else config.RETRIES
    s = session or requests.Session()
    hdrs = dict(DEFAULT_HEADERS)
    if headers:
        hdrs.update(headers)
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = s.get(url, headers=hdrs, params=params, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                if attempt < retries:
                    _sleep_backoff(attempt)
                    continue
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries:
                _sleep_backoff(attempt)
    raise last_err


def http_post_json(url, json_body=None, headers=None, timeout=None, retries=None, session=None):
    """POST JSON, return parsed JSON. Raises on final failure."""
    timeout = timeout or config.REQUEST_TIMEOUT
    retries = retries if retries is not None else config.RETRIES
    s = session or requests.Session()
    hdrs = dict(DEFAULT_HEADERS)
    if headers:
        hdrs.update(headers)
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = s.post(url, json=json_body, headers=hdrs, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                if attempt < retries:
                    _sleep_backoff(attempt)
                    continue
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries:
                _sleep_backoff(attempt)
    raise last_err
