import sqlite3
import json
import requests
import os
from urllib.parse import urlparse
from modules.frequency import analyze_input_fields, analyze_url_patterns, analyze_parameters, find_interesting_patterns

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


DB_PATH = "data/crawl_links.db"

def get_crawling_summary():
    """크롤링된 데이터의 요약 정보 생성"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM crawl_links")
    total_links = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT host) FROM crawl_links")
    unique_hosts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM crawl_links WHERE input_fields != '[]'")
    pages_with_inputs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM crawl_links WHERE query_params != '{}' ")
    pages_with_params = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(depth) FROM crawl_links")
    max_depth = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT link, input_fields, query_params 
        FROM crawl_links 
        WHERE input_fields != '[]' OR query_params != '{}' 
        LIMIT 20
    """)
    sample_data = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_links': total_links,
        'unique_hosts': unique_hosts,
        'pages_with_inputs': pages_with_inputs,
        'pages_with_params': pages_with_params,
        'max_depth': max_depth,
        'sample_data': sample_data
    }

def call_openai_api(prompt, max_tokens=2000):
    if not OPENAI_API_KEY:
        return "OpenAI API 키가 설정되지 않음."
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 개쩌는 웹 보안 전문가야. 크롤링된 웹사이트 데이터를 분석하여 보안 취약점과 공격 벡터를 식별하는 것이 너의 역할이야. "
                    "실용적이고 구체적인 보안 분석을 제공해줘."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
        
    except requests.exceptions.RequestException as e:
        return f"API 호출 실패: {str(e)}"
    except KeyError as e:
        return f"API 응답 파싱 실패: {str(e)}"

def analyze_attack_vectors():
    summary = get_crawling_summary()
    input_analysis = analyze_input_fields()
    patterns = find_interesting_patterns()
    
    prompt = f"""
다음은 웹 크롤링으로 수집된 데이터야:

## 기본 통계
- 총 링크 수: {summary['total_links']}
- 고유 호스트 수: {summary['unique_hosts']}
- 입력 필드가 있는 페이지: {summary['pages_with_inputs']}
- 쿼리 매개변수가 있는 페이지: {summary['pages_with_params']}
- 최대 크롤링 깊이: {summary['max_depth']}

## 발견된 입력 필드 타입
{json.dumps(input_analysis['field_types'], indent=2, ensure_ascii=False)}

## 발견된 입력 필드 이름
{json.dumps(dict(list(input_analysis['field_names'].items())[:20]), indent=2, ensure_ascii=False)}

## 흥미로운 패턴
{json.dumps(patterns, indent=2, ensure_ascii=False)}

위 데이터를 바탕으로 다음을 분석해줘:

1. 주요 공격 벡터: 발견된 입력 필드와 매개변수를 기반으로 가능한 공격 방법들
2. 우선순위 타겟: 보안 테스트에서 우선적으로 확인해야 할 페이지들
3. 취약점 가능성: 각 입력 필드 타입별로 예상되는 취약점들
4. 추가 테스트 권장사항: 수동 테스트나 추가 도구 사용 권장사항

한국어로 실용적이고 구체적인 분석을 제공해줘.
"""
    
    return call_openai_api(prompt)

def suggest_hidden_endpoints():
    url_analysis = analyze_url_patterns()
    
    prompt = f"""
다음은 크롤링에서 발견된 URL 패턴들이야.:

## 발견된 경로들
{json.dumps(dict(list(url_analysis['paths'].items())[:30]), indent=2, ensure_ascii=False)}

## 발견된 디렉토리들
{json.dumps(dict(list(url_analysis['directories'].items())[:30]), indent=2, ensure_ascii=False)}

## 발견된 확장자들
{json.dumps(url_analysis['extensions'], indent=2, ensure_ascii=False)}

## 발견된 서브도메인들
{json.dumps(url_analysis['subdomains'], indent=2, ensure_ascii=False)}

위 패턴을 분석하여 다음을 추측해줘:

1. 숨겨진 관리자 페이지: 존재할 가능성이 높은 관리자 인터페이스들
2. API 엔드포인트: 발견되지 않은 API 경로들
3. 백업/설정 파일: 노출될 수 있는 민감한 파일들
4. 개발/테스트 페이지: 개발 과정에서 남겨진 페이지들
5. 추가 서브도메인: 존재할 가능성이 있는 다른 서브도메인들

각 추측에 대해 실제 URL 예시와 함께 제시해야해.
한국어로 답변해줘.
"""
    
    return call_openai_api(prompt)

