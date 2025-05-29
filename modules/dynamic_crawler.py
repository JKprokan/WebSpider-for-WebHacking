import asyncio
from urllib.parse import urljoin, urlparse
from collections import deque
from bs4 import BeautifulSoup
import json

from modules.db import insert_link
from modules.params import extract_params_from_url
from modules.url_filter import compile_patterns, is_url_allowed
from playwright.async_api import async_playwright

TARGET_ATTRS = {"name", "type", "title", "autocomplete"}

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

def run_dynamic_crawl_entry(start_url, max_depth=1, include=None, exclude=None):
    asyncio.run(_run_dynamic_crawl_entry(start_url, max_depth, include, exclude))

async def fetch_page(context, url, depth, parent, include_patterns, exclude_patterns, max_depth, visited, queue):
    if url in visited or depth > max_depth:
        return
    visited.add(url)

    print(f"[Depth {depth}] 수집: {url}")

    try:
        page = await context.new_page()
        await page.goto(url, timeout=10000)
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
            if not is_url_allowed(next_url, include_patterns, exclude_patterns):
                continue
            queue.append((next_url, depth + 1, url))

        await page.close()

    except Exception as e:
        print(f"[!] 요청 실패: {url} - {e}")

async def _run_dynamic_crawl_entry(start_url, max_depth=1, include=None, exclude=None):
    visited = set()
    queue = deque()
    queue.append((start_url, 0, None))

    include_patterns = compile_patterns(include)
    exclude_patterns = compile_patterns(exclude)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()

        while queue:
            tasks = []
            for _ in range(min(len(queue), 5)):
                url, depth, parent = queue.popleft()
                tasks.append(fetch_page(context, url, depth, parent, include_patterns, exclude_patterns, max_depth, visited, queue))
            await asyncio.gather(*tasks)

        await browser.close()
