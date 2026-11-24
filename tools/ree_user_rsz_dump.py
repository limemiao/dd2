"""Parse DD2 .user RSZ files using REasy's exported Rsz JSON definitions."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any


PRIMITIVES = {
    "Bool": ("<?", 1),
    "U8": ("<B", 1),
    "S8": ("<b", 1),
    "U16": ("<H", 2),
    "S16": ("<h", 2),
    "U32": ("<I", 4),
    "S32": ("<i", 4),
    "U64": ("<Q", 8),
    "S64": ("<q", 8),
    "F32": ("<f", 4),
    "F64": ("<d", 8),
}


def align(position: int, value: int) -> int:
    return (position + value - 1) & ~(value - 1)


class UserRsz:
    def __init__(self, path: Path, classes_path: Path):
        self.path = path
        self.data = path.read_bytes()
        self.classes = json.loads(classes_path.read_text(encoding="utf-8"))
        self.position = 0
        self.instances: list[dict[str, Any] | None] = []
        self.instance_types: list[int] = []
        self.object_table: list[int] = []
        self.userdata: dict[int, str] = {}

    def unpack(self, fmt: str) -> Any:
        size = struct.calcsize(fmt)
        value = struct.unpack_from(fmt, self.data, self.position)[0]
        self.position += size
        return value

    def read_string(self) -> str:
        count = self.unpack("<i")
        start = self.position
        end = start + max(0, count) * 2
        value = self.data[start:end].decode("utf-16le", errors="replace").rstrip("\0")
        self.position = end
        return value

    def read_field(self, field: dict[str, Any]) -> Any:
        field_type = field["type"]
        is_array = bool(field.get("array"))
        self.position = align(self.position, 4 if is_array else field.get("align", 1))
        if is_array:
            count = self.unpack("<i")
            if count < 0 or count > 1_000_000:
                raise ValueError(f"Invalid array size {count} for {field['name']}")
            if count:
                self.position = align(self.position, field.get("align", 1))
            return [self.read_value(field) for _ in range(count)]
        return self.read_value(field)

    def read_value(self, field: dict[str, Any]) -> Any:
        field_type = field["type"]
        if field_type in PRIMITIVES:
            return self.unpack(PRIMITIVES[field_type][0])
        if field_type in ("String", "Resource"):
            return self.read_string()
        if field_type == "RuntimeType":
            size = self.unpack("<I")
            start = self.position
            value = self.data[start : start + size].decode("utf-8", errors="replace")
            self.position += size
            return value
        if field_type == "Object":
            return self.unpack("<i")
        if field_type == "Guid":
            start = self.position
            self.position += 16
            return self.data[start : self.position].hex()
        if field_type == "Struct":
            target = self.classes.get(field["original_type"])
            if target is None:
                raise ValueError(f"Unknown struct {field['original_type']}")
            return {
                item["name"]: self.read_field(item)
                for item in target.get("fields", [])
            }
        if field_type == "Data":
            size = field.get("size", 0)
            value = self.data[self.position : self.position + size].hex()
            self.position += size
            return value
        raise NotImplementedError(f"Unsupported RSZ field type {field_type}")

    def parse(self) -> None:
        if self.data[:4] != b"USR\0":
            raise ValueError("Not an RE Engine user file")
        rsz_start = struct.unpack_from("<q", self.data, 32)[0]
        self.position = rsz_start
        if self.data[self.position : self.position + 4] != b"RSZ\0":
            raise ValueError("RSZ block not found")
        self.position += 4
        version = self.unpack("<I")
        object_count = self.unpack("<i")
        instance_count = self.unpack("<i")
        userdata_count = self.unpack("<q")
        instance_offset = self.unpack("<q")
        data_offset = self.unpack("<q")
        userdata_offset = self.unpack("<q")

        self.position = rsz_start + instance_offset - object_count * 4
        self.object_table = [self.unpack("<i") for _ in range(object_count)]

        self.position = rsz_start + instance_offset
        infos: list[tuple[int, int]] = []
        for _ in range(instance_count):
            infos.append(struct.unpack_from("<II", self.data, self.position))
            self.position += 8

        if userdata_count:
            self.position = rsz_start + userdata_offset
            for _ in range(userdata_count):
                instance_id = self.unpack("<i")
                _type_id = self.unpack("<I")
                _path_hash = self.unpack("<I")
                _size = self.unpack("<I")
                _rsz_offset = self.unpack("<q")
                self.userdata[instance_id] = "<external>"

        self.position = rsz_start + data_offset
        self.instance_types = [item[0] for item in infos]
        for index, (type_id, _crc) in enumerate(infos):
            if type_id == 0 or index in self.userdata:
                self.instances.append(None)
                continue
            cls = self.classes.get(f"{type_id:x}")
            if cls is None:
                raise ValueError(f"Unknown RSZ class 0x{type_id:X} at instance {index}")
            values = {
                field["name"]: self.read_field(field)
                for field in cls.get("fields", [])
            }
            self.instances.append(
                {
                    "_class": cls["name"],
                    "_index": index,
                    "_values": values,
                }
            )

        print(
            f"version={version} objects={object_count} instances={instance_count} "
            f"userdata={userdata_count} roots={self.object_table}"
        )

    def resolve(self, value: Any, depth: int = 0) -> Any:
        if depth > 8:
            return "<max-depth>"
        if isinstance(value, int):
            if 0 <= value < len(self.instances) and self.instances[value] is not None:
                instance = self.instances[value]
                return {
                    "_class": instance["_class"],
                    "_index": value,
                    "fields": {
                        key: self.resolve(item, depth + 1)
                        for key, item in instance["_values"].items()
                    },
                }
            return value
        if isinstance(value, list):
            return [self.resolve(item, depth + 1) for item in value]
        if isinstance(value, dict) and "_values" in value:
            return {
                "_class": value["_class"],
                "_index": value["_index"],
                "fields": {
                    key: self.resolve(item, depth + 1)
                    for key, item in value["_values"].items()
                },
            }
        return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--classes",
        type=Path,
        default=Path(__file__).resolve().parent / "rszdd2.json",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    source = UserRsz(args.input, args.classes)
    source.parse()
    roots = [source.resolve(source.instances[index]) for index in source.object_table]
    if args.json_out:
        args.json_out.write_text(
            json.dumps(roots, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Wrote {args.json_out}")
    else:
        print(json.dumps(roots[: args.limit], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
