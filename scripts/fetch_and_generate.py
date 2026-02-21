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
DEFAULT_IMAGE = "/assets/images/models/sample.png"
MODEL_PAGE_URL_HEADER = "個別ページURL"
SITE_CONFIG_PATH = "_config.yml"


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


def parse_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if text == "":
        return []
    parts = re.split(r"[,\n、]+", text)
    return [p.strip() for p in parts if p.strip()]


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
                lines.append(f"  - {yaml_scalar(item)}")
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")

    lines.append("---")
    return "\n".join(lines) + "\n"


def build_model_record(record, index):
    name = first_value(record, ["名前", "氏名", "name"])
    kana = first_value(record, ["ふりがな", "名前カナ", "かな", "カナ", "kana"])
    university = first_value(record, ["大学", "university", "school"])
    # モデルIDは常に自動生成（シート入力値は使わない）
    model_id = slugify(f"{name}-{university}")
    if not model_id:
        model_id = f"model-{index}"

    age = parse_int(first_value(record, ["年齢", "age"]))
    height = parse_int(first_value(record, ["身長", "height", "height_cm"]))
    gender = normalize_gender(first_value(record, ["性別", "gender"]))

    tags = parse_list(first_value(record, ["タグ", "tags"]))
    images = parse_list(first_value(record, ["画像", "images", "image_urls"]))
    converted_images = []
    for image in images:
        converted = to_web_image_url(image)
        if converted:
            converted_images.append(converted)
    images = converted_images
    if not images:
        images = [DEFAULT_IMAGE]

    skill_hobby = first_value(record, ["特技・趣味", "特技", "趣味", "skill_hobby", "skills_hobbies"])
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
