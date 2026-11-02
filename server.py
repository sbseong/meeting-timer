"""브라우저 대시보드용 작은 웹 서버 (표준 라이브러리만 사용).

GET /            대시보드 화면
GET /api/state   현재·다음 회의, 오늘·내일 일정 (JSON)
POST /api/refresh  캘린더 바로 다시 받기
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from calendar_source import CalendarFeed

STATIC = Path(__file__).resolve().parent / "static"


def make_handler(feed: CalendarFeed):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _local_only(self) -> bool:
            """다른 웹사이트가 일정을 몰래 읽지 못하게 한다 (DNS 리바인딩·CSRF 방지).
            Host 는 127.0.0.1/localhost 만, Origin 이 있으면 같은 주소일 때만 허용."""
            port = self.server.server_address[1]
            allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if self.headers.get("Host", "") not in allowed:
                self._send(403, b"forbidden", "text/plain")
                return False
            origin = self.headers.get("Origin")
            if origin and origin.split("://", 1)[-1] not in allowed:
                self._send(403, b"forbidden", "text/plain")
                return False
            return True

        def do_GET(self):
            if not self._local_only():
                return
            if self.path in ("/", "/index.html"):
                self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                body = json.dumps(feed.snapshot(), ensure_ascii=False).encode()
                self._send(200, body, "application/json; charset=utf-8")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if not self._local_only():
                return
            if self.path == "/api/refresh":
                feed.refresh_now()
                self._send(200, b"{}", "application/json")
            else:
                self._send(404, b"not found", "text/plain")

        def log_message(self, *args):  # 접속 로그는 끈다
            pass

    return Handler


def serve(feed: CalendarFeed, port: int, background: bool = True):
    # 127.0.0.1 에만 열어서 같은 맥에서만 볼 수 있게 한다
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(feed))
    if background:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
    else:
        httpd.serve_forever()
    return httpd


if __name__ == "__main__":
    feed = CalendarFeed()
    feed.start_background()
    port = feed.cfg.get("port", 8765)
    print(f"http://127.0.0.1:{port}")
    serve(feed, port, background=False)
