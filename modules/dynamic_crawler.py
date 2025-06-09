import asyncio
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json
from collections import deque

from modules.db import insert_link
from modules.params import extract_params_from_url
from modules.url_filter import compile_patterns, is_url_allowed
from playwright.async_api import async_playwright

TARGET_ATTRS = {"name", "type", "title", "autocomplete", "oninput", "onchange"}

def extract_inputs_with_form_context(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # form 내부 input 수집
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

def is_supported_scheme(url):
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"}

def is_internal_url(url, base_netloc):
    return urlparse(url).netloc.endswith(base_netloc)

def parse_cookie_string(cookie_str, domain):
    cookies = []
    for pair in cookie_str.split(";"):
        if "=" not in pair:
            continue
        name, value = pair.strip().split("=", 1)
        cookies.append({
            "name": name.strip(),
            "value": value.strip(),
            "domain": domain,
            "path": "/"
        })
    return cookies

async def block_unneeded_resources(route):
    if route.request.resource_type in ["image", "font", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()

def run_dynamic_crawl_entry(start_url, max_depth=1, include=None, exclude=None, mode='dfs', cookie=""):
    base_netloc = urlparse(start_url).netloc
    if mode == 'dfs':
        asyncio.run(_run_dynamic_dfs(start_url, max_depth, include, exclude, base_netloc, cookie))
    else:
        asyncio.run(_run_dynamic_bfs(start_url, max_depth, include, exclude, base_netloc, cookie))

async def fetch_page(context, url, depth, parent, include_patterns, exclude_patterns, max_depth, visited, container, push, base_netloc):
    if url in visited or depth > max_depth:
        return
    visited.add(url)

    print(f"[Depth {depth}] 수집 : {url}")

    try:
        page = await context.new_page()
        await page.goto(url, timeout=7000, wait_until="domcontentloaded")
        await page.wait_for_load_state("domcontentloaded")
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser") 

        input_fields = extract_inputs_with_form_context(content)
        input_fields_json = json.dumps(input_fields, ensure_ascii=False)

        parsed = urlparse(url)
        host = parsed.netloc
        query_dict = extract_params_from_url(url)
        query_params = json.dumps(query_dict, ensure_ascii=False)

        insert_link(url, parent, depth, host, query_params, input_fields_json)

        if depth == max_depth:
            await page.close()
            return

        for tag in soup.find_all("a", href=True):
            next_url = urljoin(url, tag["href"])
            if next_url.startswith("javascript:") or not is_supported_scheme(next_url):
                continue
            if not is_internal_url(next_url, base_netloc):
                continue
            if not is_url_allowed(next_url, include_patterns, exclude_patterns):
                continue
            push(container, (next_url, depth + 1, url))

        await page.close()

    except Exception as e:
        print(f"[!] 요청 실패: {url} - {e}")
        await page.close()

async def _run_dynamic_dfs(start_url, max_depth=1, include=None, exclude=None, base_netloc=None, cookie=""):
    visited = set()
    stack = [(start_url, 0, None)]

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)

        # 쿠키 설정
        if cookie:
            parsed = urlparse(start_url)
            cookies = parse_cookie_string(cookie, parsed.hostname)
            await context.add_cookies(cookies)

        await context.route("**/*", block_unneeded_resources)

        while stack:
            url, depth, parent = stack.pop()
            await fetch_page(context, url, depth, parent, include_patterns, exclude_patterns, max_depth, visited, stack, list.append, base_netloc)

        await browser.close()

async def _run_dynamic_bfs(start_url, max_depth=1, include=None, exclude=None, base_netloc=None, cookie=""):
    visited = set()
    queue = deque()
    queue.append((start_url, 0, None))

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)

        # 쿠키 설정
        if cookie:
            parsed = urlparse(start_url)
            cookies = parse_cookie_string(cookie, parsed.hostname)
            await context.add_cookies(cookies)

        await context.route("**/*", block_unneeded_resources)

        while queue:
            tasks = []
            for _ in range(min(len(queue), 20)):
                url, depth, parent = queue.popleft()
                tasks.append(fetch_page(context, url, depth, parent, include_patterns, exclude_patterns, max_depth, visited, queue, deque.append, base_netloc))
            await asyncio.gather(*tasks)

        await browser.close()