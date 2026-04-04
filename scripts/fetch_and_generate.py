import glob
import json
import os
import re
import unicodedata
from urllib.parse import parse_qs, urlparse

import gspread
from gspread.utils import rowcol_to_a1
from oauth2client.service_account import ServiceAccountCredentials


SHEET_NAME = "モデル一覧"
MODEL_PAGE_URL_HEADER = "個別ページURL"
SITE_CONFIG_PATH = "_config.yml"

MEDIA_URL_KEYS = ["url", "src", "path", "image", "source"]
VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".m4v", ".ogv")


def first_value(record, keys, default=""):
    for key in keys:
        if key in record and record[key] is not None:
            value = str(record[key]).strip()
            if value != "":
                return value
    return default


def clean_yaml_value(value):
    v = str(value).split("#", 1)[0].strip()
    if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
        return v[1:-1]
    return v


def load_site_url_config(path=SITE_CONFIG_PATH):
    site_url = ""
    baseurl = ""

    if not os.path.exists(path):
        return site_url, baseurl

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not site_url:
                match = re.match(r"^\s*url:\s*(.+?)\s*$", line)
                if match:
                    site_url = clean_yaml_value(match.group(1))
                    continue
            if not baseurl:
                match = re.match(r"^\s*baseurl:\s*(.+?)\s*$", line)
                if match:
                    baseurl = clean_yaml_value(match.group(1))
                    continue

    return site_url, baseurl


def build_model_page_url(model_id, site_url, baseurl):
    normalized_baseurl = str(baseurl).strip()
    if normalized_baseurl in ("", "/"):
        normalized_baseurl = ""
    else:
        normalized_baseurl = "/" + normalized_baseurl.strip("/")

    path = f"{normalized_baseurl}/models/{model_id}/"
    site_root = str(site_url).strip().rstrip("/")
    if site_root:
        return f"{site_root}{path}"
    return path


def ensure_sheet_column(sheet, header_name):
    headers = sheet.row_values(1)
    for idx, header in enumerate(headers, start=1):
        if str(header).strip() == header_name:
            return idx

    col = len(headers) + 1 if headers else 1
    sheet.update_cell(1, col, header_name)
    return col


def update_model_page_urls(sheet, row_url_pairs):
    if not row_url_pairs:
        return

    url_col = ensure_sheet_column(sheet, MODEL_PAGE_URL_HEADER)
    updates = [
        {
            "range": rowcol_to_a1(row, url_col),
            "values": [[url]],
        }
        for row, url in row_url_pairs
    ]
    sheet.batch_update(updates, value_input_option="RAW")
    print(f"Updated {len(row_url_pairs)} URLs in sheet column '{MODEL_PAGE_URL_HEADER}'.")


def parse_int(value, default=0):
    if value is None:
        return default
    text = str(value).strip()
    if text == "":
        return default
    match = re.search(r"\d+", text)
    if not match:
        return default
    return int(match.group(0))


def normalize_media_value(value):
    if isinstance(value, dict):
        normalized = {}
        for key, val in value.items():
            if val is None:
                continue
            text = str(val).strip()
            if text == "":
                continue
            normalized[str(key).strip().lower()] = text
        return normalized or None

    text = str(value).strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return normalize_media_value(parsed)
        except json.JSONDecodeError:
            pass

    prefixed_match = re.match(r"^(image|video)\s*:\s*(.+)$", text, re.IGNORECASE)
    if prefixed_match:
        return {
            "type": prefixed_match.group(1).lower(),
            "url": prefixed_match.group(2).strip(),
        }

    if "|" in text and "=" in text:
        maybe_dict = {}
        valid = True
        for part in text.split("|"):
            segment = part.strip()
            if segment == "":
                continue
            if "=" not in segment:
                valid = False
                break
            key, val = segment.split("=", 1)
            key = key.strip().lower()
            val = val.strip()
            if key == "" or val == "":
                valid = False
                break
            maybe_dict[key] = val
        if valid and maybe_dict:
            return normalize_media_value(maybe_dict)

    return text if text else None


