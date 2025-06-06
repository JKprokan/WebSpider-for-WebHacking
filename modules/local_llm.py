import sqlite3
import json
import click
import subprocess
from urllib.parse import urlparse, parse_qs


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
You are a web security analyst. You are given input field metadata and query parameters extracted from a web application.

Your task is to analyze each field and return a structured, concise summary as follows:

- For each input field or query parameter:
  - Describe its **likely use** (e.g., login field, search field, etc.).
  - Identify any **likely vulnerability** (e.g., SQL Injection, XSS, CSRF, etc.).
  - Map the vulnerability to the **relevant OWASP Top 10 category** (e.g., A03: Injection).
  - Do **not include excessive explanation or justification**.
  - Return only the structured result in the specified format.

Use this format:

[
  {{
    "field": "FIELD_NAME",
    "usage": "LIKELY_USAGE",
    "vulnerability": "VULNERABILITY_TYPE",
    "owasp10": "OWASP_CATEGORY"
  }},
  ...
]

Example:
[
  {{
    "field": "username",
    "usage": "login field",
    "vulnerability": "SQL Injection",
    "owasp10": "A03: Injection"
  }}
]

Do not return anything outside this format.

---

Target URL: {url}

[Input Fields]
{fields_str}

[Query Parameters]
{params_str}
    """
    return prompt

def query_local_llm(prompt: str) -> str:
    result = subprocess.run(
        ["ollama", "run", "llama3.2"],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


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
            result = query_local_llm(prompt)
            if result:
                click.secho(result, fg="green")
            else:
                raise ValueError("LLM 응답이 비어 있음")
        except Exception as e:
            click.secho(f"[!] LLM 분석 실패 또는 결과 파싱 오류: {e}", fg="red")


if __name__ == "__main__":
    run_llm_analysis()