def analyze_input_security():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT link, input_fields 
        FROM crawl_links 
        WHERE input_fields != '[]' 
        ORDER BY RANDOM() 
        LIMIT 10
    """)
    sample_forms = cursor.fetchall()
    conn.close()
    
    forms_data = []
    for link, input_fields_json in sample_forms:
        try:
            fields = json.loads(input_fields_json)
            forms_data.append({
                'url': link,
                'fields': fields
            })
        except json.JSONDecodeError:
            continue
    
    prompt = f"""
다음은 크롤링에서 발견된 입력 폼들의 샘플이야.:

{json.dumps(forms_data, indent=2, ensure_ascii=False)}

각 폼을 분석하여 다음을 제공해줘.:

1. XSS 취약점 가능성: 각 입력 필드별 XSS 공격 가능성과 테스트 페이로드
2. SQL Injection 가능성: 데이터베이스와 연동될 가능성이 있는 필드들
3. 파일 업로드 보안: 파일 업로드 필드의 보안 위험성
4. CSRF 보호 여부: 폼에 CSRF 토큰이나 보호 메커니즘 확인
5. 입력 검증 우회: 클라이언트 사이드 검증 우회 방법들

각 취약점에 대해 구체적인 테스트 방법과 페이로드를 포함해서 설명해줘.
한국어로 답변해줘.
"""
    
    return call_openai_api(prompt)

def generate_comprehensive_report():
    param_analysis = analyze_parameters()
    
    prompt = f"""
다음은 크롤링에서 발견된 매개변수들이야.:

## 주요 매개변수들
{json.dumps(dict(list(param_analysis['parameter_names'].items())[:20]), indent=2, ensure_ascii=False)}

## 매개변수별 값들 (샘플)
{json.dumps({k: v for k, v in list(param_analysis['parameter_values'].items())[:10]}, indent=2, ensure_ascii=False)}

이전 분석 결과들과 함께 종합적인 보안 분석 리포트를 작성해줘.:

1. 전체 보안 상태 평가: 발견된 웹사이트의 전반적인 보안 수준
2. 가장 심각한 위험요소: 즉시 확인해야 할 보안 이슈들
3. 매개변수 기반 공격: URL 매개변수를 통한 공격 방법들
4. 권장 테스트 순서: 효율적인 보안 테스트 진행 순서
5. 자동화 도구 추천: 추가로 사용할 보안 스캐닝 도구들

실무에서 바로 사용할 수 있는 구체적이고 실용적인 리포트를 작성해줘.
한국어로 답변해줘.
"""
    
    return call_openai_api(prompt)

def run_llm_analysis():
    print("\n" + "="*80)
    print("LLM SECURITY ANALYSIS REPORT")
    print("="*80)
    
    print("\nATTACK VECTORS ANALYSIS")
    print("-" * 60)
    attack_analysis = analyze_attack_vectors()
    print(attack_analysis)
    
    print("\n" + "="*80)
    print("\nHIDDEN ENDPOINTS SUGGESTIONS")
    print("-" * 60)
    endpoint_suggestions = suggest_hidden_endpoints()
    print(endpoint_suggestions)
    
    print("\n" + "="*80)
    print("\nINPUT FIELDS SECURITY ANALYSIS")
    print("-" * 60)
    input_security = analyze_input_security()
    print(input_security)
    
    print("\n" + "="*80)
    print("\nCOMPREHENSIVE SECURITY REPORT")
    print("-" * 60)
    comprehensive_report = generate_comprehensive_report()
    print(comprehensive_report)
    
    report_data = {
        'attack_vectors': attack_analysis,
        'hidden_endpoints': endpoint_suggestions,
        'input_security': input_security,
        'comprehensive_report': comprehensive_report
    }
    
    os.makedirs("data", exist_ok=True)
    with open("data/llm_analysis_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print("\n분석 결과가 data/llm_analysis_report.json에 저장되었습니다.")
    
    return report_data
