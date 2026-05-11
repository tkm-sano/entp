#!/usr/bin/env python3
"""
sync_notion.py — MissConnect モデル名簿 Sheet → Notion 同期
GitHub Actions の update-models.yml から fetch_and_generate.py の
直後に呼び出す。URL書き戻し済みのシートを読み、Notion を upsert する。

必要な環境変数:
  NOTION_TOKEN   : Notion インテグレーショントークン
  NOTION_DB_ID   : Notion データベース ID（省略時はデフォルト値を使用）
  GOOGLE_SHEETS_CREDS_FILE: 認証ファイルパス（省略時は creds.json）
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ── 設定 ──────────────────────────────────────────────────────────────────────
SHEET_NAME     = "モデル一覧"
def _extract_notion_id(raw: str) -> str:
    """Notion DB ID を URL 形式・ハイフンなし形式どちらでも正規化する。"""
    raw = raw.strip()
    # 32文字の16進数を抽出
    m = re.search(r'[0-9a-fA-F]{32}', raw.replace('-', ''))
    if m:
        h = m.group(0).lower()
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
    return raw

NOTION_DB_ID   = _extract_notion_id(os.environ.get("NOTION_DB_ID", "1c60cd11-eda2-4625-8549-3f5896c7ce05"))
NOTION_API     = "https://api.notion.com/v1"
NOTION_VER     = "2022-06-28"
CREDS_FILE     = os.environ.get("GOOGLE_SHEETS_CREDS_FILE", "creds.json")
SLEEP_SEC      = 0.35   # Notion API レート制限対策
BANK_OTHER_COL = "銀行名（その他）"


# ── ヘッダー正規化 ─────────────────────────────────────────────────────────────
def normalize_header(h: str) -> str:
    """改行・全角括弧を ASCII に変換して正規化（NotionSync.gs と同じロジック）"""
    h = re.sub(r"[\n\r]+", "", str(h or ""))
    h = h.replace("（", "(").replace("）", ")")
    return h.strip()


# ── 列名 → Notion プロパティ名・型 マッピング ─────────────────────────────────
COLUMN_MAP: dict[str, tuple[str, str]] = {
    "名前":                    ("名前",           "title"),
    "フリガナ":                ("フリガナ",        "rich_text"),
    "モデルID":                ("モデルID",        "rich_text"),
    "タイムスタンプ":           ("タイムスタンプ",  "date"),
    "メールアドレス":           ("メール",          "email"),
    "電話番号":                ("電話",            "phone_number"),
    "表示フラグ":              ("表示フラグ",       "select"),
    "大学":                    ("大学",            "rich_text"),
    "性別":                    ("性別",            "select"),
    "生年月日":                ("生年月日",         "rich_text"),
    "身長":                    ("身長",            "rich_text"),
    "趣味・特技①(必須)":       ("趣味・特技1",     "rich_text"),
    "趣味・特技②(任意)":       ("趣味・特技2",     "rich_text"),
    "趣味・特技③(任意)":       ("趣味・特技3",     "rich_text"),
    "ミスコン出場年度":         ("ミスコン出場年度", "rich_text"),
    "Instagramユーザーネーム":  ("Instagram",       "rich_text"),
    "Xユーザーネーム":         ("X",               "rich_text"),
    "TikTokユーザーネーム":    ("TikTok",          "rich_text"),
    "銀行名":                  ("銀行名",           "rich_text_bank"),
    "支店番号":                ("支店番号",         "rich_text"),
    "口座種別":                ("口座種別",         "select"),
    "口座番号":                ("口座番号",         "rich_text"),
    "口座名義":                ("口座名義",         "rich_text"),
    "利用規約・登録契約書":     ("契約同意",         "checkbox"),
    "紹介者":                  ("紹介者",           "rich_text"),
    "個別ページURL":           ("個別ページURL",    "url"),
    "タグ①":                  ("__tag1__",         "tag"),
    "タグ②":                  ("__tag2__",         "tag"),
    "タグ③":                  ("__tag3__",         "tag"),
    "メモ":                   ("メモ",             "rich_text"),
}


def build_notion_props(normalized_row: dict) -> dict:
    def get(col: str) -> str:
        return str(normalized_row.get(normalize_header(col), "") or "").strip()

    props: dict = {}
    tags: list[dict] = []

    for col_name, (notion_name, prop_type) in COLUMN_MAP.items():
        raw = get(col_name)

        if prop_type == "tag":
            if raw:
                tags.append({"name": raw})
            continue

        if prop_type == "rich_text_bank":
            if raw == "その他":
                raw = get(BANK_OTHER_COL)
            prop_type = "rich_text"

        if prop_type == "title":
            props[notion_name] = {"title": [{"text": {"content": raw}}]}

        elif prop_type == "rich_text":
            if raw:
                props[notion_name] = {"rich_text": [{"text": {"content": raw}}]}

        elif prop_type == "email":
            if raw:
                props[notion_name] = {"email": raw}

        elif prop_type == "phone_number":
            if raw:
                props[notion_name] = {"phone_number": raw}

        elif prop_type == "url":
            if raw:
                props[notion_name] = {"url": raw}

        elif prop_type == "checkbox":
            props[notion_name] = {"checkbox": "同意" in raw}

        elif prop_type == "date":
            if raw:
                for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                            "%Y/%m/%d", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(raw, fmt)
                        props[notion_name] = {
                            "date": {"start": dt.strftime("%Y-%m-%dT%H:%M:%S+09:00")}
                        }
                        break
                    except ValueError:
                        continue

        elif prop_type == "select":
            VALID_SELECT = {
                "表示フラグ":  {"表示", "非表示"},
                "性別":        {"男性", "女性"},
                "口座種別":    {"普通", "当座"},
            }
            if raw in VALID_SELECT.get(notion_name, set()):
                props[notion_name] = {"select": {"name": raw}}

    if tags:
        props["タグ"] = {"multi_select": tags}

    return props


# ── Notion API ────────────────────────────────────────────────────────────────
def notion_request(method: str, path: str, token: str, body: dict = None) -> dict:
    url = NOTION_API + path
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VER,
        "Content-Type":  "application/json",
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Notion API {e.code}: {e.read().decode('utf-8')}") from e


def find_page_id(model_id: str, token: str) -> str | None:
    result = notion_request("POST", f"/databases/{NOTION_DB_ID}/query", token, {
        "filter": {
            "property": "モデルID",
            "rich_text": {"equals": model_id},
        },
        "page_size": 1,
    })
    pages = result.get("results", [])
    return pages[0]["id"] if pages else None


def upsert_page(model_id: str, props: dict, token: str) -> str:
    page_id = find_page_id(model_id, token)
    if page_id:
        notion_request("PATCH", f"/pages/{page_id}", token, {"properties": props})
        return "updated"
    else:
        notion_request("POST", "/pages", token, {
            "parent":     {"database_id": NOTION_DB_ID},
            "properties": props,
        })
        return "created"


# ── メイン ────────────────────────────────────────────────────────────────────
def main() -> None:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("⚠️  NOTION_TOKEN が未設定のため Notion 同期をスキップします。")
        return
    print(f"🔍 NOTION_DB_ID: {NOTION_DB_ID}")
    print(f"🔍 TOKEN prefix: {token[:10]}...")

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
    client = gspread.authorize(creds)
    sheet  = client.open(SHEET_NAME).sheet1

    all_records = sheet.get_all_records()
    print(f"📄 シート行数: {len(all_records)}")

    success = created = updated = skipped = errors = 0

    for i, record in enumerate(all_records, start=2):
        normalized_row = {normalize_header(k): v for k, v in record.items()}

        model_id = str(normalized_row.get("モデルID", "") or "").strip()
        name     = str(normalized_row.get("名前",     "") or "").strip()

        if not model_id:
            skipped += 1
            continue

        try:
            props  = build_notion_props(normalized_row)
            action = upsert_page(model_id, props, token)
            if action == "updated":
                print(f"  ✅ 更新: {model_id}  {name}")
                updated += 1
            else:
                print(f"  🆕 作成: {model_id}  {name}")
                created += 1
            success += 1
            time.sleep(SLEEP_SEC)
        except Exception as exc:
            print(f"  ❌ エラー ({model_id} / {name}): {exc}")
            errors += 1

    print()
    print("=== Notion 同期結果 ===")
    print(f"✅ 成功: {success} 件  (更新: {updated} / 作成: {created})")
    print(f"⏭  スキップ（ID なし）: {skipped} 件")
    print(f"❌ エラー: {errors} 件")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
