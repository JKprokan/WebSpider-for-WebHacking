# modules/Directory_Bruteforce.py

import asyncio
from playwright.async_api import async_playwright

async def run_dynamic_bruteforce_async(base_url, wordlist_path, cookie=""):
    found_urls = []
    headers = {}

    if cookie:
        headers["Cookie"] = cookie

    with open(wordlist_path, 'r') as f:
        words = [line.strip() for line in f if line.strip()]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(extra_http_headers=headers)
        page = await context.new_page()

        for word in words:
            target_url = base_url.rstrip('/') + word
            try:
                response = await page.goto(target_url, timeout=5000)
                if response and 200 <= response.status < 400:
                    print(f"[+] Found: {target_url} ({response.status})")
                    found_urls.append(target_url)
            except Exception:
                pass

        await browser.close()

    return found_urls

# 동기 래퍼 함수 추가
def run_dynamic_bruteforce(base_url, wordlist_path, cookie=""):
    return asyncio.run(run_dynamic_bruteforce_async(base_url, wordlist_path, cookie))