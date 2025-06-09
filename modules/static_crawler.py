import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from collections import deque

from modules.config import STATIC_TARGET_ATTRS
from modules.parser import extract_inputs_with_form_context
from modules.db import insert_link
from modules.params import extract_params_from_url
from modules.url_filter import compile_patterns, is_url_allowed

def is_internal_url(url, base_netloc):
    return urlparse(url).netloc.endswith(base_netloc)

def parse_cookie_string(cookie_str):
    cookies = {}
    for pair in cookie_str.split(";"):
        if "=" in pair:
            name, value = pair.strip().split("=", 1)
            cookies[name.strip()] = value.strip()
    return cookies

def run_static_crawl(start_url, max_depth=1, include=None, exclude=None, mode='dfs', cookie=""):
    if mode == 'dfs':
        run_static_dfs(start_url, max_depth, include, exclude, cookie)
    else:
        run_static_bfs(start_url, max_depth, include, exclude, cookie)


def run_static_dfs(start_url, max_depth, include, exclude, cookie=""):
    visited = set()
    stack = [(start_url, 0, None)]

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    base_netloc = urlparse(start_url).netloc

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    if cookie:
        for k, v in parse_cookie_string(cookie).items():
            session.cookies.set(k, v)

    while stack:
        url, depth, parent = stack.pop()

        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        print(f"[Depth {depth}] 수집: {url}")

        try:
            res = session.get(url, timeout=5)
            res.raise_for_status()
        except Exception as e:
            print(f"[!] 요청 실패: {url} - {e}")
            continue

        parsed = urlparse(url)
        host = parsed.netloc
        query_dict = extract_params_from_url(url)
        query_params = json.dumps(query_dict, ensure_ascii=False)

        input_fields = extract_inputs_with_form_context(res.text, target_attrs=STATIC_TARGET_ATTRS)
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

def run_static_bfs(start_url, max_depth, include, exclude, cookie=""):
    visited = set()
    queue = deque()
    queue.append((start_url, 0, None))

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    base_netloc = urlparse(start_url).netloc

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    if cookie:
        for k, v in parse_cookie_string(cookie).items():
            session.cookies.set(k, v)

    while queue:
        url, depth, parent = queue.popleft()

        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        print(f"[Depth {depth}] 수집: {url}")

        try:
            res = session.get(url, timeout=5)
            res.raise_for_status()
        except Exception as e:
            print(f"[!] 요청 실패: {url} - {e}")
            continue

        parsed = urlparse(url)
        host = parsed.netloc
        query_dict = extract_params_from_url(url)
        query_params = json.dumps(query_dict, ensure_ascii=False)

        input_fields = extract_inputs_with_form_context(res.text, target_attrs=STATIC_TARGET_ATTRS)
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