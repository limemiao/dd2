"""Read modern RE Engine MSG string tables used by DD2."""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path


MSG_MAGIC = 0x47534D47
HEADER_SIZE = 72
LANGUAGE_NAMES = [
    "Japanese", "English", "French", "Italian", "German", "Spanish",
    "Russian", "Polish", "Dutch", "Portuguese", "PortugueseBr", "Korean",
    "TraditionalChinese", "SimplifiedChinese", "Finnish", "Swedish",
    "Danish", "Norwegian", "Czech", "Hungarian", "Slovak", "Arabic",
    "Turkish", "Bulgarian", "Greek", "Romanian", "Thai", "Ukrainian",
    "Vietnamese", "Indonesian", "Fiction", "Hindi", "LatinAmericanSpanish",
]
KEY = bytes([207, 206, 251, 248, 236, 10, 51, 102, 147, 169, 29, 147, 80, 57, 95, 9])


def decrypt(data: bytearray) -> None:
    previous = 0
    for index, value in enumerate(data):
        data[index] = previous ^ value ^ KEY[index & 15]
        previous = value


def read_wstring(data: bytes | bytearray, offset: int) -> str:
    end = offset
    while end + 1 < len(data) and data[end : end + 2] != b"\0\0":
        end += 2
    return bytes(data[offset:end]).decode("utf-16le", errors="replace")


def load_messages(path: Path) -> dict[str, dict[str, str]]:
    raw = path.read_bytes()
    if len(raw) < HEADER_SIZE:
        raise ValueError(f"MSG file is truncated: {path}")
    version, magic, _header_offset, entry_count, attribute_count, lang_count, _pad = (
        struct.unpack_from("<iIqiiii", raw, 0)
    )
    data_offset, _unknown, lang_offset, attribute_offset, attribute_name_offset = (
        struct.unpack_from("<5q", raw, 32)
    )
    if magic != MSG_MAGIC:
        raise ValueError(f"Not an RE Engine MSG file: {path}")

    data = bytearray(raw)
    if version > 12:
        decrypt(memoryview(data)[data_offset:])

    languages = list(
        struct.unpack_from(f"<{lang_count}i", data, lang_offset)
    ) if lang_count else []
    attribute_types = list(
        struct.unpack_from(f"<{attribute_count}i", data, attribute_offset)
    ) if attribute_count else []
    attributes: list[tuple[str, int]] = []
    for index in range(attribute_count):
        name_offset = struct.unpack_from("<q", data, attribute_name_offset + index * 8)[0]
        attributes.append((read_wstring(data, name_offset), attribute_types[index]))

    entry_offsets = struct.unpack_from(f"<{entry_count}q", data, HEADER_SIZE)
    result: dict[str, dict[str, str]] = {}
    for entry_offset in entry_offsets:
        # GUID (16), sound id (4), hash/index (4), name offset (8),
        # attribute offset (8), then one absolute string offset per language.
        name_offset = struct.unpack_from("<q", data, entry_offset + 24)[0]
        entry_name = read_wstring(data, name_offset)
        language_offsets = struct.unpack_from(
            f"<{lang_count}q", data, entry_offset + 40
        )
        values: dict[str, str] = {}
        for index, string_offset in enumerate(language_offsets):
            language_id = languages[index] if index < len(languages) else index
            language_name = (
                LANGUAGE_NAMES[language_id]
                if 0 <= language_id < len(LANGUAGE_NAMES)
                else f"Language{language_id}"
            )
            values[language_name] = read_wstring(data, string_offset)
        result[entry_name] = values
    return result


def load_messages_by_guid(path: Path) -> dict[str, dict[str, str]]:
    """Load a MSG table keyed by the raw GUID stored in skill data files."""
    raw = path.read_bytes()
    if len(raw) < HEADER_SIZE:
        raise ValueError(f"MSG file is truncated: {path}")
    version, magic, _header_offset, entry_count, _attribute_count, lang_count, _pad = (
        struct.unpack_from("<iIqiiii", raw, 0)
    )
    data_offset, _unknown, lang_offset, _attribute_offset, _attribute_name_offset = (
        struct.unpack_from("<5q", raw, 32)
    )
    if magic != MSG_MAGIC:
        raise ValueError(f"Not an RE Engine MSG file: {path}")

    data = bytearray(raw)
    if version > 12:
        decrypt(memoryview(data)[data_offset:])
    languages = (
        list(struct.unpack_from(f"<{lang_count}i", data, lang_offset))
        if lang_count
        else []
    )
    entry_offsets = struct.unpack_from(f"<{entry_count}q", data, HEADER_SIZE)
    result: dict[str, dict[str, str]] = {}
    for entry_offset in entry_offsets:
        guid = bytes(data[entry_offset : entry_offset + 16]).hex()
        language_offsets = struct.unpack_from(
            f"<{lang_count}q", data, entry_offset + 40
        )
        values: dict[str, str] = {}
        for index, string_offset in enumerate(language_offsets):
            language_id = languages[index] if index < len(languages) else index
            language_name = (
                LANGUAGE_NAMES[language_id]
                if 0 <= language_id < len(LANGUAGE_NAMES)
                else f"Language{language_id}"
            )
            values[language_name] = read_wstring(data, string_offset)
        result[guid] = values
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--language", default="English")
    parser.add_argument("--filter", default="")
    parser.add_argument("--key-regex")
    parser.add_argument("--id-min", type=int)
    parser.add_argument("--id-max", type=int)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    messages = load_messages(args.input)
    print(f"entries={len(messages)}")
    shown = 0
    needle = args.filter.lower()
    for key, values in messages.items():
        if args.key_regex and not re.search(args.key_regex, key, re.IGNORECASE):
            continue
        id_match = re.search(r"(\d+)$", key)
        if args.id_min is not None or args.id_max is not None:
            if not id_match:
                continue
            item_id = int(id_match.group(1))
            if args.id_min is not None and item_id < args.id_min:
                continue
            if args.id_max is not None and item_id > args.id_max:
                continue
        if needle and needle not in key.lower() and needle not in values.get(args.language, "").lower():
            continue
        print(f"{key}\t{values.get(args.language, '')}")
        shown += 1
        if shown >= args.limit:
            break


if __name__ == "__main__":
    main()
