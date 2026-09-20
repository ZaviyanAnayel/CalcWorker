#!/usr/bin/env python3
"""
IndexNow Auto-Indexing Utility for CalcWorker.com
Notifies Bing, Yandex, Seznam, and IndexNow-enabled search engines
about new or updated URLs instantly.
"""

import urllib.request
import json
import re
import sys
import os

INDEXNOW_KEY = "f63b4b8a25c14e13b821a7df84e622b1"
HOST = "calcworker.com"
KEY_LOCATION = f"https://{HOST}/{INDEXNOW_KEY}.txt"

ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://yandex.com/indexnow",
    "https://www.bing.com/indexnow"
]

def get_sitemap_urls():
    sitemap_path = os.path.join(os.path.dirname(__file__), "..", "sitemap.xml")
    if not os.path.exists(sitemap_path):
        print(f"Error: sitemap.xml not found at {sitemap_path}")
        return []
    with open(sitemap_path, "r", encoding="utf-8") as f:
        content = f.read()
    return re.findall(r"<loc>(.*?)</loc>", content)

def submit_urls(urls):
    if not urls:
        print("No URLs provided for submission.")
        return False

    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls
    }

    data = json.dumps(payload).encode("utf-8")
    success = False

    for endpoint in ENDPOINTS:
        try:
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                code = resp.getcode()
                if code in (200, 202):
                    print(f"[SUCCESS] {endpoint} accepted {len(urls)} URLs! (HTTP {code})")
                    success = True
                    break
        except urllib.error.HTTPError as e:
            if e.code in (200, 202):
                print(f"[SUCCESS] {endpoint} accepted {len(urls)} URLs! (HTTP {e.code})")
                success = True
                break
            else:
                err_body = e.read().decode('utf-8', errors='ignore')
                print(f"[INFO] {endpoint} returned {e.code}: {err_body[:100]}... Trying next endpoint...")
        except Exception as e:
            print(f"[INFO] {endpoint} error: {e}. Trying next...")

    return success

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_urls = [u.strip() for u in sys.argv[1:] if u.strip().startswith("http")]
    else:
        print("No specific URLs provided. Loading all URLs from sitemap.xml...")
        target_urls = get_sitemap_urls()

    print(f"Submitting {len(target_urls)} URLs to IndexNow ({HOST})...")
    submit_urls(target_urls)
