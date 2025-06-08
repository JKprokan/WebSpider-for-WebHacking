import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from collections import deque

from modules.db import insert_link
from modules.params import extract_params_from_url
from modules.url_filter import compile_patterns, is_url_allowed

TARGET_ATTRS = {"name", "type", "title", "autocomplete", "value"}

def extract_inputs_with_form_context(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # 먼저 form 내부 input 수집
    form_input_ids = set()
    for form in soup.find_all("form"):
        method = form.get("method", "").upper()
        action = form.get("action", "")
        for tag in form.find_all(["input", "textarea", "select"]):
            input_info = {}
            for attr, value in tag.attrs.items():
                if attr in TARGET_ATTRS or attr.startswith("aria-"):
                    input_info[attr] = value
            if input_info:
                input_info["form_method"] = method
                input_info["form_action"] = action
                results.append(input_info)
            form_input_ids.add(id(tag))

    # form 외부 input 수집
    for tag in soup.find_all(["input", "textarea", "select"]):
        if id(tag) not in form_input_ids:
            input_info = {}
            for attr, value in tag.attrs.items():
                if attr in TARGET_ATTRS or attr.startswith("aria-"):
                    input_info[attr] = value
            if input_info:
                results.append(input_info)

    return results

def is_internal_url(url, base_netloc):
    return urlparse(url).netloc.endswith(base_netloc)

def run_static_crawl(start_url, max_depth=1, include=None, exclude=None, mode='dfs'):
    if mode == 'dfs':
        run_static_dfs(start_url, max_depth, include, exclude)
    else:
        run_static_bfs(start_url, max_depth, include, exclude)

def run_static_dfs(start_url, max_depth, include, exclude):
    visited = set()
    stack = [(start_url, 0, None)]

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)


    base_netloc = urlparse(start_url).netloc

    while stack:
        url, depth, parent = stack.pop()

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

        input_fields = extract_inputs_with_form_context(res.text)
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

def run_static_bfs(start_url, max_depth, include, exclude):
    visited = set()
    queue = deque()
    queue.append((start_url, 0, None))

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    base_netloc = urlparse(start_url).netloc

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

        input_fields = extract_inputs_with_form_context(res.text)
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