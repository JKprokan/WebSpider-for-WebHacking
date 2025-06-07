#진석 코드
import sqlite3
import json
import click
import requests
import os
from urllib.parse import urlparse, parse_qs

# 🔑 Upstage API 설정
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY", "APIkey")
UPSTAGE_API_URL = "API_URI"
UPSTAGE_MODEL = "solar-1-mini-chat"


def build_field_list(input_fields_raw: list) -> list:
    return [
        field for field in input_fields_raw
        if any(k in field for k in ("name", "aria-label", "title"))
    ]


def extract_query_params(url: str) -> dict:
    try:
        parsed = urlparse(url)
        return parse_qs(parsed.query)
    except:
        return {}


def build_prompt(url, input_fields, query_params):
    fields_str = json.dumps(input_fields, ensure_ascii=False, indent=2)
    params_str = json.dumps(query_params, ensure_ascii=False, indent=2)

    prompt = f"""
    You are a penetration testing expert specializing in web security vulnerability analysis.

    You are provided with structured information about input fields and query parameters from a web page.  
    This information includes technical hints about how the inputs are structured and which HTML attributes or names they contain.

    Your tasks are:
    1. For each input or parameter, infer how it is likely to be used in the context of the application.
    2. Based on this, identify the most likely web vulnerabilities (such as SQL Injection, XSS, CSRF, Open Redirect, etc.) in order of likelihood.
    3. When suggesting possible vulnerabilities, clearly explain **why** you think they are likely by referring to or using the given information.

    ---

    ### Analysis Guidelines

    - Do **not** assume that every input is vulnerable. Only suggest vulnerabilities that are realistically likely based on the provided information (attribute names, field names, query keys, etc.).
    - If you suspect a vulnerability, clearly state the **rationale** behind your assessment.  
    Example: `"name='login'" is likely used for user authentication and may be directly inserted into an SQL query, indicating a high risk of SQL Injection.`

    - Provide a representative **example payload** for each vulnerability type you identify.  
    (However, do not force a fixed number like five—just include **valid and plausible** payloads.)

    - Organize the results by input field or query parameter for clarity.

    ---

    ### Target Page Information

    URL: {url}  

    [Input Field Information]  
    {fields_str}

    [Query Parameters]  
    {params_str}
    """
    return prompt



def query_external_llm(prompt: str, model=UPSTAGE_MODEL) -> str:
    headers = {
        "Authorization": f"Bearer {UPSTAGE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(UPSTAGE_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"[!] Upstage LLM 요청 오류: {e}"


def run_llm_analysis(db_path="data/crawl_links.db"):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT link, input_fields, query_params
            FROM crawl_links
            WHERE input_fields IS NOT NULL AND input_fields != '[]'
        """)
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        click.secho(f"[!] DB 연결 실패: {e}", fg="red")
        return

    if not rows:
        click.secho("[!] 분석할 대상이 없습니다. (input_fields 없음)", fg="yellow")
        return

    click.secho(f"[+] 입력 필드가 있는 URL {len(rows)}개 분석 시작", fg="cyan")

    for url, input_fields_json, query_params_json in rows:
        try:
            raw_fields = json.loads(input_fields_json)
            fields = build_field_list(raw_fields)
            if not fields:
                click.secho(f"\n[🔍] {url}\n  (의미 있는 입력 필드가 없어 분석 생략)", fg="yellow")
                continue
            query_params = json.loads(query_params_json) if query_params_json else {}
        except Exception as e:
            click.secho(f"[!] JSON 파싱 실패: {url} - {e}", fg="red")
            continue

        click.secho(f"\n[🔍] {url}", fg="blue")
        prompt = build_prompt(
            url=url,
            input_fields=fields,
            query_params=query_params
        )

        try:
            result = query_external_llm(prompt)
            if result:
                click.secho(result, fg="green")
            else:
                raise ValueError("LLM 응답이 비어 있음")
        except Exception as e:
            click.secho(f"[!] LLM 분석 실패 또는 결과 파싱 오류: {e}", fg="red")


if __name__ == "__main__":
    run_llm_analysis()
    