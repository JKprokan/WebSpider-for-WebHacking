import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
import json

from modules.db import insert_link
from modules.params import extract_params_from_url
from modules.url_filter import compile_patterns, is_url_allowed

def run_static_crawl(start_url, max_depth=1, include=None, exclude=None):
    visited = set()
    queue = deque()
    queue.append((start_url, 0, None))  # (URL, depth, parent)

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    while queue:
        url, depth, parent = queue.popleft()

        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        print(f"[Depth {depth}] 수집: {url}")

        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            res.raise_for_status()
        except Exception as e:
            print(f"[!] 요청 실패: {url} - {e}")
            continue

        parsed = urlparse(url)
        host = parsed.netloc
        query_dict = extract_params_from_url(url)
        query_params = json.dumps(query_dict, ensure_ascii=False)

        insert_link(url, parent, depth, host, query_params)

        if depth == max_depth:
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            next_url = urljoin(url, href)

            if not is_url_allowed(next_url, include_patterns, exclude_patterns):
                continue

            queue.append((next_url, depth + 1, url))
