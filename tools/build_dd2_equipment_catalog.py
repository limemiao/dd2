"""Build a browsable Dragon's Dogma 2 equipment catalog from game resources."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from ree_msg_dump import load_messages
from ree_user_rsz_dump import UserRsz


WEAPON_MODEL_TYPES = {
    "wp000": "剑",
    "wp001": "盾牌",
    "wp002": "大剑",
    "wp003": "匕首",
    "wp004": "弓",
    "wp005": "魔弓",
    "wp007": "法杖",
    "wp008": "大法杖",
    "wp009": "双头枪",
    "wp010": "香炉",
}

ARMOR_SLOTS = {
    0: "其他防具",
    1: "盾牌",
    2: "头部",
    3: "身体",
    4: "腿部",
    5: "披风",
    6: "戒指",
    7: "面部饰物",
}

JOB_BITS = [
    (2, "战士"),
    (4, "弓箭手"),
    (8, "法师"),
    (16, "盗贼"),
    (32, "斗士"),
    (64, "巫师"),
    (128, "魔剑士"),
    (256, "魔弓手"),
    (512, "幻术师"),
]

VOCATIONS = [
    "战士",
    "弓箭手",
    "法师",
    "盗贼",
    "斗士",
    "巫师",
    "魔剑士",
    "魔弓手",
    "幻术师",
    "龙选者",
]

WEAPON_STAT_FIELDS = [
    ("_PhysicalAttack", "物理攻击"),
    ("_MagicAttack", "魔法攻击"),
    ("_SlashRate", "斩击倍率"),
    ("_StrikeRate", "打击倍率"),
    ("_ElementStore", "属性值"),
    ("_Shake", "硬直"),
    ("_Blow", "击退"),
    ("_PoisonStore", "毒"),
    ("_SleepStore", "睡眠"),
    ("_SilentStore", "沉默"),
    ("_StoneStore", "石化"),
    ("_WaterStore", "潮湿"),
    ("_OilStore", "油污"),
]

ARMOR_STAT_FIELDS = [
    ("_PhysicalDefence", "物理防御"),
    ("_MagicDefence", "魔法防御"),
    ("_FireDefence", "火焰防御"),
    ("_IceDefence", "冰霜防御"),
    ("_ThunderDefence", "雷电防御"),
    ("_LightDefence", "光防御"),
    ("_DarkDefence", "暗防御"),
    ("_SlashDefenceRate", "斩击抗性"),
    ("_StrikeDefenceRate", "打击抗性"),
    ("_FireResist", "火耐性"),
    ("_IceResist", "冰耐性"),
    ("_ThunderResist", "雷耐性"),
    ("_PoisonResist", "毒耐性"),
    ("_SleepResist", "睡眠耐性"),
    ("_SilentResist", "沉默耐性"),
    ("_StoneResist", "石化耐性"),
    ("_WaterResist", "潮湿耐性"),
    ("_OilResist", "油污耐性"),
    ("_FaintResist", "昏厥耐性"),
    ("_ColdResist", "寒冷耐性"),
]


def safe_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    return value.strip(" .")[:80] or "unnamed"


def resolve_message_references(text: str, messages: dict[str, str], depth: int = 0) -> str:
    """Expand MSG <REF key> links and remove presentation-only tags."""
    if not text or depth > 8:
        return text

    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip().lower()
        replacement = messages.get(key, "")
        return resolve_message_references(replacement, messages, depth + 1)

    resolved = re.sub(r"<REF\s+([^>]+)>", replace, text, flags=re.IGNORECASE)
    resolved = re.sub(r"</?COLOR(?:\s+[^>]*)?>", "", resolved, flags=re.IGNORECASE)
    resolved = re.sub(r"<EQABI(?:\s+[^>]*)?>", "", resolved, flags=re.IGNORECASE)
    return resolved.strip()


def parse_params(path: Path, classes_path: Path) -> tuple[str, list[dict[str, Any]]]:
    source = UserRsz(path, classes_path)
    source.parse()
    root = source.instances[source.object_table[0]]
    refs = root["_values"]["_Params"]
    return root["_class"], [
        dict(source.instances[index]["_values"]) for index in refs
    ]


def simple_stat_rows(row: dict[str, Any], fields: list[tuple[str, str]]) -> list[str]:
    values: list[str] = []
    for key, label in fields:
        value = int(row.get(key, 0) or 0)
        if value:
            values.append(f"{label} {value}")
    if row.get("_Element"):
        values.append(f"元素代码 {row['_Element']}")
    special = int(row.get("_Special", 0) or 0)
    if special:
        values.append(f"特殊效果代码 {special}")
    for key, label in [
        ("_SpecialValue", "效果值1"),
        ("_SpecialValue2", "效果值2"),
        ("_SpecialValue3", "效果值3"),
    ]:
        value = int(row.get(key, 0) or 0)
        if value:
            values.append(f"{label} {value}")
    return values


def placeholder_icon(path: Path, label: str) -> None:
    image = Image.new("RGBA", (234, 234), (232, 228, 218, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((14, 14, 220, 220), radius=16, outline=(132, 119, 94, 255), width=3)
    font = ImageFont.load_default(size=18)
    box = draw.textbbox((0, 0), label, font=font)
    draw.text(
        ((234 - (box[2] - box[0])) / 2, (234 - (box[3] - box[1])) / 2),
        label,
        fill=(92, 82, 66, 255),
        font=font,
    )
    image.save(path)


def jobs_for_mask(mask: int) -> list[str]:
    if mask in (0, 1022):
        return ["全职业", "龙选者"]
    jobs = [name for bit, name in JOB_BITS if mask & bit]
    # Warfarer can equip gear from every vocation by design; its combinations
    # are not represented as a separate bit in the item data.
    if "龙选者" not in jobs:
        jobs.append("龙选者")
    return jobs


def weapon_type_for_row(row: dict[str, Any], name: str) -> str:
    """Identify weapon type from its model, with conservative fallbacks."""
    model = str(row.get("_WeaponName", "") or "").strip().lower()
    prefix = model.split("_", 1)[0]
    if prefix == "wp00":
        return "剑"
    if prefix in WEAPON_MODEL_TYPES:
        return WEAPON_MODEL_TYPES[prefix]

    # A few expansion records omit the weapon model. Their display name or
    # exclusive job mask is still sufficient to place them correctly.
    if name.endswith("盾"):
        return "盾牌"
    if name.endswith("弓") and int(row.get("_Job", 0) or 0) == 4:
        return "弓"
    if name.endswith("杖") and int(row.get("_Job", 0) or 0) == 64:
        return "大法杖"

    fallback = {
        2: "剑",
        4: "弓",
        8: "法杖",
        16: "匕首",
        32: "大剑",
        64: "大法杖",
        128: "双头枪",
        256: "魔弓",
        512: "香炉",
    }
    return fallback.get(int(row.get("_Job", 0) or 0), "其他武器")


def atlas_series_for_icon(icon_no: int) -> int:
    """Return the c00 atlas sequence used by the game for an item icon ID."""
    series = icon_no // 1000
    # The 12xxx-14xxx item icon IDs are offset by one from their atlas file
    # sequence. For example, icon 13084 is stored in atlas 12 at pattern 84,
    # while 12040 is the axe in atlas 11 at pattern 40.
    return series - 1 if 12 <= series <= 14 else series


def crop_icon(
    icon_no: int,
    atlas_dir: Path,
    output_path: Path,
    placeholder: Path,
    force: bool = False,
) -> str:
    pattern = icon_no % 1000
    atlas_series = atlas_series_for_icon(icon_no)
    atlas = atlas_dir / f"tex_ui01c00_{atlas_series:02d}_iam.png"
    # Icon 0 is an unset sentinel, not the first cell of atlas 0. Several
    # expansion records use it for duplicate variants and inherit the icon
    # from another variant with the same name.
    if icon_no <= 0 or not atlas.exists() or pattern >= 100:
        if not output_path.exists():
            placeholder_icon(output_path, "图集无图标")
        return "missing"
    if output_path.exists() and not force:
        return "in_game"
    with Image.open(atlas) as source:
        size = source.width // 10
        x = pattern % 10 * size
        y = pattern // 10 * size
        source.crop((x, y, x + size, y + size)).save(output_path)
    return "in_game"


def build(args: argparse.Namespace) -> None:
    extracted = args.extracted.resolve()
    itemdata_dir = extracted / "natives/stm/appsystem/item/itemdata"
    message_dir = extracted / "natives/stm/message/ui"
    output = args.output.resolve()
    icons_dir = output / "icons"
    output.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)

    names: dict[str, str] = {}
    details: dict[str, str] = {}
    for filename in ("itemname.msg.24", "itemname_end.msg.24"):
        table = load_messages(message_dir / filename)
        for key, languages in table.items():
            names[key.lower()] = languages.get("SimplifiedChinese") or languages.get("English", "")
    for filename in ("itemdetail.msg.24", "itemdetail_end.msg.24"):
        table = load_messages(message_dir / filename)
        for key, languages in table.items():
            details[key.lower()] = languages.get("SimplifiedChinese") or languages.get("English", "")
    appraisal_names: dict[str, str] = {}
    appraisal_details: dict[str, str] = {}
    for target, filename in (
        (appraisal_names, "appraisalitemname_tu_end.msg.24"),
        (appraisal_details, "appraisalitemdetail_tu_end.msg.24"),
    ):
        path = message_dir / filename
        if not path.exists():
            continue
        table = load_messages(path)
        for key, languages in table.items():
            target[key.lower()] = (
                languages.get("SimplifiedChinese") or languages.get("English", "")
            )

    sources: list[tuple[str, str, Path]] = [
        ("weapon", "itemweapondata.user.3", itemdata_dir / "itemweapondata.user.3"),
        ("weapon", "exitemweapondata.user.3", itemdata_dir / "exitemweapondata.user.3"),
        ("armor", "itemarmordata.user.3", itemdata_dir / "itemarmordata.user.3"),
        ("armor", "exitemarmordata.user.3", itemdata_dir / "exitemarmordata.user.3"),
    ]
    records: dict[int, dict[str, Any]] = {}
    for kind, source_name, path in sources:
        _root_class, rows = parse_params(path, args.classes)
        for row in rows:
            item_id = int(row["_Id"])
            record = records.setdefault(item_id, {})
            record.update(row)
            record["_catalog_kind"] = kind
            record["_source"] = source_name

    catalog: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    for item_id, row in sorted(records.items()):
        name = resolve_message_references(
            names.get(f"item_name_{item_id}", ""), appraisal_names
        )
        if not name or "#rejected#" in name.lower():
            skipped["无有效名称/废弃条目"] += 1
            continue
        kind = row["_catalog_kind"]
        if kind == "weapon":
            category = f"武器 · {weapon_type_for_row(row, name)}"
        else:
            category = f"防具 · {ARMOR_SLOTS.get(int(row.get('_EquipCategory', 0) or 0), '其他防具')}"

        source_icon_no = int(row.get("_IconNo", 0) or 0)
        icon_no = source_icon_no
        icon_fallback_from: int | None = None
        if icon_no <= 0:
            # Some duplicate item variants have no icon number of their own.
            # Reuse the icon of a same-named item in the same catalog group
            # instead of treating 0 as atlas 0, cell 0 (a food icon).
            for candidate_id, candidate_row in sorted(records.items()):
                if candidate_id == item_id:
                    continue
                candidate_name = resolve_message_references(
                    names.get(f"item_name_{candidate_id}", ""), appraisal_names
                )
                if (
                    candidate_name != name
                    or candidate_row["_catalog_kind"] != kind
                    or int(
                        candidate_row.get("_EquipCategory", -1) or -1
                    )
                    != int(row.get("_EquipCategory", -1) or -1)
                ):
                    continue
                candidate_icon_no = int(candidate_row.get("_IconNo", 0) or 0)
                if candidate_icon_no > 0:
                    icon_no = candidate_icon_no
                    icon_fallback_from = candidate_id
                    break
        filename = f"{item_id:05d}_{safe_filename(name)}.png"
        icon_path = icons_dir / filename
        availability = crop_icon(
            icon_no,
            extracted / "gui_item_png",
            icon_path,
            icons_dir / "_no_icon.png",
            args.force_icons,
        )
        stat_fields = WEAPON_STAT_FIELDS if kind == "weapon" else ARMOR_STAT_FIELDS
        stats = simple_stat_rows(row, stat_fields)
        description = resolve_message_references(
            details.get(f"item_detail_{item_id}", ""), appraisal_details
        )
        if "#rejected#" in description.lower():
            description = ""
        record = {
            "id": item_id,
            "name": name,
            "kind": kind,
            "category": category,
            "icon_no": icon_no,
            "source_icon_no": source_icon_no,
            "icon_fallback_from": icon_fallback_from,
            "icon": f"icons/{filename}",
            "icon_availability": availability,
            "weight": int(row.get("_Weight", 0) or 0),
            "buy_price": int(row.get("_BuyPrice", 0) or 0),
            "sell_price": int(row.get("_SellPrice", 0) or 0),
            "level": int(row.get("_Lv", 0) or 0),
            "model_id": int(row.get("_ModelId", 0) or 0),
            "field_model_id": int(row.get("_FieldModelId", 0) or 0),
            "weapon_model": row.get("_WeaponName", ""),
            "job_mask": int(row.get("_Job", 0) or 0),
            "jobs": jobs_for_mask(int(row.get("_Job", 0) or 0)),
            "stats": stats,
            "stats_raw": row,
            "description": description.replace("\r", "\n").strip(),
            "source": row["_source"],
        }
        catalog.append(record)

    (output / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (output / "catalog.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["ID", "名称", "分类", "可装备职业", "职业掩码", "重量", "购买价", "出售价", "等级", "图标编号", "图标来源", "数值", "说明"]
        )
        for item in catalog:
            writer.writerow(
                [
                    item["id"],
                    item["name"],
                    item["category"],
                    "、".join(item["jobs"]),
                    item["job_mask"],
                    item["weight"],
                    item["buy_price"],
                    item["sell_price"],
                    item["level"],
                    item["icon_no"],
                    "游戏图集" if item["icon_availability"] == "in_game" else "缺失",
                    "；".join(item["stats"]),
                    item["description"],
                ]
            )

    categories = sorted({item["category"] for item in catalog})
    cards: list[str] = []
    for item in catalog:
        card_class = "missing" if item["icon_availability"] != "in_game" else ""
        stats_html = "".join(f"<span>{html.escape(value)}</span>" for value in item["stats"])
        description = html.escape(item["description"])
        searchable = " ".join(
            [item["name"], str(item["id"]), item["category"], *item["jobs"]]
        ).lower()
        cards.append(
            f"""
            <article class="card {card_class}" data-category="{html.escape(item['category'])}"
                     data-kind="{html.escape(item['kind'])}"
                     data-jobs="{html.escape('|'.join(item['jobs']))}"
                     data-search="{html.escape(searchable)}">
              <div class="icon"><img loading="lazy" src="{html.escape(item['icon'])}" alt="{html.escape(item['name'])}"></div>
              <div class="body">
                <small>#{item['id']} · {html.escape(item['category'])}</small>
                <h3>{html.escape(item['name'])}</h3>
                <div class="meta jobs">可装备：{html.escape('、'.join(item['jobs']))}</div>
                <div class="meta">重量 {item['weight']} · 买价 {item['buy_price']} · 卖价 {item['sell_price']}</div>
                <div class="stats">{stats_html or '<span>无额外数值</span>'}</div>
                <p>{description}</p>
              </div>
            </article>"""
        )

    category_buttons = "".join(
        f'<button data-category="{html.escape(category)}">{html.escape(category)}</button>'
        for category in categories
    )
    kind_buttons = (
        '<button class="active" data-kind="">全部装备</button>'
        '<button data-kind="weapon">武器</button>'
        '<button data-kind="armor">防具</button>'
    )
    job_buttons = '<button class="active" data-job="">全部职业</button>' + "".join(
        f'<button data-job="{html.escape(job)}">{html.escape(job)}</button>'
        for job in VOCATIONS
    )
    in_game = sum(item["icon_availability"] == "in_game" for item in catalog)
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>龙之信条 2 装备图鉴</title>
<style>
:root{{color-scheme:dark;--bg:#11100e;--panel:#1b1915;--line:#4b4235;--gold:#d8bd7c;--muted:#b5aa96}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at top,#292319,var(--bg) 46%);color:#eee8dd;font:15px/1.55 "Microsoft YaHei",sans-serif}}
header{{padding:34px max(20px,6vw) 22px;border-bottom:1px solid var(--line)}}h1{{margin:0;color:var(--gold);font-size:40px}}header p{{color:var(--muted);margin:8px 0 0}}
.controls{{position:sticky;top:0;z-index:3;padding:14px max(20px,6vw);background:#11100fee;backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}}
.controls-top{{display:flex;align-items:center;gap:16px;flex-wrap:wrap}}#search{{width:min(560px,100%);padding:11px 14px;background:#211e18;border:1px solid var(--line);color:white;border-radius:8px;font-size:16px}}#result-count{{color:var(--muted);font-size:13px;margin-left:auto}}
.filter-row{{display:flex;align-items:flex-start;gap:10px;margin-top:10px}}.filter-label{{color:#d8bd7c;font-size:12px;font-weight:700;min-width:62px;padding-top:7px}}
.filter-scroll{{display:flex;gap:7px;overflow:auto;padding-bottom:2px}}button{{white-space:nowrap;color:#ddd3c0;background:#262219;border:1px solid var(--line);border-radius:999px;padding:6px 12px;cursor:pointer}}button.active{{background:var(--gold);color:#17140e}}button:disabled{{opacity:.35;cursor:default}}
main{{padding:24px max(20px,6vw) 60px}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(235px,1fr));gap:16px}}
.card{{display:flex;flex-direction:column;background:linear-gradient(160deg,#211e18,#171511);border:1px solid var(--line);border-radius:12px;overflow:hidden;min-height:390px;box-shadow:0 8px 28px #0005}}
.icon{{height:234px;background:linear-gradient(135deg,#e8e4dc,#c9c2b4);display:grid;place-items:center}}.icon img{{width:234px;height:234px;object-fit:contain}}
.body{{padding:13px 15px 15px}}h3{{margin:3px 0 7px;color:#f2dfb1;font-size:19px}}small,.meta{{color:var(--muted)}}.meta{{font-size:12px}}
.meta.jobs{{color:#e1ca8d;margin-bottom:3px}}
.stats{{display:flex;flex-wrap:wrap;gap:5px;margin:10px 0}}.stats span{{font-size:12px;background:#2d281e;border:1px solid #4b402f;border-radius:5px;padding:2px 6px}}
p{{font-size:12px;color:#aaa090;margin:8px 0 0;max-height:4.8em;overflow:auto}}.card.missing{{opacity:.72}}
.empty{{padding:32px;text-align:center;color:var(--muted);border:1px dashed var(--line);border-radius:12px;margin-bottom:18px}}
.hidden{{display:none}}@media(max-width:600px){{h1{{font-size:30px}}.grid{{grid-template-columns:repeat(auto-fill,minmax(180px,1fr))}}.icon,.icon img{{height:190px;width:190px}}.card{{min-height:340px}}}}
</style>
</head>
<body>
<header><h1>龙之信条 2 · 装备图鉴</h1><p>共 {len(catalog)} 件装备，{in_game} 件直接从游戏图集裁剪；名称、重量、攻防与抗性来自 PAK 内数据。</p></header>
<div class="controls">
  <div class="controls-top"><input id="search" placeholder="搜索名称、物品 ID 或职业…"><div id="result-count"></div></div>
  <div class="filter-row"><span class="filter-label">装备类型</span><div class="filter-scroll" id="kind-filters">{kind_buttons}</div></div>
  <div class="filter-row"><span class="filter-label">职业</span><div class="filter-scroll" id="job-filters">{job_buttons}</div></div>
  <div class="filter-row"><span class="filter-label">类型 / 部位</span><div class="filter-scroll" id="category-filters"><button class="active" data-category="">全部部位</button>{category_buttons}</div></div>
</div>
<main><div id="empty" class="empty hidden">当前职业与筛选条件下没有可装备物品。</div><div class="grid">{''.join(cards)}</div></main>
<script>
const state={{kind:'',job:'',category:''}};
const cards=[...document.querySelectorAll('.card')];
const categoryButtons=[...document.querySelectorAll('#category-filters button')];
const search=document.querySelector('#search');
function matchesBase(card){{
  const jobs=(card.dataset.jobs||'').split('|');
  const jobMatch=!state.job||jobs.includes(state.job)||jobs.includes('全职业');
  const kindMatch=!state.kind||card.dataset.kind===state.kind;
  return jobMatch&&kindMatch;
}}
function refreshCategories(){{
  let selectedIsValid=state.category==='';
  for(const button of categoryButtons){{
    const category=button.dataset.category;
    const count=cards.filter(card=>matchesBase(card)&&(!category||card.dataset.category===category)).length;
    button.textContent=`${{category||'全部部位'}} (${{count}})`;
    button.disabled=count===0;
    if(category===state.category){{
      selectedIsValid=count>0;
    }}
  }}
  if(!selectedIsValid)state.category='';
  for(const button of categoryButtons)button.classList.toggle('active',button.dataset.category===state.category);
}}
function apply(){{
  refreshCategories();
  const q=search.value.trim().toLowerCase();
  let visible=0;
  for(const card of cards){{
    const show=matchesBase(card)&&(!state.category||card.dataset.category===state.category)&&(!q||card.dataset.search.includes(q));
    card.classList.toggle('hidden',!show);
    if(show)visible++;
  }}
  document.querySelector('#result-count').textContent=`显示 ${{visible}} / ${{cards.length}} 件`;
  document.querySelector('#empty').classList.toggle('hidden',visible!==0);
}}
document.querySelector('#search').addEventListener('input',apply);
for(const button of document.querySelectorAll('#kind-filters button'))button.addEventListener('click',()=>{{
  state.kind=button.dataset.kind;state.category='';
  document.querySelectorAll('#kind-filters button').forEach(x=>x.classList.toggle('active',x===button));
  apply();
}});
for(const button of document.querySelectorAll('#job-filters button'))button.addEventListener('click',()=>{{
  state.job=button.dataset.job;state.category='';
  document.querySelectorAll('#job-filters button').forEach(x=>x.classList.toggle('active',x===button));
  apply();
}});
for(const button of categoryButtons)button.addEventListener('click',()=>{{
  if(button.disabled)return;
  state.category=button.dataset.category;
  categoryButtons.forEach(x=>x.classList.toggle('active',x===button));
  apply();
}});
apply();
</script>
</body></html>"""
    (output / "index.html").write_text(document, encoding="utf-8")
    summary = {
        "equipment_records": len(catalog),
        "in_game_icons": in_game,
        "missing_icons": len(catalog) - in_game,
        "skipped_records": dict(skipped),
        "categories": {
            category: sum(item["category"] == category for item in catalog)
            for category in categories
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--extracted",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "extracted_dd2",
    )
    parser.add_argument(
        "--classes",
        type=Path,
        default=Path(__file__).resolve().parent / "rszdd2.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "catalogs" / "dd2_equipment_catalog",
    )
    parser.add_argument(
        "--force-icons",
        action="store_true",
        help="Regenerate every equipment icon, including files already present.",
    )
    build(parser.parse_args())


if __name__ == "__main__":
    main()
