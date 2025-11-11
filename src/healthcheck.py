# healthcheck.py
import sys, urllib.request, contextlib

URL = "http://localhost:8000/api/health"
try:
    with contextlib.closing(urllib.request.urlopen(URL, timeout=5)) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
