import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from collections import deque

from modules.db import insert_link
from modules.params import extract_params_from_url
from modules.url_filter import compile_patterns, is_url_allowed

TARGET_ATTRS = {"name", "type", "title", "autocomplete", "value"}

def extract_input_fields(html):
    soup = BeautifulSoup(html, "html.parser")
    inputs = []

    for tag in soup.find_all(["input", "textarea", "select"]):
        input_info = {}
        for attr, value in tag.attrs.items():
            if attr in TARGET_ATTRS or attr.startswith("aria-"):
                input_info[attr] = value
        if input_info:
            inputs.append(input_info)

    return inputs

def is_internal_url(url, base_netloc):
    return urlparse(url).netloc.endswith(base_netloc)

def parse_cookie_string(cookie_str):
    cookies = {}
    if cookie_str:
        for part in cookie_str.split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                cookies[key.strip()] = value.strip()
    return cookies

def run_static_crawl(start_url, max_depth=1, include=None, exclude=None, mode='dfs', cookie=None, seed_urls=None):
    cookie_dict = parse_cookie_string(cookie) if cookie else {}
    seed_urls = seed_urls or []

    start_points = [start_url] + seed_urls

    if mode == 'dfs':
        run_static_dfs(start_points, max_depth, include, exclude, cookie_dict)
    else:
        run_static_bfs(start_points, max_depth, include, exclude, cookie_dict)

def run_static_dfs(start_points, max_depth, include, exclude, cookies):
    visited = set()
    stack = [(url, 0, None) for url in start_points]

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    base_netloc = urlparse(start_points[0]).netloc

    while stack:
        url, depth, parent = stack.pop()

        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        print(f"[Depth {depth}] 수집: {url}")

        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, cookies=cookies, timeout=5)
            res.raise_for_status()
        except Exception as e:
            print(f"[!] 요청 실패: {url} - {e}")
            continue

        parsed = urlparse(url)
        host = parsed.netloc
        query_dict = extract_params_from_url(url)
        query_params = json.dumps(query_dict, ensure_ascii=False)

        input_fields = extract_input_fields(res.text)
        input_fields_json = json.dumps(input_fields, ensure_ascii=False)

        insert_link(url, parent, depth, host, query_params, input_fields_json)

        if depth == max_depth:
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup.find_all("a", href=True):
            next_url = urljoin(url, tag["href"])

            if not is_internal_url(next_url, base_netloc):
                continue
            if not is_url_allowed(next_url, include_patterns, exclude_patterns):
                continue

            stack.append((next_url, depth + 1, url))

def run_static_bfs(start_points, max_depth, include, exclude, cookies):
    visited = set()
    queue = deque([(url, 0, None) for url in start_points])

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    base_netloc = urlparse(start_points[0]).netloc

    while queue:
        url, depth, parent = queue.popleft()

        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        print(f"[Depth {depth}] 수집: {url}")

        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, cookies=cookies, timeout=5)
            res.raise_for_status()
        except Exception as e:
            print(f"[!] 요청 실패: {url} - {e}")
            continue

        parsed = urlparse(url)
        host = parsed.netloc
        query_dict = extract_params_from_url(url)
        query_params = json.dumps(query_dict, ensure_ascii=False)

        input_fields = extract_input_fields(res.text)
        input_fields_json = json.dumps(input_fields, ensure_ascii=False)

        insert_link(url, parent, depth, host, query_params, input_fields_json)

        if depth == max_depth:
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup.find_all("a", href=True):
            next_url = urljoin(url, tag["href"])

            if not is_internal_url(next_url, base_netloc):
                continue
            if not is_url_allowed(next_url, include_patterns, exclude_patterns):
                continue

            queue.append((next_url, depth + 1, url))