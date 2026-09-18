#!/usr/bin/env python3
"""미리보기 서버.

`python -m http.server` 와 같지만 캐시를 쓰지 않도록 헤더를 붙인다.
그림이나 영상을 다시 만들어도 브라우저가 옛 파일을 보여주지 않는다.

    python serve.py               # http://0.0.0.0:8777
    python serve.py --port 9000
    python serve.py --bind 127.0.0.1   # 외부에 노출하지 않음
"""

import argparse
import functools
import http.server
import socketserver
from pathlib import Path

PAGE_DIR = Path(__file__).resolve().parent


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_head(self):
        # 조건부 요청 헤더를 지워 304 Not Modified 가 나가지 않게 한다.
        del self.headers["If-Modified-Since"]
        del self.headers["If-None-Match"]
        return super().send_head()


def get_parser():
    p = argparse.ArgumentParser(description="프로젝트 페이지 미리보기 서버")
    p.add_argument("--port", type=int, default=8777)
    p.add_argument("--bind", default="0.0.0.0",
                   help="기본은 모든 인터페이스. SSH 포트 포워딩만 쓸 때는 127.0.0.1 권장")
    return p


def main():
    args = get_parser().parse_args()
    handler = functools.partial(NoCacheHandler, directory=str(PAGE_DIR))

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.bind, args.port), handler) as httpd:
        print("{} 를 http://{}:{} 로 제공합니다 (캐시 없음)".format(
            PAGE_DIR.name, args.bind, args.port))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n중지")


if __name__ == "__main__":
    main()
