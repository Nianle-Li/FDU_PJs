from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .api import ApiRouter
from .config import AppConfig
from .errors import ApiError
from .repositories import CampusRepository, create_repository
from .serialization import json_default


def content_type_for(path: Path) -> str:
    if path.suffix == ".html":
        return "text/html; charset=utf-8"
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".js":
        return "application/javascript; charset=utf-8"
    return "text/plain; charset=utf-8"


def make_handler(router: ApiRouter, frontend_dir: Path) -> type[BaseHTTPRequestHandler]:
    frontend_dir = frontend_dir.resolve()

    class AppHandler(BaseHTTPRequestHandler):
        server_version = "FCQA/0.1"

        def do_GET(self) -> None:
            self.dispatch("GET")

        def do_POST(self) -> None:
            self.dispatch("POST")

        def do_PUT(self) -> None:
            self.dispatch("PUT")

        def do_DELETE(self) -> None:
            self.dispatch("DELETE")

        def do_OPTIONS(self) -> None:
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_cors_headers()
            self.end_headers()

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"{self.address_string()} - {fmt % args}")

        def dispatch(self, method: str) -> None:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self.handle_api(method, parsed.path, parse_qs(parsed.query))
                return
            self.serve_static(parsed.path)

        def handle_api(self, method: str, path: str, raw_query: dict[str, list[str]]) -> None:
            query = {key: values[-1] for key, values in raw_query.items() if values}
            try:
                data = router.route(method, path, query, self.read_json)
                self.send_json(data)
            except ApiError as exc:
                self.send_json({"error": exc.message}, status=exc.status)
            except Exception as exc:
                self.send_json({"error": f"服务内部错误：{exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        def read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ApiError(HTTPStatus.BAD_REQUEST, "请求体不是合法 JSON") from exc

        def send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False, default=json_default).encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def serve_static(self, path: str) -> None:
            if path in {"", "/"}:
                path = "/index.html"
            elif path == "/admin":
                path = "/admin.html"
            requested = (frontend_dir / path.lstrip("/")).resolve()
            if frontend_dir not in requested.parents and requested != frontend_dir:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            if not requested.exists() or not requested.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = requested.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type_for(requested))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return AppHandler


def create_server(config: AppConfig, repository: CampusRepository | None = None) -> ThreadingHTTPServer:
    resolved_repository = repository or create_repository(config)
    router = ApiRouter(resolved_repository)
    handler = make_handler(router, config.frontend_dir)
    return ThreadingHTTPServer((config.host, config.port), handler)


def run_server(config: AppConfig) -> None:
    server = create_server(config)
    mode_text = "demo data" if config.demo_mode else f"PostgreSQL {config.database_url}"
    print(f"FCQA server listening on http://{config.host}:{config.port} ({mode_text})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        server.server_close()
