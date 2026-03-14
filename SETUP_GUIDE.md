# Tech News Digest — 完全セットアップガイド

## 目次
1. [ディレクトリ構成の説明](#1-ディレクトリ構成)
2. [セキュリティについて（公開リポジトリで安全か）](#2-セキュリティ確認)
3. [GitHubリポジトリの作成手順](#3-githubリポジトリの作成)
4. [ファイルのアップロード手順](#4-ファイルのアップロード)
5. [GitHub Actions の設定](#5-github-actions-の設定)
6. [ntfy.sh 通知の設定](#6-ntfysh-通知の設定)
7. [動作テストと確認](#7-動作テスト)
8. [トラブルシューティング](#8-トラブルシューティング)

---

## 1. ディレクトリ構成

### リポジトリ（mainブランチ）の構成

```
tech-news-digest/                 ← GitHubリポジトリのルート
├── .github/
│   └── workflows/
│       └── daily-news.yml        ← 自動実行の設定ファイル
├── generate_news.py              ← ニュース収集・HTML生成スクリプト
└── requirements.txt              ← Python依存パッケージ
```

### 公開サイト（gh-pagesブランチ）の構成

デプロイ後、GitHub Pages で以下のURLが利用可能になります：

```
https://あなたのユーザー名.github.io/tech-news-digest/

├── index.html                    ← 最新のニュース（毎日上書き）
│
├── archive/
│   └── index.html                ← 過去の全アーカイブ一覧ページ
│
├── 2026/
│   ├── 03/
│   │   ├── 2026-03-14.html       ← 3月14日のダイジェスト（永続保存）
│   │   ├── 2026-03-15.html
│   │   └── 2026-03-16.html
│   └── 04/
│       ├── 2026-04-01.html
│       └── ...
└── 2027/
    └── ...
```

### アクセスURL一覧

| ページ | URL |
|--------|-----|
| 最新ニュース | `https://USERNAME.github.io/tech-news-digest/` |
| アーカイブ一覧 | `https://USERNAME.github.io/tech-news-digest/archive/` |
| 特定の日 | `https://USERNAME.github.io/tech-news-digest/2026/03/2026-03-14.html` |

### なぜこの構造？

- `index.html` は毎日上書き → スマホのブックマーク1つで常に最新を読める
- `YYYY/MM/YYYY-MM-DD.html` は蓄積 → 見逃した日のニュースを後から読める
- アーカイブ一覧はJavaScriptでGitHub APIを呼んで動的に一覧表示するため、手動での管理が不要

---

## 2. セキュリティ確認

### 公開リポジトリにしても大丈夫？

**結論：問題ありません。** 以下の理由による：

| 確認項目 | 状態 | 説明 |
|----------|------|------|
| コード内にAPIキー・トークン | ✅ なし | すべてGitHub Secretsで管理 |
| コード内にメールアドレス等 | ✅ なし | `GH_OWNER`はリポジトリ名から自動取得 |
| 生成されるHTMLに個人情報 | ✅ なし | 公開ニュースのタイトル+URLのみ |
| ntfyトピック名の露出 | ✅ なし | `${{ secrets.NTFY_TOPIC }}` でマスク済み |
| ワークフローログへの漏洩 | ✅ 対策済み | Secretsはログ上で `***` に自動マスク |

### ⚠️ 1点だけ注意：ntfyトピック名の選び方

ntfy.sh は**トピック名を知っている人なら誰でも**通知を送れる仕組みです。
簡単な名前（`my-news`、`tech`など）を使うとスパム通知を受ける可能性があります。

**推奨**：ランダムな英数字を含む名前を使う

```
❌ 悪い例：tech-news, mun-digest
✅ 良い例：mun-9f2k7p-tech, mun-x8qj3r
```

簡単なランダム文字列の生成方法（ブラウザのコンソールで実行）：
```javascript
Math.random().toString(36).slice(2, 10)  // → "9f2k7pa3" のような文字列
```

→ これを組み合わせて `mun-9f2k7pa3-news` のような名前にする

---

## 3. GitHubリポジトリの作成

### 3-1. リポジトリ作成

1. ブラウザで https://github.com/new を開く
2. 以下の設定で作成：

   | 設定 | 値 |
   |------|-----|
   | Repository name | `tech-news-digest` |
   | Visibility | **Public**（GitHub Pages 無料の条件） |
   | Initialize with README | ✅ チェックを入れる |

3. **Create repository** をクリック

### 3-2. GitHub Pages の有効化

1. 作成したリポジトリの **Settings** タブをクリック
2. 左メニューから **Pages** をクリック
3. **Build and deployment** セクションの **Source** を **Deploy from a branch** に変更
4. **Branch** を `gh-pages` / `/ (root)` に設定して **Save**

> **メモ**：最初のデプロイ前は gh-pages ブランチが存在しないため「Branch not found」と表示されることがあります。初回 Actions 実行後に自動で作成されます。

---

## 4. ファイルのアップロード

### 4-1. generate_news.py と requirements.txt

1. リポジトリのトップページで **Add file → Upload files** をクリック
2. `github-actions-setup` フォルダから以下2ファイルをドラッグ＆ドロップ：
   - `generate_news.py`
   - `requirements.txt`
3. Commit message: `Add news generator script`
4. **Commit changes** をクリック

### 4-2. GitHub Actions ワークフローの作成

ワークフローは `.github/workflows/` というパスに置く必要があります：

1. リポジトリで **Add file → Create new file** をクリック
2. ファイル名の欄に `.github/workflows/daily-news.yml` と入力
   - スラッシュを入力すると自動的にフォルダが作られます
3. `github-actions-setup/daily-news.yml` の内容を全てコピーして貼り付け
4. Commit message: `Add GitHub Actions workflow`
5. **Commit new file** をクリック

### アップロード後のリポジトリ構成確認

```
tech-news-digest/
├── .github/
│   └── workflows/
│       └── daily-news.yml   ✅
├── README.md
├── generate_news.py         ✅
└── requirements.txt         ✅
```

---

## 5. GitHub Actions の設定

### 5-1. Actions の有効化確認

1. リポジトリの **Actions** タブをクリック
2. 「I understand my workflows, go ahead and enable them」と表示されたらクリックして有効化

### 5-2. ワークフローの権限設定

1. リポジトリ **Settings → Actions → General** を開く
2. **Workflow permissions** セクションで **Read and write permissions** を選択
3. **Save** をクリック

---

## 6. ntfy.sh 通知の設定

### 6-1. アプリのインストール

| プラットフォーム | ダウンロード |
|-----------------|-------------|
| iPhone / iPad | [App Store](https://apps.apple.com/app/ntfy/id1625396347) |
| Android | [Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy) |

### 6-2. トピック名の決定

安全なトピック名を決めます（上の「セキュリティ確認」参照）：

例：`mun-9f2k7pa3-news`

### 6-3. GitHub Secrets への登録

1. リポジトリ **Settings → Secrets and variables → Actions** を開く
2. **New repository secret** をクリック
3. 以下を入力：
   - **Name**: `NTFY_TOPIC`
   - **Secret**: 決めたトピック名（例: `mun-9f2k7pa3-news`）
4. **Add secret** をクリック

> Secretsはリポジトリのコード上からは一切見えません。GitHub Actionsが実行するときにのみ使用され、ログ上では `***` に自動マスクされます。

### 6-4. アプリでのサブスクライブ

1. ntfyアプリを開く
2. `+` ボタン（または「Add topic」）をタップ
3. トピック名を入力（例: `mun-9f2k7pa3-news`）
4. **Subscribe** をタップ

---

## 7. 動作テスト

### 手動実行

1. リポジトリ **Actions** タブを開く
2. 左メニューで **📡 Daily Tech News Digest** をクリック
3. 右側の **Run workflow** ボタンをクリック → **Run workflow**
4. 約5〜10分待つ

### 確認チェックリスト

- [ ] Actions の実行が ✅ 緑になっている
- [ ] `https://あなたのユーザー名.github.io/tech-news-digest/` にアクセスできる
- [ ] スマホのntfyアプリに通知が届いた
- [ ] 通知をタップするとニュースページが開く
- [ ] `https://あなたのユーザー名.github.io/tech-news-digest/archive/` にアーカイブ一覧が表示される

---

## 8. トラブルシューティング

### Actions が失敗する場合

リポジトリ → Actions → 失敗したジョブ → 各ステップをクリックしてログを確認

| エラー内容 | 対処方法 |
|-----------|----------|
| `Permission denied` to push to gh-pages | Settings → Actions → General → Workflow permissions を「Read and write」に設定 |
| `pip install` 失敗 | `requirements.txt` が正しく配置されているか確認 |
| Translation エラー（翻訳スキップ） | 軽微な問題。HTMLは生成される。`deep-translator` の一時的な制限の可能性 |
| `dist/index.html` が空 | データソースへの接続エラー。翌日再実行すれば通常解決 |

### Pages が表示されない場合

- Settings → Pages で Source が `gh-pages` ブランチになっているか確認
- 初回デプロイ後3〜5分待つ（反映に時間がかかることがある）

### ntfy 通知が届かない場合

1. GitHub Secrets の `NTFY_TOPIC` が正しく設定されているか確認
2. ntfyアプリで対象トピックをサブスクライブしているか確認（大文字小文字も一致させる）
3. Actions のログで「Notification sent (HTTP 200)」が出ているか確認

### アーカイブ一覧が表示されない場合

- GitHub APIのレート制限（60リクエスト/時間）に達している可能性。数時間待つと解消
- リポジトリがPublicになっているか確認（PrivateだとAPIが認証を要求する）

---

## 自動実行スケジュール（まとめ）

| タスク | 実行時刻 | 動作 |
|--------|---------|------|
| Cowork ローカルタスク | 毎日 19:00 JST | ローカルHTMLを `outputs/` フォルダに保存 |
| GitHub Actions | 毎日 19:05 JST | GitHub Pages にデプロイ → ntfy通知 |

---

## データソース一覧

| ソース | 内容 | 件数 |
|--------|------|------|
| Hacker News (Algolia) | セキュリティ・AI・クラウド・Frontend・その他 | 最大35件 |
| Reddit r/webdev | Webdev・Frontend | 最大15件 |
| Reddit r/programming | プログラミング全般 | 最大15件 |
| Zenn トレンド | 日本語技術記事 | 最大20件 |
| Krebs on Security | セキュリティインシデント | 最大8件 |
| Bleeping Computer | セキュリティインシデント | 最大8件 |
| CISA Advisories | 公式セキュリティ警告 | 最大5件 |

**合計**: 最大約106件/日
