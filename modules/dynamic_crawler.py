import asyncio
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json
from collections import deque

from config import DYNAMIC_TARGET_ATTRS
from modules.parser import extract_inputs_with_form_context
from modules.db import insert_link
from modules.params import extract_params_from_url
from modules.url_filter import compile_patterns, is_url_allowed
from playwright.async_api import async_playwright

def is_supported_scheme(url):
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"}

def is_internal_url(url, base_netloc):
    return urlparse(url).netloc.endswith(base_netloc)

def parse_cookie_string(cookie_str: str) -> list:
    cookies = []
    if cookie_str:
        for part in cookie_str.split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                cookies.append({"name": key.strip(), "value": value.strip()})
    return cookies

def run_dynamic_crawl_entry(start_url, max_depth=1, include=None, exclude=None, mode='dfs', cookie=None, seed_urls=None):
    base_netloc = urlparse(start_url).netloc
    cookie_list = parse_cookie_string(cookie) if cookie else []
    seed_urls = seed_urls or []
    start_points = [start_url] + seed_urls

    if mode == 'dfs':
        asyncio.run(_run_dynamic_dfs(start_points, max_depth, include, exclude, base_netloc, cookie_list))
    else:
        asyncio.run(_run_dynamic_bfs(start_points, max_depth, include, exclude, base_netloc, cookie_list))

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

        input_fields = extract_inputs_with_form_context(content, target_attrs=DYNAMIC_TARGET_ATTRS)
        input_fields_json = json.dumps(input_fields, ensure_ascii=False)

        parsed = urlparse(url)
        host = parsed.netloc
        query_dict = extract_params_from_url(url)
        query_params = json.dumps(query_dict, ensure_ascii=False)

        insert_link(url, parent, depth, host, query_params, input_fields_json)

        if depth == max_depth:
            await page.close()
            return

        soup = BeautifulSoup(content, "html.parser")
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
        try:
            await page.close()
        except:
            pass

async def _run_dynamic_dfs(start_points, max_depth=1, include=None, exclude=None, base_netloc=None, cookie_list=None):
    visited = set()
    stack = [(url, 0, None) for url in start_points]

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)

        if cookie_list:
            domain = urlparse(start_points[0]).hostname
            for cookie in cookie_list:
                cookie["domain"] = domain
                cookie["path"] = "/"
            await context.add_cookies(cookie_list)

        while stack:
            url, depth, parent = stack.pop()
            await fetch_page(context, url, depth, parent, include_patterns, exclude_patterns, max_depth, visited, stack, list.append, base_netloc)

        await browser.close()

async def _run_dynamic_bfs(start_points, max_depth=1, include=None, exclude=None, base_netloc=None, cookie_list=None):
    visited = set()
    queue = deque([(url, 0, None) for url in start_points])

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)

        if cookie_list:
            domain = urlparse(start_points[0]).hostname
            for cookie in cookie_list:
                cookie["domain"] = domain
                cookie["path"] = "/"
            await context.add_cookies(cookie_list)

        async def block_unneeded_resources(route):
            if route.request.resource_type in ["image", "font", "stylesheet"]:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", block_unneeded_resources)

        while queue:
            tasks = []
            for _ in range(min(len(queue), 20)):
                url, depth, parent = queue.popleft()
                tasks.append(fetch_page(context, url, depth, parent, include_patterns, exclude_patterns, max_depth, visited, queue, deque.append, base_netloc))
            await asyncio.gather(*tasks)

        await browser.close()