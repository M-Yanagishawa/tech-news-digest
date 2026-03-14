# 📡 Tech News Digest

毎日19時（JST）に自動収集・日本語翻訳されるテックニュースのダイジェストサイトです。
GitHub Actions で生成され、GitHub Pages で公開されます。

**→ [最新のニュースを見る](https://YOUR_USERNAME.github.io/tech-news-digest/)**
**→ [アーカイブ一覧](https://YOUR_USERNAME.github.io/tech-news-digest/archive/)**

---

## 特徴

- 🌐 **多ソース収集** — Hacker News・Reddit・Zenn・セキュリティRSSを一括取得
- 🤖 **日本語翻訳** — 英語タイトルを自動で日本語に翻訳（原文も表示）
- 📂 **アーカイブ** — 日付別（`YYYY/MM/YYYY-MM-DD.html`）で過去分を永続保存
- 📱 **モバイル対応** — スマホで快適に読めるダークテーマUI
- 🔔 **プッシュ通知** — 更新時に [ntfy.sh](https://ntfy.sh/) でスマホに通知

---

## ニュースソース

| ソース | カテゴリ |
|--------|----------|
| [Hacker News](https://news.ycombinator.com/) | セキュリティ・AI・クラウド・フロントエンド・その他 |
| [Reddit r/webdev](https://reddit.com/r/webdev) | Web開発・フロントエンド |
| [Reddit r/programming](https://reddit.com/r/programming) | プログラミング全般 |
| [Zenn](https://zenn.dev/) | 日本語技術記事トレンド |
| [Krebs on Security](https://krebsonsecurity.com/) | セキュリティインシデント |
| [Bleeping Computer](https://www.bleepingcomputer.com/) | セキュリティインシデント |
| [CISA Advisories](https://www.cisa.gov/cybersecurity-advisories) | 公式セキュリティ警告 |

---

## サイト構成

```
https://USERNAME.github.io/tech-news-digest/
│
├── index.html          最新のニュース（毎日更新）
├── archive/
│   └── index.html      過去のアーカイブ一覧
└── YYYY/
    └── MM/
        └── YYYY-MM-DD.html   日付別アーカイブ（永続保存）
```

---

## リポジトリ構成

```
tech-news-digest/
├── .github/
│   └── workflows/
│       └── daily-news.yml    GitHub Actions ワークフロー（毎日19:05 JST）
├── generate_news.py           ニュース収集・翻訳・HTML生成スクリプト
├── requirements.txt           Python依存パッケージ
└── SETUP_GUIDE.md             詳細セットアップ手順
```

---

## セットアップ

セットアップ手順の詳細は **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** を参照してください。

大まかな流れは以下の通りです：

1. このリポジトリを **Fork** またはテンプレートとして使用
2. **Settings → Pages** で Source を `gh-pages` ブランチに設定
3. **Settings → Secrets** に `NTFY_TOPIC` を登録（通知用トピック名）
4. **Actions** タブから手動実行して動作確認

---

## 動作の仕組み

```
毎日 19:05 JST
      │
      ▼
GitHub Actions 起動
      │
      ├─ Hacker News API でトップ記事取得
      ├─ Reddit API でホット投稿取得
      ├─ Zenn API でトレンド記事取得
      └─ セキュリティRSSフィード取得
            │
            ▼
      deep-translator で英語タイトルを日本語翻訳
            │
            ▼
      HTML生成（ダークテーマ・モバイル対応）
      │
      ├─ dist/index.html（最新・毎日上書き）
      └─ dist/YYYY/MM/YYYY-MM-DD.html（アーカイブ）
            │
            ▼
      gh-pages ブランチにデプロイ（keep_files で過去分保持）
            │
            ▼
      ntfy.sh でスマホにプッシュ通知
```

---

## ローカル実行

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# 実行（dist/ フォルダにHTMLが生成されます）
python generate_news.py
```

---

## ライセンス

MIT License — 自由に改変・再配布できます。

---

*このプロジェクトは [Claude](https://claude.ai/) (Anthropic) を使って構築・自動化されています。*
