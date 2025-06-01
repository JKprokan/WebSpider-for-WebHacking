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

def is_supported_scheme(url):
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"}

def is_internal_url(url, base_netloc):
    return urlparse(url).netloc.endswith(base_netloc)

def run_dynamic_crawl_entry(start_url, max_depth=1, include=None, exclude=None, mode='dfs'):
    base_netloc = urlparse(start_url).netloc
    if mode == 'dfs':
        asyncio.run(_run_dynamic_dfs(start_url, max_depth, include, exclude, base_netloc))
    else:
        asyncio.run(_run_dynamic_bfs(start_url, max_depth, include, exclude, base_netloc))

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

        input_fields = extract_input_fields(content)
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
        await page.close()

async def _run_dynamic_dfs(start_url, max_depth=1, include=None, exclude=None, base_netloc=None):
    visited = set()
    stack = [(start_url, 0, None)]

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()

        while stack:
            url, depth, parent = stack.pop()
            await fetch_page(context, url, depth, parent, include_patterns, exclude_patterns, max_depth, visited, stack, list.append, base_netloc)

        await browser.close()

async def _run_dynamic_bfs(start_url, max_depth=1, include=None, exclude=None, base_netloc=None):
    visited = set()
    queue = deque()
    queue.append((start_url, 0, None))

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        #리소스 차단
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
                tasks.append(fetch_page(context, url, depth, parent, include_patterns, exclude_patterns, max_depth, visited, queue, deque.append, base_netloc=None))
            await asyncio.gather(*tasks)

        await browser.close()