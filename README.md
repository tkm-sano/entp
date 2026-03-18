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
15. 個別ページURL（自動更新）

補足:
- `モデルID` は現在スクリプトで自動生成されるため、入力しなくて構いません。
- `個別ページURL` 列は、スクリプト実行時に `url` と `baseurl` から自動生成して書き戻します（列が無い場合は自動追加）。
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

### 4. スプレッドシートから実行する

Google Sheets の Apps Script から GitHub Actions を呼び出せます。

1. GitHub で Fine-grained Personal Access Token を作成
- 権限: `Actions: Read and write`（対象リポジトリに付与）

2. スプレッドシートで `拡張機能` -> `Apps Script` を開く

3. 以下スクリプトを追加（owner/repo は環境に合わせて変更）

```javascript
function onOpen() {
	SpreadsheetApp.getUi()
		.createMenu('連携メニュー')
		.addItem('モデル情報をGitHubへ反映', 'triggerUpdateModels')
		.addToUi();
}

function triggerUpdateModels() {
	const owner = 'YOUR_GITHUB_OWNER';
	const repo = 'talent-site';
	const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');

	if (!token) {
		throw new Error('Script Properties に GITHUB_TOKEN を設定してください');
	}

	const url = `https://api.github.com/repos/${owner}/${repo}/dispatches`;
	const payload = {
		event_type: 'update-models-from-sheet',
		client_payload: {
			triggered_by: 'google-sheets',
			spreadsheet_id: SpreadsheetApp.getActiveSpreadsheet().getId(),
		},
	};

	const res = UrlFetchApp.fetch(url, {
		method: 'post',
		contentType: 'application/json',
		headers: {
			Authorization: `Bearer ${token}`,
			Accept: 'application/vnd.github+json',
			'X-GitHub-Api-Version': '2022-11-28',
		},
		payload: JSON.stringify(payload),
		muteHttpExceptions: true,
	});

	const code = res.getResponseCode();
	if (code !== 204) {
		throw new Error(`GitHub API error: ${code} ${res.getContentText()}`);
	}
}
```

4. Apps Script の `プロジェクトの設定` -> `スクリプト プロパティ` に `GITHUB_TOKEN` を登録

5. スプレッドシートを再読み込みすると、上部に `連携メニュー` が表示される
6. `連携メニュー` -> `モデル情報をGitHubへ反映` をクリックして実行

補足:
- `repository_dispatch` はデフォルトブランチでワークフローが実行されます。
- 実行結果は GitHub の `Actions` タブで確認できます。
- 初回実行時は Apps Script の権限許可ダイアログが表示されます。

## セキュリティ

- `creds.json` はコミットしないでください（`.gitignore` 済み）。
- サービスアカウント鍵はGitHub Secretsで管理してください。
