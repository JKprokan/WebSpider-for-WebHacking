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

def build_prompt(url, input_fields, query_params):
    user_content = {
        "url": url,
        "input_fields": input_fields,
        "query_params": query_params,
    }
    json_str = json.dumps(user_content, ensure_ascii=False, separators=(',', ':'))
    prompt = (
        "<s>[INST] "
        "Analyze the following input fields and query parameters for security vulnerabilities. "
        "Respond only with pretty-printed JSON (with indentation and line breaks), and do not include any explanations or markdown formatting. "
        f"{json_str} [/INST]"
    )
    return prompt

def extract_json_from_text(text):
    """
    텍스트에서 가장 첫 '{'와 마지막 '}' 사이만 추출
    (LLM이 앞뒤로 텍스트를 붙여도 JSON만 파싱할 수 있도록)
    """
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text

def pretty_fieldwise_click_secho(parsed, color="green"):
    """
    딕셔너리 key-value를 보기 좋게 출력
    여러 건(리스트)도 모두 순회하며 출력
    """
    if isinstance(parsed, list):
        for idx, obj in enumerate(parsed):
            click.secho(f"\n--- Result {idx+1} ---", fg=color)
            for k, v in obj.items():
                click.secho(f"{k}: {v}", fg=color)
        click.secho("", fg=color)
    else:
        for k, v in parsed.items():
            click.secho(f"{k}: {v}", fg=color)
        click.secho("", fg=color)

def query_local_llm(prompt: str) -> str:
    """
    Ollama LLM에 프롬프트 전달, 결과 반환
    """
    try:
        result = subprocess.run(
            ["ollama", "run", "mistral-fine"],
            input=prompt,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        click.secho(f"[!] Ollama 실행 실패: {e}", fg="red")
        return ""

def run_llm_analysis(db_path="data/crawl_links.db"):
    """
    전체 분석 워크플로우
    """
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
                try:
                    pure_json = extract_json_from_text(result)
                    parsed = json.loads(pure_json)
                    pretty_fieldwise_click_secho(parsed, color="green")
                except Exception as e:
                    click.secho(f"[!] JSON 파싱 실패 또는 예상 외 포맷: {e}", fg="red")
                    click.secho(result, fg="green")
            else:
                raise ValueError("LLM 응답이 비어 있음")
        except Exception as e:
            click.secho(f"[!] LLM 분석 실패 또는 결과 파싱 오류: {e}", fg="red")

if __name__ == "__main__":
    run_llm_analysis()
