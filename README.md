# whspider

WebSpider for WebHacking  
본 프로젝트는 웹 취약점 분석을 위한 맞춤형 웹 스파이더(WebSpider)를 개발하는 WHS3 프로젝트입니다.

---

whspider는 정적/동적 웹 크롤링, 입력필드 추출, 링크 네트워크 시각화,  
LLM(로컬 AI) 기반 자동 보안 분석까지 모두 지원하는 커맨드라인 도구입니다.  
코드/실행파일과 AI 모델(gguf)을 분리 관리하여,  
파인튜닝된 LLM을 자유롭게 교체/연동할 수 있습니다.

---

## 설치 및 환경 준비

### 1. Python 및 Ollama 설치

- Python 3.8 이상 필요
- Ollama(로컬 LLM 엔진) 설치  
  - Mac:    `brew install ollama`
  - Ubuntu: `curl -fsSL https://ollama.com/install.sh | sh`
  - Windows: https://ollama.com/download 참고

### 2. whspider 설치

- 소스 직접 설치:
  `git clone https://github.com/JKprokan/WebSpider-for-WebHacking.git`

  `cd WebSpider-for-WebHacking`

  `pip install .`

## AI 모델(gguf) 및 Modelfile 다운로드
  `ollama pull hf.co/Jin312/WebSpider_Mistral:Q4_K_M`

## 사용 예시

`whspider -u "https://target.com" --llm --graph`

### 주요 옵션 안내

| 옵션           | 설명                             | 기본값 |
|----------------|----------------------------------|--------|
| -u, --url      | 타겟 URL 지정 (필수)             |        |
| --depth        | 크롤링 깊이                      | 1      |
| --static       | 정적 크롤링 (기본값)             | True   |
| --dynamic      | 동적 크롤링 (Playwright)         | False  |
| --llm          | LLM 기반 입력필드 취약점 분석    | False  |
| --json         | JSON 파일로 결과 저장            | False  |
| --csv          | CSV 파일로 결과 저장             | False  |
| --graph        | 링크 네트워크 그래프 생성        | False  |
| --frequency    | 파라미터 빈도 분석               | False  |
| --mode         | dfs/bfs 탐색 방식 선택           | dfs    |
| --cookie       | 요청 시 사용할 쿠키 지정         |        |
| --include      | 포함할 키워드 (쉼표로 구분)      |        |
| --exclude      | 제외할 키워드 (쉼표로 구분)      |        |
| --ignore-robots| robots.txt 규칙 무시             | False  |

**참고:**
- `--static` 또는 `--dynamic` 옵션이 지정되지 않으면 `--static`이 기본으로 적용됩니다.
- 모든 결과 파일(DB, JSON, CSV, 그래프)은 타겟 URL의 도메인 이름을 기반으로 `data/` 디렉토리에 저장됩니다. (예: `suninatas.com` -> `data/suninatas_com.db`, `data/suninatas_com.json`)

전체 옵션은 `whspider --help`로 확인할 수 있습니다.

### 참고
오류, 문의: @@
라이선스: @@

---

영문버전 @@