def infer_media_type_from_url(url):
    normalized = str(url).split("?", 1)[0].split("#", 1)[0].lower()
    for ext in VIDEO_EXTENSIONS:
        if normalized.endswith(ext):
            return "video"
    return None

def parse_list(value):
    if value is None:
        return []

    def normalize_items(items):
        return [item for item in (normalize_media_value(v) for v in items) if item]

    if isinstance(value, list):
        return normalize_items(value)
    text = str(value).strip()
    if text == "":
        return []

    # JSON配列文字列（例: ["a", "b"]）も受け付ける
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return normalize_items(parsed)
        except json.JSONDecodeError:
            pass

    parts = re.split(r"[,\n、;]+", text)
    return normalize_items(parts)


def build_media_entry(value):
    media_meta = {}
    url_candidate = None
    if isinstance(value, dict):
        media_meta = value
        url_candidate = first_value(media_meta, MEDIA_URL_KEYS)
    else:
        url_candidate = str(value).strip()

    if not url_candidate:
        return None

    converted_url = to_web_image_url(url_candidate)
    if not converted_url:
        return None

    entry = {k: v for k, v in media_meta.items() if k not in MEDIA_URL_KEYS}
    entry["url"] = converted_url

    if "poster" in entry:
        entry["poster"] = to_web_image_url(entry["poster"])

    entry_type = entry.get("type")
    if entry_type:
        entry["type"] = entry_type.lower()
    else:
        inferred = infer_media_type_from_url(converted_url)
        if inferred:
            entry["type"] = inferred

    return entry


def combine_hobbies(raw_values):
    values = []
    seen = set()
    for value in raw_values:
        if not value:
            continue
        for item in parse_list(value):
            if isinstance(item, dict):
                continue
            text = str(item).strip()
            if text == "" or text in seen:
                continue
            seen.add(text)
            values.append(text)
    return " / ".join(values)


def extract_drive_file_id(url):
    parsed = urlparse(url)
    if "drive.google.com" not in parsed.netloc:
        return ""

    # /file/d/<FILE_ID>/view
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", parsed.path)
    if match:
        return match.group(1)

    # /open?id=<FILE_ID> or other ?id=
    query_id = parse_qs(parsed.query).get("id", [])
    if query_id:
        return query_id[0]

    return ""


def to_web_image_url(url):
    value = str(url).strip()
    if not value:
        return ""

    file_id = extract_drive_file_id(value)
    if not file_id:
        return value

    # Google Driveの共有URLをWeb表示向けURLへ変換
    return f"https://drive.google.com/uc?export=view&id={file_id}"


def normalize_gender(value):
    v = str(value).strip().lower()
    if v in ("male", "man", "m", "男性"):
        return "male"
    if v in ("female", "woman", "f", "女性"):
        return "female"
    return ""


def slugify(value):
    value = unicodedata.normalize("NFKC", str(value)).lower().strip()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-_]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value


def yaml_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def to_front_matter(model):
    lines = ["---"]
    order = [
        "layout",
        "name",
        "kana",
        "gender",
        "height",
        "age",
        "university",
        "hobby_1",
        "hobby_2",
        "hobby_3",
        "skill_hobby",
        "miss_contest_year",
        "tags",
        "images",
        "instagram_url",
        "x_url",
        "tiktok_url",
    ]

    for key in order:
        if key not in model:
            continue
        value = model[key]
        if value == "" or value is None:
            continue

        if isinstance(value, list):
            if not value:
                continue
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    prioritized_keys = ["url", "type", "poster", "alt"]
                    seen = set()
                    subitems = []
                    for subkey in prioritized_keys:
                        if subkey in item:
                            subitems.append((subkey, item[subkey]))
                            seen.add(subkey)
                    for subkey, subvalue in item.items():
                        if subkey not in seen:
                            subitems.append((subkey, subvalue))

                    for idx, (subkey, subvalue) in enumerate(subitems):
                        indent = "  - " if idx == 0 else "    "
                        lines.append(f"{indent}{subkey}: {yaml_scalar(subvalue)}")
                else:
                    lines.append(f"  - {yaml_scalar(item)}")
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")

    lines.append("---")
    return "\n".join(lines) + "\n"


