# talent-site

## Google Sheets連携

このリポジトリは、Google Sheetsのデータから `_data/models.json` と `_models/*.md` を更新します。

### 1. 必要な設定

1. Google Cloudで以下APIを有効化
- Google Sheets API
- Google Drive API

2. サービスアカウントを作成し、JSON鍵を発行

3. スプレッドシートをサービスアカウントの `client_email` に共有
- 対象シート名: `モデル一覧`

4. GitHub Secretsを設定
- `Settings` -> `Secrets and variables` -> `Actions` -> `Repository secrets`
- Name: `GOOGLE_SHEETS_KEY`
- Value: サービスアカウントJSON全文

### 2. シート列構成

A列から以下の順で作成:

1. モデルID（任意: 現在は未使用）
2. 名前
3. ふりがな
4. 大学
5. 性別
6. 年齢
7. 身長
8. 特技・趣味
9. ミスコン出場年度
10. タグ
11. 画像
12. instagram_url
13. x_url
14. tiktok_url

補足:
- `モデルID` は現在スクリプトで自動生成されるため、入力しなくて構いません。
- `画像` は複数指定する場合、カンマ区切りまたは改行区切りに対応しています。
- Google Driveの共有URLはWeb表示向けURLに自動変換されます。

### 3. 実行方法

GitHub Actionsから手動実行:

1. `Actions` タブ
2. `Update Models`
3. `Run workflow`

成功すると、以下が更新されます。
- `_data/models.json`
- `_models/*.md`

## セキュリティ

- `creds.json` はコミットしないでください（`.gitignore` 済み）。
- サービスアカウント鍵はGitHub Secretsで管理してください。
