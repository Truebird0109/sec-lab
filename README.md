# sec-lab

모의해킹 / 침투테스트 실습 환경 모음입니다.  
각 폴더는 블로그 글과 1:1로 대응되며, Docker로 바로 띄울 수 있습니다.

---

## 실습 목록

| 폴더 | 주제 | 설명 |
|------|------|--------|
| [ssrf-url-parser-confusion](./ssrf-url-parser-confusion) | SSRF & URL Parser Confusion | [블로그](https://7rueb1rd.tistory.com/44) |

---

## 사용 방법

모든 실습 환경은 Docker Compose 기반입니다.

```bash
cd <폴더명>
docker compose up -d --build
```

종료할 때는

```bash
docker compose down
```

---

## 환경 요구사항

- Docker 24.0 이상
- Docker Compose v2 이상

---

## 주의사항

이 레포의 모든 실습 환경은 로컬에서만 사용합니다.  
허가 없이 외부 시스템에 사용하는 건 불법입니다.
