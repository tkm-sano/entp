import glob
from datetime import date, datetime
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
MODEL_ID_HEADER = "モデルID"
SITE_CONFIG_PATH = "_config.yml"
MODEL_IMAGE_DIR = os.path.join("assets", "images", "models")
MODEL_VIDEO_DIR = os.path.join("assets", "videos", "models")

MEDIA_URL_KEYS = ["url", "src", "path", "image", "source"]
VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".m4v", ".ogv")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")


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


def extract_model_id_from_page_url(url):
    value = str(url).strip()
    if not value:
        return ""

    parsed = urlparse(value)
    path = parsed.path if parsed.scheme or parsed.netloc else value
    match = re.search(r"/models/([^/]+)/?$", path)
    if not match:
        return ""

    return slugify(match.group(1))


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


def update_model_ids(sheet, row_id_pairs):
    if not row_id_pairs:
        return

    model_id_col = ensure_sheet_column(sheet, MODEL_ID_HEADER)
    updates = [
        {
            "range": rowcol_to_a1(row, model_id_col),
            "values": [[model_id]],
        }
        for row, model_id in row_id_pairs
    ]
    sheet.batch_update(updates, value_input_option="RAW")
    print(f"Updated {len(row_id_pairs)} IDs in sheet column '{MODEL_ID_HEADER}'.")


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


def parse_birth_date(value):
    if value is None:
        return ""

    text = str(value).strip()
    if text == "":
        return ""

    normalized = (
        text.replace("年", "-")
        .replace("月", "-")
        .replace("日", "")
        .replace("/", "-")
        .replace(".", "-")
    )
    normalized = re.sub(r"\s+", "", normalized)

    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y%m%d", "%Y%m"):
        try:
            parsed = datetime.strptime(normalized, fmt)
            if fmt in ("%Y-%m", "%Y%m"):
                return parsed.strftime("%Y-%m-01")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", normalized)
    if not match:
        return ""

    year, month, day = map(int, match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def calculate_age(birth_date, today=None):
    if not birth_date:
        return 0

    try:
        born = datetime.strptime(birth_date, "%Y-%m-%d").date()
    except ValueError:
        return 0

    today = today or date.today()
    age = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        age -= 1
    return max(age, 0)


def extract_instagram_username(value):
    text = str(value).strip()
    if text == "":
        return ""

    if "instagram.com" not in text:
        return text.lstrip("@")

    parsed = urlparse(text)
    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return ""

    username = path_parts[0]
    if username.lower() in {"p", "reel", "stories", "explore"}:
        return ""

    return username.lstrip("@")


def is_hidden_model(record):
    display_flag = first_value(record, ["表示フラグ", "display_flag", "visible_flag"])
    return display_flag == "非表示"


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


def sort_key_for_path(path):
    parts = re.split(r"(\d+)", os.path.basename(path).lower())
    key = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part)
    return key


def to_site_asset_path(path):
    normalized = str(path).replace(os.sep, "/").lstrip("./")
    if not normalized.startswith("assets/"):
        return f"/{normalized}"
    return f"/{normalized}"


def find_matching_poster(video_path):
    base_dir = os.path.dirname(video_path)
    stem = os.path.splitext(os.path.basename(video_path))[0]
    candidates = []
    for ext in IMAGE_EXTENSIONS:
        candidates.append(os.path.join(base_dir, f"{stem}-poster{ext}"))
        candidates.append(os.path.join(base_dir, f"{stem}_poster{ext}"))
    poster_dir = os.path.join(MODEL_IMAGE_DIR, os.path.basename(base_dir))
    for ext in IMAGE_EXTENSIONS:
        candidates.append(os.path.join(poster_dir, f"{stem}-poster{ext}"))
        candidates.append(os.path.join(poster_dir, f"{stem}_poster{ext}"))
    for candidate in candidates:
        if os.path.exists(candidate):
            return to_site_asset_path(candidate)
    return ""


def load_assets_media_entries(model_id):
    entries = []
    image_dir = os.path.join(MODEL_IMAGE_DIR, model_id)
    video_dir = os.path.join(MODEL_VIDEO_DIR, model_id)

    image_paths = []
    for ext in IMAGE_EXTENSIONS:
        image_paths.extend(glob.glob(os.path.join(image_dir, f"*{ext}")))
        image_paths.extend(glob.glob(os.path.join(image_dir, f"*{ext.upper()}")))
    for path in sorted(set(image_paths), key=sort_key_for_path):
        lower_name = os.path.basename(path).lower()
        if "-poster." in lower_name or "_poster." in lower_name:
            continue
        entries.append({"url": to_site_asset_path(path)})

    video_paths = []
    for ext in VIDEO_EXTENSIONS:
        video_paths.extend(glob.glob(os.path.join(video_dir, f"*{ext}")))
        video_paths.extend(glob.glob(os.path.join(video_dir, f"*{ext.upper()}")))
    for path in sorted(set(video_paths), key=sort_key_for_path):
        entry = {
            "url": to_site_asset_path(path),
            "type": "video",
        }
        poster = find_matching_poster(path)
        if poster:
            entry["poster"] = poster
        entries.append(entry)

    return entries


def media_entry_key(entry):
    if not isinstance(entry, dict):
        return ("value", str(entry).strip())
    return (
        str(entry.get("type", "image")).strip().lower(),
        str(entry.get("url", "")).strip(),
        str(entry.get("poster", "")).strip(),
    )


