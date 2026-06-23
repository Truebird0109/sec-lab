from flask import Flask, request, jsonify, render_template
import requests
import socket
import ipaddress
from urllib.parse import urlparse

app = Flask(__name__)

# ── 허용 도메인 allowlist ──────────────────────────────────
ALLOWED_DOMAINS = ["images.example.com", "cdn.example.com"]

# ── 사설 IP 대역 ───────────────────────────────────────────
PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # 클라우드 메타데이터
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


# ──────────────────────────────────────────────────────────
# [취약] netloc으로 검증 → @ / \ 파서 컨퓨전에 뚫림
# ──────────────────────────────────────────────────────────
def is_safe_weak(url: str) -> bool:
    parsed = urlparse(url)
    domain = parsed.netloc  # userinfo(@) 포함, 백슬래시 포함
    # 취약: netloc에 허용 도메인이 "포함"되는지만 확인 → @ / \ 컨퓨전에 뚫림
    return any(d in domain for d in ALLOWED_DOMAINS)


# ──────────────────────────────────────────────────────────
# [안전] hostname + DNS 해석 + 사설 IP 차단
# ──────────────────────────────────────────────────────────
def is_safe_strong(url: str) -> bool:
    parsed = urlparse(url)

    # 스킴 allowlist
    if parsed.scheme not in ("http", "https"):
        return False

    # netloc이 아닌 hostname 사용 (@ 이후 실제 호스트)
    host = parsed.hostname
    if not host:
        return False

    # 백슬래시 명시적 차단
    if "\\" in url:
        return False

    # 정확히 허용 도메인과 일치하는지 확인
    if host not in ALLOWED_DOMAINS:
        return False

    # DNS 해석 후 사설 IP 차단
    try:
        ip_str = socket.gethostbyname(host)
        ip = ipaddress.ip_address(ip_str)
    except Exception:
        return False

    for private in PRIVATE_RANGES:
        if ip in private:
            return False

    return True


# ── 엔드포인트 ────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/fetch-weak")
def fetch_weak():
    """
    취약한 SSRF 엔드포인트.
    urlparse의 netloc으로만 검증 → 파서 컨퓨전으로 우회 가능.
    """
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "url parameter required"}), 400

    if not is_safe_weak(url):
        return jsonify({"error": "Blocked by WAF"}), 403

    try:
        # allow_redirects=True (기본값) → 302 리다이렉트도 자동 추적
        r = requests.get(url, timeout=5)
        return jsonify({"status": r.status_code, "body": r.text[:1000]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/fetch-strong")
def fetch_strong():
    """
    안전한 엔드포인트 (비교용).
    hostname 검증 + DNS 체크 + 리다이렉트 차단.
    """
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "url parameter required"}), 400

    if not is_safe_strong(url):
        return jsonify({"error": "Blocked by WAF"}), 403

    try:
        r = requests.get(url, timeout=5, allow_redirects=False)
        return jsonify({"status": r.status_code, "body": r.text[:1000]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/internal-secret")
def internal_secret():
    """
    외부에서 직접 접근하면 안 되는 민감 엔드포인트.
    SSRF로 접근 성공 여부를 확인하기 위한 목표 지점.
    """
    return jsonify({
        "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
        "aws_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "db_password": "Admin123!",
        "message": "이 데이터가 보인다면 SSRF 성공!"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