def build_model_record(record, index):
    name = first_value(record, ["名前", "氏名", "name"])
    kana = first_value(record, ["フリガナ", "ふりがな", "名前カナ", "かな", "カナ", "kana"])
    university = first_value(record, ["大学", "university", "school"])
    # モデルIDは常に自動生成（シート入力値は使わない）
    model_id = slugify(f"{name}-{university}")
    if not model_id:
        model_id = f"model-{index}"

    age = parse_int(first_value(record, ["年齢", "age"]))
    height = parse_int(first_value(record, ["身長", "height", "height_cm"]))
    gender = normalize_gender(first_value(record, ["性別", "gender"]))

    tags = parse_list(
        first_value(record, ["タグ", "タグ（複数選択）", "タグ（複数）", "tags", "Tags"])
    )
    raw_images = parse_list(first_value(record, ["画像・動画", "画像", "images", "image_urls"]))
    processed_images = []
    for image in raw_images:
        entry = build_media_entry(image)
        if entry:
            processed_images.append(entry)
    images = processed_images

    hobby_1 = first_value(record, ["趣味①（必須）"])
    hobby_2 = first_value(record, ["趣味②（任意）"])
    hobby_3 = first_value(record, ["趣味③（任意）"])
    skill_hobby = combine_hobbies(
        [
            hobby_1,
            hobby_2,
            hobby_3,
            first_value(record, ["特技・趣味", "特技", "趣味", "skill_hobby", "skills_hobbies"]),
        ]
    )
    miss_contest_year = first_value(
        record,
        ["ミスコン出場年度", "出場年度", "miss_contest_year", "contest_year"],
    )

    instagram_url = first_value(record, ["instagram_url", "instagram", "Instagram"])
    x_url = first_value(record, ["x_url", "x", "X", "twitter_url", "twitter"])
    tiktok_url = first_value(record, ["tiktok_url", "tiktok", "TikTok"])

    model = {
        "id": model_id,
        "layout": "model",
        "name": name,
        "kana": kana,
        "gender": gender,
        "height": height,
        "age": age,
        "university": university,
        "hobby_1": hobby_1,
        "hobby_2": hobby_2,
        "hobby_3": hobby_3,
        "skill_hobby": skill_hobby,
        "miss_contest_year": miss_contest_year,
        "tags": tags,
        "images": images,
        "instagram_url": instagram_url,
        "x_url": x_url,
        "tiktok_url": tiktok_url,
    }
    return model_id, model


def main():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open(SHEET_NAME).sheet1
    raw_records = sheet.get_all_records()
    site_url, baseurl = load_site_url_config()

    models = []
    os.makedirs("_models", exist_ok=True)
    current_ids = set()
    used_ids = set()
    row_url_pairs = []

    for i, record in enumerate(raw_records, start=1):
        model_id, model = build_model_record(record, i)

        # 重複時は連番サフィックスを付与
        base_id = model_id
        n = 2
        while model_id in used_ids:
            model_id = f"{base_id}-{n}"
            n += 1
        used_ids.add(model_id)

        model["id"] = model_id
        current_ids.add(model_id)
        models.append(model)
        row_url_pairs.append((i + 1, build_model_page_url(model_id, site_url, baseurl)))

        filepath = f"_models/{model_id}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(to_front_matter(model))

    os.makedirs("_data", exist_ok=True)
    with open("_data/models.json", "w", encoding="utf-8") as f:
        json.dump(models, f, ensure_ascii=False, indent=2)

    update_model_page_urls(sheet, row_url_pairs)

    # シート0件時に既存ページを全削除しない安全策
    if not raw_records:
        print("No records found. Skip deleting existing model files.")
        return

    existing_files = glob.glob("_models/*.md")
    for file_path in existing_files:
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        if file_name not in current_ids:
            os.remove(file_path)
            print(f"Deleted obsolete model page: {file_name}")


if __name__ == "__main__":
    main()
