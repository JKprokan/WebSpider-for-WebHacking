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
        "You are an expert web security analyst. Your task is to analyze the provided web page data for potential vulnerabilities based on common attack patterns and context. "
        "Your response MUST be a single, valid, pretty-printed JSON object OR a JSON array of objects `[{}, {}, ...]` if you find multiple vulnerabilities. "
        "Do not include any other text, explanations, or markdown. "
        
        "The JSON object(s) must include: "
        '"category", "attack_type", "parameter", "usage", "payload", "tool", "indicator", "confidence_score", "reasoning". '
        
        "**Crucial Instructions for `confidence_score` and `reasoning`:** "
        "Your `confidence_score` (float from 0.0 to 1.0) and `reasoning` (string) MUST be based on the following expert heuristics: "
        
        "1. **SQL Injection (SQLi):** "
        "   - **HIGH (0.8-1.0):** Assign for parameters like `id`, `password`, `search`, `user_id`, `uid`. "
        "   - **LOW (0.1-0.3):** Assign for generic fields like `comment`, `message`. "
        
        "2. **Cross-Site Scripting (XSS):** "
        "   - **HIGH (0.8-1.0):** Assign for fields where user input is displayed, like `comment`, `message`, `post`, `searchK`, especially in URLs with `/board/`, `/view/`. "

        "3. **Open Redirect:** "
        "   - **HIGH (0.8-1.0):** Assign for query parameters named `url`, `redirect`, `next`, `goto`, `return_to` that contain a URL as their value. "
        
        "4. **Command Injection:** "
        "   - **VERY LOW (0.1-0.2):** Assign only for highly suggestive names like `cmd`, `exec`. Never assign high confidence for this in fields like `comment` or `_csrf`. "

        "5. **No Vulnerability Found:** "
        "   - If no vulnerability is reasonably suspected, you MUST respond with an empty JSON array `[]`. "

        "- Your `reasoning` MUST explicitly state which rule you followed. "
        "- Do not analyze security tokens like `_csrf` as attackable parameters. "
        
        "Analyze ALL provided `input_fields` and `query_params`. If you find vulnerabilities in multiple fields/params, return one JSON object for each in a single JSON array. "
        "Analyze the following data: "
        f"{json_str} [/INST]"
    )
    return prompt

def extract_json_from_text(text: str) -> str:
    """
    텍스트에서 JSON 객체 또는 배열을 추출합니다. LLM의 일반적인 형식 오류를 수정합니다.
    """
    # LLM이 `[{}],[{}]` 와 같이 잘못된 형식을 생성하는 경우를 대비해 정리
    # 여러 줄에 걸쳐 있을 수 있는 패턴도 처리
    cleaned_text = text.replace("]\n,[", ",").replace("], [", ",").replace("],[", ",")

    # 1. JSON 배열 `[...]` 먼저 시도
    start_arr = cleaned_text.find('[')
    end_arr = cleaned_text.rfind(']')
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        json_part = cleaned_text[start_arr:end_arr+1]
        try:
            # 파싱 전에 최종적으로 한 번 더 정리
            json.loads(json_part)
            return json_part
        except json.JSONDecodeError:
            pass # 객체 시도로 넘어감

    # 2. JSON 객체 `{...}` 시도
    start_obj = cleaned_text.find('{')
    end_obj = cleaned_text.rfind('}')
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        # 배열 안에 있는 객체가 아닌지 확인
        if not (start_arr != -1 and end_arr != -1 and start_arr < start_obj and end_obj < end_arr):
             json_part = cleaned_text[start_obj:end_obj+1]
             try:
                json.loads(json_part)
                return json_part
             except json.JSONDecodeError:
                pass

    # 3. 키: 값 형태의 비정형 텍스트를 JSON 객체로 변환 (단일 객체만 지원)
    if '[' not in cleaned_text and ':' in cleaned_text:
        lines = cleaned_text.strip().split('\n')
        json_dict = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().replace('"', '').replace("'", "")
                value = value.strip()
                if value.endswith(','):
                    value = value[:-1]
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'" ) and value.endswith("'")):
                    value = value[1:-1]
                json_dict[key] = value
        
        if json_dict:
            return json.dumps(json_dict, indent=2, ensure_ascii=False)

    return text # 모든 방법이 실패하면 원본 반환

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
            ["ollama", "run", "hf.co/Jin312/WebSpider_Mistral:Q4_K_M"],
            input=prompt,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        click.secho(f"[!] Ollama 실행 실패: {e}", fg="red")
        return ""

def run_llm_analysis(db_path, url):
    """
    전체 분석 워크플로우
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t1.link, t1.input_fields, t1.query_params
            FROM crawl_links t1
            INNER JOIN (
                SELECT link, MAX(collected_time) AS max_time
                FROM crawl_links
                GROUP BY link
            ) t2
            ON t1.link = t2.link AND t1.collected_time = t2.max_time
            WHERE (t1.input_fields IS NOT NULL AND t1.input_fields != '[]') 
               OR (t1.query_params IS NOT NULL AND t1.query_params != '{}')
        """)
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        click.secho(f"[!] DB 연결 실패: {e}", fg="red")
        return

    if not rows:
        click.secho("[!] 분석할 대상이 없습니다.", fg="yellow")
        return

    click.secho(f"[+] 분석 대상 URL {len(rows)}개 분석 시작", fg="cyan")

    for url, input_fields_json, query_params_json in rows:
        try:
            raw_fields = json.loads(input_fields_json)
            fields = build_field_list(raw_fields)
            query_params = json.loads(query_params_json) if query_params_json else {}
        except Exception as e:
            click.secho(f"[!] 데이터 파싱 실패: {url} - {e}", fg="red")
            continue

        if not fields and not query_params:
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
                    
                    if isinstance(parsed, list) and not parsed:
                        click.secho(f"  (분석 결과 없음)", fg="yellow")
                        continue

                    if isinstance(parsed, list):
                        filtered_results = [res for res in parsed if res.get("confidence_score", 0.0) >= 0.1]
                        if not filtered_results:
                            click.secho(f"  (낮은 신뢰도 결과만 있어 생략)", fg="yellow")
                            continue
                        pretty_fieldwise_click_secho(filtered_results, color="green")
                    elif isinstance(parsed, dict):
                        if parsed.get("confidence_score", 0.0) < 0.1:
                            click.secho(f"  (낮은 신뢰도({parsed.get('confidence_score')})로 결과 생략)", fg="yellow")
                            continue
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