def merge_media_entries(primary_entries, secondary_entries):
    merged = []
    seen = set()

    for entry in list(primary_entries) + list(secondary_entries):
        if not entry:
            continue
        key = media_entry_key(entry)
        if key in seen:
            continue
        seen.add(key)
        merged.append(entry)

    return merged

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

    if value.startswith("/assets/") or value.startswith("assets/"):
        normalized = value if value.startswith("/") else f"/{value}"
        return normalized

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


def build_model_match_keys(record):
    keys = set()

    def add(parts):
        normalized = [slugify(part) for part in parts if str(part).strip()]
        if normalized:
            keys.add("|".join(normalized))

    name = first_value(record, ["名前", "氏名", "name"])
    kana = first_value(record, ["フリガナ", "ふりがな", "名前カナ", "かな", "カナ", "kana"])
    university = first_value(record, ["大学", "university", "school"])
    instagram_url = first_value(record, ["instagram_url", "instagram", "Instagram"])
    x_url = first_value(record, ["x_url", "x", "X", "twitter_url", "twitter"])
    tiktok_url = first_value(record, ["tiktok_url", "tiktok", "TikTok"])

    add([name, kana, university])
    add([name, university])
    add([name, kana])
    add([name])
    add([instagram_url])
    add([x_url])
    add([tiktok_url])

    return keys


def load_existing_model_id_map(path=os.path.join("_data", "models.json")):
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        try:
            existing_models = json.load(f)
        except json.JSONDecodeError:
            return {}

    id_map = {}
    for model in existing_models:
        model_id = slugify(model.get("id", ""))
        if not model_id:
            continue

        candidate_records = [
            {
                "名前": model.get("name", ""),
                "フリガナ": model.get("kana", ""),
                "大学": model.get("university", ""),
                "instagram_url": model.get("instagram_url", ""),
                "x_url": model.get("x_url", ""),
                "tiktok_url": model.get("tiktok_url", ""),
            }
        ]
        for record in candidate_records:
            for key in build_model_match_keys(record):
                id_map.setdefault(key, model_id)

    return id_map


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
        "birth_date",
        "university",
        "hobby_1",
        "hobby_2",
        "hobby_3",
        "skill_hobby",
        "miss_contest_year",
        "tags",
        "images",
        "instagram_username",
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


def build_model_record(record, index, existing_model_id_map=None):
    name = first_value(record, ["名前", "氏名", "name"])
    kana = first_value(record, ["フリガナ", "ふりがな", "名前カナ", "かな", "カナ", "kana"])
    university = first_value(record, ["大学", "university", "school"])
    model_id = first_value(record, [MODEL_ID_HEADER, "model_id", "id"])
    if model_id:
        model_id = slugify(model_id)
    if not model_id:
        model_id = extract_model_id_from_page_url(first_value(record, [MODEL_PAGE_URL_HEADER]))
    if not model_id and existing_model_id_map:
        for match_key in build_model_match_keys(record):
            if match_key in existing_model_id_map:
                model_id = existing_model_id_map[match_key]
                break
    if not model_id:
        model_id = slugify(f"{name}-{university}")
    if not model_id:
        model_id = f"model-{index}"

    birth_date = parse_birth_date(first_value(record, ["生年月日", "birth_date", "birthday", "dob"]))
    age = calculate_age(birth_date) if birth_date else parse_int(first_value(record, ["年齢", "age"]))
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
    images = merge_media_entries(processed_images, load_assets_media_entries(model_id))

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
    instagram_username = first_value(
        record,
        ["instagram_username", "Instagramユーザーネーム", "インスタのユーザーネーム", "インスタユーザーネーム"],
    )
    if not instagram_username:
        instagram_username = extract_instagram_username(instagram_url)
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
        "birth_date": birth_date,
        "university": university,
        "hobby_1": hobby_1,
        "hobby_2": hobby_2,
        "hobby_3": hobby_3,
        "skill_hobby": skill_hobby,
        "miss_contest_year": miss_contest_year,
        "tags": tags,
        "images": images,
        "instagram_username": instagram_username,
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
    existing_model_id_map = load_existing_model_id_map()

    models = []
    os.makedirs("_models", exist_ok=True)
    os.makedirs(MODEL_IMAGE_DIR, exist_ok=True)
    current_ids = set()
    used_ids = set()
    row_id_pairs = []
    row_url_pairs = []

    for i, record in enumerate(raw_records, start=1):
        if is_hidden_model(record):
            row_id_pairs.append((i + 1, ""))
            row_url_pairs.append((i + 1, ""))
            continue

        model_id, model = build_model_record(record, i, existing_model_id_map)

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
        row_id_pairs.append((i + 1, model_id))
        row_url_pairs.append((i + 1, build_model_page_url(model_id, site_url, baseurl)))

        os.makedirs(os.path.join(MODEL_IMAGE_DIR, model_id), exist_ok=True)

        filepath = f"_models/{model_id}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(to_front_matter(model))

    os.makedirs("_data", exist_ok=True)
    with open("_data/models.json", "w", encoding="utf-8") as f:
        json.dump(models, f, ensure_ascii=False, indent=2)

    update_model_ids(sheet, row_id_pairs)
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
