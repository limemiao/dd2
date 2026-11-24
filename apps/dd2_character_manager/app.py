"""Local character preset manager for Dragon's Dogma 2 pawn configuration.

The server binds to localhost, stores reusable presets in this workspace, and
writes ThePawnController config only when DD2.exe is closed.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
GAME_ROOT = Path(os.environ.get(
    "DD2_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\Dragons Dogma 2",
))
CONFIG_PATH = GAME_ROOT / "reframework" / "data" / "ThePawnController" / "config.json"
ITEM_DATA_PATH = CONFIG_PATH.parent / "itemData.json"
SKILLS_PATH = WORKSPACE / "catalogs" / "dd2_skill_catalog" / "skills.json"
EQUIPMENT_PATH = WORKSPACE / "catalogs" / "dd2_equipment_catalog" / "catalog.json"
PROFILE_DIR = ROOT / "profiles"
TRASH_DIR = ROOT / "trash"
BACKUP_DIR = WORKSPACE / "game_config_backups"
INDEX_PATH = ROOT / "index.html"

PROFILE_FORMAT = "lime-dd2-character-manager.profile"
PROFILE_VERSION = 1
MAX_BODY_BYTES = 32 * 1024 * 1024

JOB_NAMES = {
    1: "战士",
    2: "弓箭手",
    3: "法师",
    4: "盗贼",
    5: "斗士",
    6: "巫师",
    7: "魔剑士",
    8: "魔弓手",
    9: "幻术师",
    10: "龙选者",
}

SPECIALIZATION_NAMES = {
    0: "无",
    1: "森林语学者",
    2: "外科医生",
    3: "后勤专家",
    4: "商人",
    5: "采集者",
    6: "阿弗尼特",
}

EQUIPMENT_ORDER = (
    "Main",
    "Sub",
    "Head",
    "Upper",
    "Lower",
    "Mantle",
    "Jewelry_00",
    "Jewelry_01",
    "Visual",
)

SECTION_FIELDS = {
    "identity": (
        "enabled",
        "name",
        "nickname",
        "name_moniker",
        "personality",
        "specialization",
    ),
    "appearance": ("clone", "clone_keep"),
    "voice": ("voice_gender", "voice_tone"),
    "vocation": (
        "job",
        "job_rank",
        "level",
        "level_keep",
        "skills",
        "skill_levels",
        "abilities",
        "core",
        "extra_aug",
    ),
    "equipment": ("equipment", "enhance", "eq_skills"),
    "behavior": (
        "chatter",
        "plague_immune",
        "knowledge",
        "knowledge_raw",
        "possession",
        "qol",
    ),
}

TECHNICAL_FIELDS = {"owner", "sid", "eq_sid", "names", "status", "chara_id"}
SENTINEL_FIELDS = {
    "job",
    "job_rank",
    "level",
    "personality",
    "specialization",
    "voice_gender",
    "voice_tone",
}


class ApiError(Exception):
    def __init__(self, message: str, status: int = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = int(status)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".limewrite.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_modified_at(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(
        timespec="seconds"
    )


def game_is_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/NH"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    lowered = result.stdout.casefold()
    return "dd2.exe" in lowered or "dragonsdogma2.exe" in lowered


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def meaningful_override(key: str, value: Any) -> bool:
    if key == "enabled":
        return isinstance(value, bool)
    if key in SENTINEL_FIELDS:
        return isinstance(value, (int, float)) and value not in (0, -1)
    if key in ("name", "nickname") and value in (None, ""):
        return False
    if isinstance(value, list):
        return any(item not in (0, None, "") for item in value)
    if isinstance(value, dict):
        def has_value(item: Any) -> bool:
            if isinstance(item, dict):
                return any(has_value(child) for child in item.values())
            if isinstance(item, list):
                return any(has_value(child) for child in item)
            if isinstance(item, bool):
                return item
            return item not in (0, 0.0, -1, None, "")

        return has_value(value)
    return value is not None


def effective_pawn(config: dict[str, Any], slot: int) -> tuple[dict[str, Any], dict[str, Any]]:
    if slot not in (0, 1, 2):
        raise ApiError("随从槽位必须是 pawn0、pawn1 或 pawn2")
    override = config.get(f"pawn{slot}")
    original_record = config.get("originals", {}).get(f"slot{slot}", {})
    original = original_record.get("data") if isinstance(original_record, dict) else {}
    if not isinstance(override, dict) or not isinstance(original, dict):
        raise ApiError(f"配置中缺少 pawn{slot} 或 originals.slot{slot}")

    result = copy.deepcopy(original)
    for key, value in override.items():
        if key in TECHNICAL_FIELDS or not meaningful_override(key, value):
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    original_job = int(original.get("job", 0) or 0)
    effective_job = int(result.get("job", 0) or 0)
    if effective_job and original_job and effective_job != original_job:
        # Zero-filled skill arrays mean "no override" for the original job,
        # but they must not leak the previous vocation's skills into a new one.
        if not any(int(value or 0) for value in override.get("skills", [])):
            result["skills"] = [0] * len(result.get("skills", []))
        if not override.get("core"):
            result["core"] = {}
    return result, override


def profile_path(profile_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", profile_id):
        raise ApiError("无效的配置 ID")
    return PROFILE_DIR / f"{profile_id}.json"


def read_profile(profile_id: str) -> dict[str, Any]:
    path = profile_path(profile_id)
    if not path.is_file():
        raise ApiError("角色配置不存在", HTTPStatus.NOT_FOUND)
    payload = read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ApiError(f"角色配置损坏：{path.name}", HTTPStatus.INTERNAL_SERVER_ERROR)
    return payload


def list_profiles() -> list[dict[str, Any]]:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    profiles: list[dict[str, Any]] = []
    for path in PROFILE_DIR.glob("*.json"):
        try:
            profiles.append(read_json(path))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return sorted(
        profiles,
        key=lambda item: (
            str(item.get("display_name", "")).casefold(),
            str(item.get("created_at", "")),
        ),
    )


def load_lookups() -> tuple[dict[tuple[int, int], str], dict[int, str], dict[int, str]]:
    skill_names: dict[tuple[int, int], str] = {}
    ability_names: dict[int, str] = {}
    if SKILLS_PATH.is_file():
        skills = read_json(SKILLS_PATH)
        for job in skills.get("jobs", []):
            catalog_job_id = int(job.get("id") or 0)
            for group in job.get("skills", []):
                for variant in group.get("variants", []):
                    if variant.get("kind") == "武器技能" and variant.get("skill_id") is not None:
                        variant_job_id = int(variant.get("job_id") or catalog_job_id)
                        key = (variant_job_id, int(variant["skill_id"]))
                        skill_names.setdefault(key, str(
                            variant.get("name") or f"技能 {variant['skill_id']}"
                        ))
                    if variant.get("kind") == "强化能力" and variant.get("ability_id") is not None:
                        ability_names.setdefault(int(variant["ability_id"]), str(
                            variant.get("name") or f"强化能力 {variant['ability_id']}"
                        ))

    equipment_names: dict[int, str] = {}
    if EQUIPMENT_PATH.is_file():
        catalog = read_json(EQUIPMENT_PATH)
        for item in catalog:
            equipment_names[int(item["id"])] = str(item.get("name") or item["id"])
    if ITEM_DATA_PATH.is_file():
        items = read_json(ITEM_DATA_PATH)
        for item_id, item in items.items():
            if isinstance(item, dict):
                equipment_names.setdefault(int(item_id), str(item.get("name") or item_id))
    return skill_names, ability_names, equipment_names


SKILL_NAMES, ABILITY_NAMES, EQUIPMENT_NAMES = load_lookups()


def id_name(
    identifier: Any,
    names: dict[Any, str],
    prefix: str,
    lookup_key: Any | None = None,
) -> dict[str, Any]:
    try:
        numeric = int(identifier or 0)
    except (TypeError, ValueError):
        numeric = 0
    return {
        "id": numeric,
        "name": names.get(numeric if lookup_key is None else lookup_key, f"{prefix} {numeric}")
        if numeric
        else "",
    }


def summarize_data(data: dict[str, Any]) -> dict[str, Any]:
    clone = data.get("clone") if isinstance(data.get("clone"), dict) else {}
    meta = clone.get("meta") if isinstance(clone.get("meta"), dict) else {}
    equipment = data.get("equipment") if isinstance(data.get("equipment"), dict) else {}
    abilities = data.get("abilities") if isinstance(data.get("abilities"), list) else []
    skills = data.get("skills") if isinstance(data.get("skills"), list) else []
    job_id = int(data.get("job", 0) or 0)
    specialization_id = int(data.get("specialization", 0) or 0)

    return {
        "name": str(data.get("name") or ""),
        "nickname": str(data.get("nickname") or ""),
        "job_id": job_id,
        "job": JOB_NAMES.get(job_id, "未指定"),
        "level": int(data.get("level", 0) or 0),
        "job_rank": int(data.get("job_rank", 0) or 0),
        "voice_gender": int(data.get("voice_gender", 0) or 0),
        "voice_tone": int(data.get("voice_tone", 0) or 0),
        "personality": int(data.get("personality", 0) or 0),
        "specialization": {
            "id": specialization_id,
            "name": SPECIALIZATION_NAMES.get(specialization_id, f"专长 {specialization_id}"),
        },
        "skills": [
            id_name(value, SKILL_NAMES, "技能", (job_id, int(value or 0)))
            for value in skills
            if int(value or 0)
        ],
        "abilities": [
            id_name(value, ABILITY_NAMES, "强化能力")
            for value in abilities
            if int(value or 0)
        ],
        "ability_slots": [int(value or 0) for value in abilities],
        "equipment": [
            {
                **id_name(equipment.get(slot), EQUIPMENT_NAMES, "物品"),
                "slot": slot,
            }
            for slot in EQUIPMENT_ORDER
            if int(equipment.get(slot, 0) or 0)
        ],
        "appearance": {
            "gender": clone.get("gender"),
            "species": clone.get("species"),
            "body_parameters": len(clone.get("body", [])),
            "face_parameters": len(clone.get("face", [])),
            "styles": {
                key: meta.get(key)
                for key in (
                    "_HeadStyle",
                    "_HairStyle",
                    "_SkinStyle",
                    "_EyeStyle",
                    "_EyebrowStyle",
                    "_LipStyle",
                )
                if key in meta
            },
        },
    }


def current_summaries(config: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for slot in (0, 1, 2):
        data, override = effective_pawn(config, slot)
        summary = summarize_data(data)
        summary.update(
            {
                "slot": f"pawn{slot}",
                "slot_number": slot + 1,
                "enabled": bool(override.get("enabled", True)),
            }
        )
        result.append(summary)
    return result


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    data = profile.get("data", {})
    return {
        "id": profile.get("id"),
        "display_name": profile.get("display_name") or data.get("nickname") or data.get("name"),
        "notes": profile.get("notes", ""),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
        "source": profile.get("source", {}),
        **summarize_data(data),
    }


def ensure_unique_id(requested: str | None = None) -> str:
    if requested:
        profile_id = re.sub(r"[^a-z0-9_-]+", "-", requested.casefold()).strip("-")
        if not profile_id:
            raise ApiError("配置 ID 只能包含英文字母、数字、下划线和连字符")
        if profile_path(profile_id).exists():
            raise ApiError("配置 ID 已存在", HTTPStatus.CONFLICT)
        return profile_id
    for _ in range(20):
        profile_id = f"char-{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
        if not profile_path(profile_id).exists():
            return profile_id
    raise ApiError("无法生成唯一配置 ID", HTTPStatus.INTERNAL_SERVER_ERROR)


def create_profile_from_slot(body: dict[str, Any]) -> dict[str, Any]:
    source_slot = str(body.get("source_slot") or "pawn0")
    match = re.fullmatch(r"pawn([0-2])", source_slot)
    if not match:
        raise ApiError("来源随从槽位无效")
    slot = int(match.group(1))
    display_name = str(body.get("display_name") or "").strip()
    if not display_name:
        raise ApiError("请输入配置名称")

    config_path = CONFIG_PATH.resolve()
    if not config_path.is_file():
        raise ApiError(f"找不到游戏配置：{config_path}", HTTPStatus.NOT_FOUND)
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes.decode("utf-8-sig"))
    effective, _override = effective_pawn(config, slot)
    data = {
        key: copy.deepcopy(value)
        for key, value in effective.items()
        if key not in TECHNICAL_FIELDS
    }
    if isinstance(data.get("clone"), dict):
        data["clone_keep"] = copy.deepcopy(data["clone"])

    profile_id = ensure_unique_id(body.get("id"))
    created_at = now_iso()
    profile = {
        "format": PROFILE_FORMAT,
        "version": PROFILE_VERSION,
        "id": profile_id,
        "display_name": display_name,
        "notes": str(body.get("notes") or "").strip(),
        "created_at": created_at,
        "updated_at": created_at,
        "source": {
            "kind": "current-pawn",
            "slot": source_slot,
            "pawn_name": effective.get("name"),
            "config_file": str(config_path),
            "config_sha256": sha256_bytes(config_bytes),
            "config_modified_at": file_modified_at(config_path),
        },
        "data": data,
    }
    write_json_atomic(profile_path(profile_id), profile)
    return profile


def create_profile_from_import(body: dict[str, Any]) -> dict[str, Any]:
    data = body.get("data")
    if not isinstance(data, dict):
        raise ApiError("导入文件缺少 data 对象")
    display_name = str(
        body.get("display_name")
        or data.get("nickname")
        or data.get("name")
        or "导入角色"
    ).strip()
    profile_id = ensure_unique_id(body.get("id"))
    created_at = now_iso()
    imported = {
        key: copy.deepcopy(value)
        for key, value in data.items()
        if key not in TECHNICAL_FIELDS
    }
    profile = {
        "format": PROFILE_FORMAT,
        "version": PROFILE_VERSION,
        "id": profile_id,
        "display_name": display_name,
        "notes": str(body.get("notes") or "").strip(),
        "created_at": created_at,
        "updated_at": created_at,
        "source": {"kind": "json-import"},
        "data": imported,
    }
    write_json_atomic(profile_path(profile_id), profile)
    return profile


def update_profile(profile_id: str, body: dict[str, Any]) -> dict[str, Any]:
    profile = read_profile(profile_id)
    if "display_name" in body:
        display_name = str(body["display_name"] or "").strip()
        if not display_name:
            raise ApiError("配置名称不能为空")
        profile["display_name"] = display_name
    if "notes" in body:
        profile["notes"] = str(body["notes"] or "").strip()
    if "data" in body:
        if not isinstance(body["data"], dict):
            raise ApiError("data 必须是 JSON 对象")
        profile["data"] = copy.deepcopy(body["data"])
    profile["updated_at"] = now_iso()
    write_json_atomic(profile_path(profile_id), profile)
    return profile


def duplicate_profile(profile_id: str, body: dict[str, Any]) -> dict[str, Any]:
    profile = copy.deepcopy(read_profile(profile_id))
    new_id = ensure_unique_id(body.get("id"))
    created_at = now_iso()
    profile.update(
        {
            "id": new_id,
            "display_name": str(body.get("display_name") or f"{profile['display_name']} 副本"),
            "created_at": created_at,
            "updated_at": created_at,
            "source": {"kind": "duplicate", "profile_id": profile_id},
        }
    )
    write_json_atomic(profile_path(new_id), profile)
    return profile


def delete_profile(profile_id: str) -> dict[str, str]:
    path = profile_path(profile_id)
    if not path.is_file():
        raise ApiError("角色配置不存在", HTTPStatus.NOT_FOUND)
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S_%f")
    destination = TRASH_DIR / f"{stamp}_{profile_id}.json"
    os.replace(path, destination)
    return {"trashed_to": str(destination)}


def apply_profile(body: dict[str, Any]) -> dict[str, Any]:
    if game_is_running():
        raise ApiError("DD2.exe 正在运行，请先关闭游戏再应用配置", HTTPStatus.CONFLICT)
    profile_id = str(body.get("profile_id") or "")
    profile = read_profile(profile_id)
    targets = body.get("targets")
    sections = body.get("sections")
    if not isinstance(targets, list) or not targets:
        raise ApiError("请至少选择一个目标随从")
    if not isinstance(sections, list) or not sections:
        raise ApiError("请至少选择一个应用区块")
    invalid_sections = sorted(set(sections) - set(SECTION_FIELDS))
    if invalid_sections:
        raise ApiError(f"未知应用区块：{', '.join(invalid_sections)}")

    if not CONFIG_PATH.is_file():
        raise ApiError(f"找不到游戏配置：{CONFIG_PATH}", HTTPStatus.NOT_FOUND)
    original_bytes = CONFIG_PATH.read_bytes()
    config = json.loads(original_bytes.decode("utf-8-sig"))
    before = copy.deepcopy(config)
    profile_data = profile["data"]
    changed_sections: dict[str, list[str]] = {}

    for target in targets:
        match = re.fullmatch(r"pawn([0-2])", str(target))
        if not match:
            raise ApiError(f"无效的随从目标：{target}")
        target_key = f"pawn{match.group(1)}"
        target_data = config.get(target_key)
        if not isinstance(target_data, dict):
            raise ApiError(f"游戏配置缺少 {target_key}")
        fields_changed: list[str] = []
        for section in sections:
            for field in SECTION_FIELDS[section]:
                if field not in profile_data:
                    continue
                if field == "clone_keep" and "clone_keep" not in profile_data:
                    continue
                target_data[field] = copy.deepcopy(profile_data[field])
                fields_changed.append(field)
        if "appearance" in sections:
            clone = profile_data.get("clone")
            if isinstance(clone, dict):
                target_data["clone"] = copy.deepcopy(clone)
                target_data["clone_keep"] = copy.deepcopy(clone)
        abilities = target_data.get("abilities")
        if "vocation" in sections and isinstance(abilities, list) and len(abilities) >= 7:
            if int(abilities[6] or 0):
                target_data["extra_aug"] = True
        target_data["enabled"] = True
        changed_sections[target_key] = sorted(set(fields_changed + ["enabled"]))

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S_%f")
    backup_path = BACKUP_DIR / f"ThePawnController_config_before_character_manager_{stamp}.json"
    backup_path.write_bytes(original_bytes)
    if sha256_bytes(backup_path.read_bytes()) != sha256_bytes(original_bytes):
        raise ApiError("配置备份校验失败", HTTPStatus.INTERNAL_SERVER_ERROR)

    try:
        write_json_atomic(CONFIG_PATH, config)
        written = read_json(CONFIG_PATH)
        for target_key in changed_sections:
            for section in sections:
                for field in SECTION_FIELDS[section]:
                    if field in profile_data and written[target_key].get(field) != profile_data[field]:
                        raise RuntimeError(f"{target_key}.{field} 写入校验失败")
        for target_key in ("pawn0", "pawn1", "pawn2"):
            if target_key not in changed_sections and written[target_key] != before[target_key]:
                raise RuntimeError(f"未选择的 {target_key} 被意外修改")
    except Exception as error:
        CONFIG_PATH.write_bytes(original_bytes)
        raise ApiError(f"写入失败，已恢复原配置：{error}", HTTPStatus.INTERNAL_SERVER_ERROR) from error

    return {
        "applied": True,
        "profile_id": profile_id,
        "targets": sorted(changed_sections),
        "sections": sections,
        "backup": str(backup_path),
        "game_was_closed": True,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "LimeDD2CharacterManager/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stdout.write(f"[{self.log_date_time_string()}] {fmt % args}\n")
        sys.stdout.flush()

    def send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def read_body(self) -> dict[str, Any]:
        length_text = self.headers.get("Content-Length", "0")
        try:
            length = int(length_text)
        except ValueError as error:
            raise ApiError("无效的 Content-Length") from error
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ApiError("请求内容过大", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(body, dict):
            raise ApiError("请求体必须是 JSON 对象")
        return body

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                content = INDEX_PATH.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(content)
                return
            if path == "/api/state":
                config = read_json(CONFIG_PATH)
                profiles = [profile_summary(item) for item in list_profiles()]
                self.send_json(
                    {
                        "game_running": game_is_running(),
                        "config_path": str(CONFIG_PATH),
                        "config_modified_at": file_modified_at(CONFIG_PATH),
                        "current": current_summaries(config),
                        "profiles": profiles,
                    }
                )
                return
            if path.startswith("/api/current/"):
                slot_text = unquote(path.rsplit("/", 1)[-1])
                match = re.fullmatch(r"pawn([0-2])", slot_text)
                if not match:
                    raise ApiError("无效的随从槽位", HTTPStatus.NOT_FOUND)
                config = read_json(CONFIG_PATH)
                data, _override = effective_pawn(config, int(match.group(1)))
                self.send_json({"slot": slot_text, "summary": summarize_data(data), "data": data})
                return
            if path.startswith("/api/profiles/"):
                profile_id = unquote(path.rsplit("/", 1)[-1])
                profile = read_profile(profile_id)
                self.send_json({**profile, "summary": profile_summary(profile)})
                return
            raise ApiError("接口不存在", HTTPStatus.NOT_FOUND)
        except ApiError as error:
            self.send_json({"error": str(error)}, error.status)
        except FileNotFoundError as error:
            self.send_json({"error": f"文件不存在：{error.filename}"}, HTTPStatus.NOT_FOUND)
        except Exception as error:
            self.send_json(
                {"error": f"服务器错误：{error}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_POST(self) -> None:
        try:
            path = urlparse(self.path).path
            body = self.read_body()
            if path == "/api/profiles":
                profile = create_profile_from_slot(body)
            elif path == "/api/profiles/import":
                profile = create_profile_from_import(body)
            elif path == "/api/apply":
                self.send_json(apply_profile(body))
                return
            elif path.endswith("/duplicate") and path.startswith("/api/profiles/"):
                profile_id = unquote(path.split("/")[3])
                profile = duplicate_profile(profile_id, body)
            else:
                raise ApiError("接口不存在", HTTPStatus.NOT_FOUND)
            self.send_json({"profile": {**profile, "summary": profile_summary(profile)}})
        except ApiError as error:
            self.send_json({"error": str(error)}, error.status)
        except Exception as error:
            self.send_json(
                {"error": f"服务器错误：{error}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_PUT(self) -> None:
        try:
            path = urlparse(self.path).path
            if not path.startswith("/api/profiles/"):
                raise ApiError("接口不存在", HTTPStatus.NOT_FOUND)
            profile_id = unquote(path.rsplit("/", 1)[-1])
            profile = update_profile(profile_id, self.read_body())
            self.send_json({"profile": {**profile, "summary": profile_summary(profile)}})
        except ApiError as error:
            self.send_json({"error": str(error)}, error.status)
        except Exception as error:
            self.send_json(
                {"error": f"服务器错误：{error}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_DELETE(self) -> None:
        try:
            path = urlparse(self.path).path
            if not path.startswith("/api/profiles/"):
                raise ApiError("接口不存在", HTTPStatus.NOT_FOUND)
            profile_id = unquote(path.rsplit("/", 1)[-1])
            self.send_json(delete_profile(profile_id))
        except ApiError as error:
            self.send_json({"error": str(error)}, error.status)
        except Exception as error:
            self.send_json(
                {"error": f"服务器错误：{error}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="DD2 character preset manager")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8791)
    args = parser.parse_args()
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving DD2 character manager at http://{args.host}:{args.port}/")
    print(f"Config: {CONFIG_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
