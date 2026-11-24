"""End-to-end smoke test against a temporary copy of the game config."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import app


def request(
    base_url: str,
    path: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        payload = json.loads(error.read().decode("utf-8"))
        raise AssertionError(f"{method} {path} -> {error.code}: {payload}") from error


def main() -> None:
    temporary_root = Path(tempfile.mkdtemp(prefix="dd2-manager-selftest-"))
    server = None
    try:
        temporary_config = temporary_root / "config.json"
        shutil.copy2(app.CONFIG_PATH, temporary_config)
        app.CONFIG_PATH = temporary_config
        app.PROFILE_DIR = temporary_root / "profiles"
        app.TRASH_DIR = temporary_root / "trash"
        app.BACKUP_DIR = temporary_root / "backups"

        server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"

        state = request(base_url, "/api/state")
        assert len(state["current"]) == 3
        assert [item["slot"] for item in state["current"]] == [
            "pawn0",
            "pawn1",
            "pawn2",
        ]

        created = request(
            base_url,
            "/api/profiles",
            "POST",
            {
                "id": "selftest-profile",
                "display_name": "自动测试配置",
                "notes": "临时副本验证",
                "source_slot": "pawn0",
            },
        )["profile"]
        assert created["id"] == "selftest-profile"
        assert created["summary"]["name"] == state["current"][0]["name"]

        detail = request(base_url, "/api/profiles/selftest-profile")
        assert isinstance(detail["data"]["clone"], dict)
        profile_data = detail["data"]

        edited = request(
            base_url,
            "/api/profiles/selftest-profile",
            "PUT",
            {"display_name": "自动测试配置（已编辑）", "notes": "编辑成功"},
        )["profile"]
        assert edited["display_name"] == "自动测试配置（已编辑）"

        duplicate = request(
            base_url,
            "/api/profiles/selftest-profile/duplicate",
            "POST",
            {"id": "selftest-copy", "display_name": "自动测试配置副本"},
        )["profile"]
        assert duplicate["data"] == profile_data

        before = json.loads(temporary_config.read_text(encoding="utf-8-sig"))
        sections = list(app.SECTION_FIELDS)
        applied = request(
            base_url,
            "/api/apply",
            "POST",
            {
                "profile_id": "selftest-profile",
                "targets": ["pawn1", "pawn2"],
                "sections": sections,
            },
        )
        assert applied["applied"] is True
        assert applied["targets"] == ["pawn1", "pawn2"]
        assert Path(applied["backup"]).is_file()

        written = json.loads(temporary_config.read_text(encoding="utf-8-sig"))
        for target in ("pawn1", "pawn2"):
            for section in sections:
                for field in app.SECTION_FIELDS[section]:
                    if field in profile_data:
                        assert written[target][field] == profile_data[field]
        assert written["pawn0"] == before["pawn0"]

        backup_data = json.loads(Path(applied["backup"]).read_text(encoding="utf-8-sig"))
        assert backup_data == before

        imported = request(
            base_url,
            "/api/profiles/import",
            "POST",
            {
                "id": "selftest-import",
                "display_name": "导入测试",
                "data": copy.deepcopy(profile_data),
            },
        )["profile"]
        assert imported["id"] == "selftest-import"

        deleted = request(base_url, "/api/profiles/selftest-profile", "DELETE")
        assert Path(deleted["trashed_to"]).is_file()
        assert not (app.PROFILE_DIR / "selftest-profile.json").exists()

        print(
            json.dumps(
                {
                    "ok": True,
                    "current_pawns": [
                        f'{item["slot"]}:{item["name"]}/{item["job"]}'
                        for item in state["current"]
                    ],
                    "tested": [
                        "state",
                        "create",
                        "detail",
                        "edit",
                        "duplicate",
                        "apply",
                        "backup",
                        "import",
                        "delete-to-trash",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        shutil.rmtree(temporary_root, ignore_errors=True)


if __name__ == "__main__":
    main()
