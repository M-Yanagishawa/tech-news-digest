#!/usr/bin/env python3
"""
Tech News Daily Digest - GitHub Actions Version
Fetches HN / Reddit / Zenn / Security RSS, translates to Japanese, generates HTML.
Output: dist/index.html  +  dist/archive/YYYYMMDD.html
"""

import requests, json, html as HL, re, os, sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# ── Config ────────────────────────────────────────────────────────────────────

HN_TOP_N       = 40
REDDIT_LIMIT   = 15
ZENN_COUNT     = 20
RSS_LIMIT      = 8
TRANSLATE      = True          # set False to skip translation (faster)
UA = 'TechNewsDigest/2.0 (github-actions)'

SECURITY_KW = ['security','hack','breach','vulnerability','cve','exploit','ransomware',
                'malware','phishing','zero-day','incident','attack','cisa','threat',
                'infosec','leak','compromise','backdoor','patch','advisory']
AI_KW       = ['ai','llm','gpt','claude','machine learning','deep learning','neural',
                'openai','anthropic','gemini','llama','diffusion','transformer',
                'model','agent','inference','fine-tun','generative','copilot','ollama']
CLOUD_KW    = ['aws','amazon web','cloudflare','lambda','s3 ','ecs','eks','workers',
                'r2 ','cdn','serverless','infrastructure','kubernetes','k8s',
                'terraform','devops','cloudfront','gcp','azure','vercel','netlify']
FRONTEND_KW = ['next.js','nextjs','react','vue','svelte','bun','vite','typescript',
                'javascript','css','tailwind','node.js','deno','sveltekit','remix',
                'astro','tanstack','htmx','wasm','webassembly','frontend','web component']


# ── Translation ───────────────────────────────────────────────────────────────

def translate_batch(texts, target='ja', batch_size=40):
    """Translate a list of strings to Japanese using deep_translator."""
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        return texts  # fallback: no translation

    results = list(texts)
    translator = GoogleTranslator(source='auto', target=target)
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        try:
            translated = translator.translate_batch(batch)
            for j, t in enumerate(translated):
                if t:
                    results[i+j] = t
        except Exception as e:
            print(f"  [WARN] Translation batch failed: {e}", file=sys.stderr)
    return results


def add_translations(items, title_field='title'):
    """Add title_ja field to each item."""
    if not TRANSLATE:
        return items
    originals = [item.get(title_field, '') for item in items]
    # Skip items that already contain CJK characters
    to_translate = [(idx, text) for idx, text in enumerate(originals)
                    if text and not re.search(r'[\u3000-\u9fff\uac00-\ud7af]', text)]
    if not to_translate:
        return items
    indices, texts = zip(*to_translate)
    translated = translate_batch(list(texts))
    for idx, ja in zip(indices, translated):
        items[idx]['title_ja'] = ja
    return items


# ── Data Fetchers ─────────────────────────────────────────────────────────────

def fetch_hn():
    print("  Hacker News (Algolia API)...")
    try:
        url = f'https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={HN_TOP_N}'
        data = requests.get(url, headers={'User-Agent': UA}, timeout=15).json()
        stories = []
        for h in data.get('hits', []):
            if not h.get('title'): continue
            stories.append({
                'title': h['title'],
                'url': h.get('url') or f"https://news.ycombinator.com/item?id={h['objectID']}",
                'hn_url': f"https://news.ycombinator.com/item?id={h['objectID']}",
                'score': h.get('points', 0),
                'comments': h.get('num_comments', 0),
                'by': h.get('author', ''),
            })
        print(f"  → {len(stories)} stories")
        return stories
    except Exception as e:
        print(f"  [WARN] HN failed: {e}", file=sys.stderr)
        return []


def fetch_reddit(sub):
    print(f"  Reddit r/{sub}...")
    try:
        url = f'https://www.reddit.com/r/{sub}/hot.json?limit={REDDIT_LIMIT}'
        data = requests.get(url, headers={'User-Agent': UA}, timeout=15).json()
        posts = []
        for c in data['data']['children']:
            p = c['data']
            if p.get('stickied'): continue
            posts.append({
                'title': p['title'],
                'url': p.get('url', f"https://reddit.com{p['permalink']}"),
                'reddit_url': f"https://reddit.com{p['permalink']}",
                'score': p['score'],
                'num_comments': p.get('num_comments', 0),
                'subreddit': p['subreddit'],
                'flair': p.get('link_flair_text', '') or '',
            })
        print(f"  → {len(posts)} posts")
        return posts
    except Exception as e:
        print(f"  [WARN] Reddit r/{sub} failed: {e}", file=sys.stderr)
        return []


def fetch_zenn():
    print("  Zenn trending...")
    try:
        url = f'https://zenn.dev/api/articles?order=trending&count={ZENN_COUNT}'
        data = requests.get(url, headers={'User-Agent': UA}, timeout=15).json()
        articles = []
        for a in data.get('articles', []):
            user = a.get('user', {})
            username = user.get('username', '')
            slug = a.get('slug', '')
            articles.append({
                'title': a.get('title', ''),
                'url': f"https://zenn.dev/{username}/articles/{slug}",
                'score': a.get('liked_count', 0),
                'comments': a.get('comments_count', 0),
                'emoji': a.get('emoji', '📝'),
                'author': user.get('name', username),
            })
        print(f"  → {len(articles)} articles")
        return articles
    except Exception as e:
        print(f"  [WARN] Zenn failed: {e}", file=sys.stderr)
        return []


def fetch_rss(name, url):
    print(f"  RSS: {name}...")
    try:
        resp = requests.get(url, headers={'User-Agent': UA}, timeout=15)
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall('.//item')[:RSS_LIMIT]:
            t = item.find('title')
            l = item.find('link')
            d = item.find('description')
            pub = item.find('pubDate')
            title = t.text.strip() if t is not None and t.text else ''
            link  = l.text.strip() if l is not None and l.text else '#'
            desc  = re.sub(r'<[^>]+>', '', (d.text or '') if d is not None else '')[:200]
            date  = (pub.text or '')[:16] if pub is not None else ''
            if title:
                items.append({'title': title, 'url': link, 'description': desc,
                               'date': date, 'source': name})
        # Atom fallback
        if not items:
            ns = {'a': 'http://www.w3.org/2005/Atom'}
            for e in root.findall('.//a:entry', ns)[:RSS_LIMIT]:
                t   = e.find('a:title', ns)
                l   = e.find('a:link', ns)
                pub = e.find('a:updated', ns) or e.find('a:published', ns)
                title = (t.text or '').strip() if t is not None else ''
                link  = l.get('href', '#') if l is not None else '#'
                date  = (pub.text or '')[:16] if pub is not None else ''
                if title:
                    items.append({'title': title, 'url': link, 'description': '',
                                   'date': date, 'source': name})
        print(f"  → {len(items)} items")
        return items
    except Exception as e:
        print(f"  [WARN] RSS {name} failed: {e}", file=sys.stderr)
        return []


# ── Categoriser ───────────────────────────────────────────────────────────────

def categorize(title, url=''):
    t = (title + ' ' + (url or '')).lower()
    if any(k in t for k in SECURITY_KW): return 'security'
    if any(k in t for k in AI_KW):       return 'ai'
    if any(k in t for k in CLOUD_KW):    return 'cloud'
    if any(k in t for k in FRONTEND_KW): return 'frontend'
    return 'other'


# ── Importance Scoring ────────────────────────────────────────────────────────
# 純粋なキーワードマッチング + エンゲージメント数によるスコアリング
# 外部API・Claudeは不使用 — Python のみで完結
#
# Level 3 = CRITICAL  … ゼロデイ・ランサムウェア・大規模侵害など即対応が必要な情報
# Level 2 = HIGH      … 重要CVE・メジャーバージョンアップ・大きな仕様変更など要チェック
# Level 1 = NORMAL    … 通常の技術情報・議論・チュートリアルなど

_CRITICAL_KW = [
    'zero-day', 'zero day', '0-day', '0day',
    'actively exploited', 'in the wild', 'exploitation detected',
    'remote code execution', ' rce ', '(rce)',
    'ransomware', 'wiper malware', 'nation-state',
    'supply chain attack', 'supply chain compromise',
    'backdoor discovered', 'backdoor found',
    'emergency patch', 'emergency update', 'emergency directive',
    'critical infrastructure attack',
    'millions of users', 'millions of accounts',
    'massive data breach', 'large-scale breach',
    'critical vulnerability',
]

_HIGH_KW = [
    'cve-20', 'vulnerability', 'security advisory', 'security alert',
    'patch tuesday', 'exploit', 'malware', 'phishing campaign',
    'breach', 'hacked', 'data leak', 'exposed database',
    'major release', 'stable release', 'lts release', 'ga release',
    'breaking change', 'breaking changes',
    'end of life', ' eol ', 'end of support', 'deprecated',
    'critical bug', 'regression', 'security fix',
]

# メジャーバージョン番号を含む技術名のパターン（例: "React 19", "Next.js 15.2"）
_MAJOR_VER = re.compile(
    r'\b(react|next\.js|nextjs|vue|nuxt|angular|svelte|sveltekit|astro|remix|'
    r'bun|deno|node\.js|node|vite|typescript|javascript|'
    r'python|rust|go |golang|java |kotlin|swift|'
    r'kubernetes|k8s|terraform|docker|'
    r'postgres|postgresql|mysql|redis|mongodb|sqlite|'
    r'aws|cloudflare|nginx|apache)\s+v?\d+',
    re.IGNORECASE
)


def calc_importance(title: str, url: str = '', category: str = 'other',
                    engagement: int = 0) -> int:
    """
    記事の重要度を 1〜3 で返す（外部API不使用・純粋Python）。
    title / url / カテゴリ / エンゲージメント数をもとに判定。
    """
    text = (title + ' ' + (url or '')).lower()

    # キーワードで基本レベルを決定
    if any(k in text for k in _CRITICAL_KW):
        level = 3
    elif any(k in text for k in _HIGH_KW):
        level = 2
    elif _MAJOR_VER.search(title):
        level = 2
    else:
        level = 1

    # セキュリティカテゴリは最低でも HIGH
    if category == 'security' and level < 2:
        level = 2

    # 高エンゲージメント（HN 500点超 / Reddit 2000点超）は最低でも HIGH
    if engagement >= 500 and level < 2:
        level = 2

    return level


# 重要度ラベル定義（HTML出力用）
_IMP = {
    3: ('<span class="imp imp-c">🔴 CRITICAL</span>', 'crit'),
    2: ('<span class="imp imp-h">🟠 HIGH</span>',     'high'),
    1: ('', ''),
}


# ── HTML Helpers ──────────────────────────────────────────────────────────────

def esc(x): return HL.escape(str(x or ''))

def badge(score, prefix='▲'):
    try: score = int(score)
    except: score = 0
    if score >= 500:   c = '#ff4500'
    elif score >= 200: c = '#f0883e'
    elif score >= 100: c = '#d29922'
    else:              c = '#6e7681'
    return f'<span class="badge" style="background:{c}">{prefix} {score}</span>'

def domain_of(url):
    try: return url.split('/')[2].replace('www.','') if '://' in url else ''
    except: return ''

def title_block(s, url, link_class=''):
    title_ja = s.get('title_ja') or s.get('title', '')
    title_en = s.get('title', '')
    has_ja   = title_ja != title_en
    t_html   = f'<a class="tlink{" "+link_class if link_class else ""}" href="{esc(url)}" target="_blank" rel="noopener">{esc(title_ja)}</a>'
    if has_ja:
        t_html += f'<span class="title-en">{esc(title_en)}</span>'
    return f'<div class="story-title">{t_html}</div>'

def _imp_html(item):
    """重要度バッジとカードCSSクラスを返す"""
    imp = item.get('importance', 1)
    badge_html, css_class = _IMP.get(imp, ('', ''))
    return badge_html, css_class

def hn_card(s):
    url = s.get('url', s.get('hn_url','#'))
    d   = domain_of(url)
    imp_badge, imp_cls = _imp_html(s)
    cls = f'card {imp_cls}' if imp_cls else 'card'
    return (f'<div class="{cls}">'
            + title_block(s, url)
            + f'<div class="meta">{imp_badge}{badge(s.get("score",0))}'
            + f'<span class="mi">💬 {s.get("comments",0)}</span>'
            + (f'<span class="domain">{esc(d)}</span>' if d else '')
            + f'<a href="{esc(s.get("hn_url",url))}" target="_blank" class="ext">HNで議論</a></div></div>')

def reddit_card(p):
    flair = (f'<span class="flair">{esc(p["flair"])}</span>' if p.get('flair') else '')
    imp_badge, imp_cls = _imp_html(p)
    cls = f'card {imp_cls}' if imp_cls else 'card'
    return (f'<div class="{cls}">'
            + title_block(p, p.get('url','#'))
            + f'<div class="meta">{imp_badge}{badge(p.get("score",0))}'
            + f'<span class="mi">💬 {p.get("num_comments",0)}</span>'
            + f'<span class="sub">r/{esc(p.get("subreddit",""))}</span>'
            + flair
            + f'<a href="{esc(p.get("reddit_url","#"))}" target="_blank" class="ext">Redditで見る</a></div></div>')

def zenn_card(a):
    title_ja = a.get('title_ja') or a.get('title', '')
    title_en = a.get('title', '')
    has_ja   = title_ja != title_en
    imp_badge, imp_cls = _imp_html(a)
    cls = f'card {imp_cls}' if imp_cls else 'card'
    t_html = f'<a class="tlink" href="{esc(a["url"])}" target="_blank" rel="noopener">{esc(a.get("emoji","📝"))} {esc(title_ja)}</a>'
    if has_ja:
        t_html += f'<span class="title-en">{esc(title_en)}</span>'
    return (f'<div class="{cls}">'
            + f'<div class="story-title">{t_html}</div>'
            + f'<div class="meta">{imp_badge}{badge(a.get("score",0), "♥")}'
            + f'<span class="mi">💬 {a.get("comments",0)}</span>'
            + f'<span class="author">by {esc(a.get("author",""))}</span>'
            + f'<span class="domain">zenn.dev</span></div></div>')

def rss_card(item):
    desc  = item.get('description','')
    dhtml = (f'<p class="desc">{esc(desc[:160])}{"…" if len(desc)>160 else ""}</p>' if desc else '')
    date  = item.get('date','')[:16]
    title_ja = item.get('title_ja') or item.get('title','')
    title_en = item.get('title','')
    has_ja   = title_ja != title_en
    imp_badge, imp_cls = _imp_html(item)
    cls = f'card rss {imp_cls}' if imp_cls else 'card rss'
    t_html = f'<a class="tlink" href="{esc(item["url"])}" target="_blank" rel="noopener">{esc(title_ja)}</a>'
    if has_ja:
        t_html += f'<span class="title-en">{esc(title_en)}</span>'
    return (f'<div class="{cls}">'
            + f'<div class="story-title">{t_html}</div>'
            + dhtml
            + f'<div class="meta">{imp_badge}<span class="src-tag">{esc(item.get("source",""))}</span>'
            + (f'<span class="mi">{esc(date)}</span>' if date else '')
            + '</div></div>')

def section(icon, title, color, cards, count=None):
    cnt  = f'<span class="cnt">{count}件</span>' if count is not None else ''
    body = ''.join(cards) if cards else '<p class="empty">記事が見つかりませんでした</p>'
    return (f'<section class="ns">'
            f'<h2 class="sh" style="border-left-color:{color}">'
            f'<span class="si">{icon}</span>{title}{cnt}</h2>'
            f'<div class="sc">{body}</div></section>')


# ── HTML Builder ──────────────────────────────────────────────────────────────

CSS = """
:root{--bg:#0d1117;--sf:#161b22;--sf2:#21262d;--bd:#30363d;--tx:#e6edf3;--mu:#8b949e;--ac:#58a6ff;--or:#f0883e;--pu:#bc8cff;--re:#f85149;--gr:#3fb950}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--tx);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans JP',Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;min-height:100vh}

/* Header */
.hdr{background:linear-gradient(135deg,#1a1f2e,#0d1117);border-bottom:1px solid var(--bd);padding:16px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;backdrop-filter:blur(10px)}
.htitle{font-size:18px;font-weight:700;color:var(--ac)}.htitle span{color:var(--mu);font-weight:400;font-size:12px;display:block;margin-top:1px}
.hdate{color:var(--mu);font-size:12px;text-align:right}

/* Nav */
.nav{background:var(--sf);border-bottom:1px solid var(--bd);padding:6px 16px;display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.nav a{color:var(--mu);text-decoration:none;padding:5px 10px;border-radius:6px;font-size:12px;white-space:nowrap;transition:all .15s}
.nav a:hover,.nav a:active{background:var(--sf2);color:var(--tx)}

/* Main */
.main{max-width:900px;margin:0 auto;padding:16px 12px 60px}

/* Section */
.ns{margin-bottom:24px;animation:fi .3s ease}
@keyframes fi{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.sh{font-size:14px;font-weight:600;border-left:3px solid var(--ac);padding:4px 10px;margin-bottom:8px;display:flex;align-items:center;gap:6px;color:var(--tx)}
.si{font-size:16px}.cnt{margin-left:auto;font-size:11px;background:var(--sf2);color:var(--mu);padding:1px 7px;border-radius:12px;font-weight:400}
.sc{display:flex;flex-direction:column;gap:6px}

/* Card */
.card{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:10px 13px;transition:border-color .15s}
.card:hover{border-color:var(--ac)}
.story-title{margin-bottom:5px}
.tlink{color:var(--tx);text-decoration:none;font-weight:500;font-size:14px;line-height:1.4;display:block}
.tlink:hover{color:var(--ac)}
.title-en{display:block;font-size:11px;color:var(--mu);margin-top:2px;font-weight:400}
.meta{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.badge{font-size:11px;font-weight:700;color:#fff;padding:2px 6px;border-radius:9px}
.mi{font-size:11px;color:var(--mu)}
.domain{font-size:10px;color:var(--mu);background:var(--sf2);padding:1px 5px;border-radius:3px}
.sub{font-size:11px;color:var(--or);font-weight:600}
.flair{font-size:10px;background:var(--sf2);color:var(--pu);padding:1px 5px;border-radius:3px}
.author{font-size:11px;color:var(--mu)}
.src-tag{font-size:10px;background:#1a2640;color:var(--ac);padding:2px 6px;border-radius:3px;font-weight:500}
.ext{font-size:11px;color:var(--mu);text-decoration:none;margin-left:auto;white-space:nowrap}
.ext:hover{color:var(--ac)}
.desc{font-size:12px;color:var(--mu);margin:4px 0 5px;line-height:1.45}
.empty{color:var(--mu);font-size:13px;padding:8px 4px}
.rss{border-left:2px solid #1a2640}

/* Importance badges */
.imp{font-size:10px;font-weight:700;padding:2px 7px;border-radius:3px;letter-spacing:.3px;white-space:nowrap}
.imp-c{background:#3d1a1a;color:#f85149;border:1px solid rgba(248,81,73,.5)}
.imp-h{background:#2d1f0e;color:#f0883e;border:1px solid rgba(240,136,62,.4)}
/* Card border highlight for important items */
.card.crit{border-left:3px solid #f85149 !important;border-color:#f85149}
.card.high{border-left:3px solid #f0883e !important;border-color:rgba(240,136,62,.6)}

/* 2-col grid for desktop */
.g2{display:grid;grid-template-columns:1fr 1fr;gap:24px}

/* Footer */
.ftr{text-align:center;padding:14px;color:var(--mu);font-size:11px;border-top:1px solid var(--bd);margin-top:12px}

/* Mobile */
@media(max-width:640px){
  .g2{grid-template-columns:1fr}
  .hdr{flex-direction:column;gap:4px;align-items:flex-start;padding:12px 16px}
  .main{padding:12px 8px 70px}
  .tlink{font-size:13px}
}

/* Archive link */
.arch-link{display:inline-block;margin:4px 0 16px;font-size:12px;color:var(--mu);text-decoration:none;padding:4px 10px;border:1px solid var(--bd);border-radius:6px}
.arch-link:hover{color:var(--ac);border-color:var(--ac)}
"""


def _by_imp(items):
    """重要度（desc）→ エンゲージメント（desc）の順にソート"""
    return sorted(items, key=lambda x: (x.get('importance', 1), x.get('score', 0)), reverse=True)

def build_html(hn, reddit, zenn, rss, archive_link=''):
    now_jst = datetime.now(timezone(timedelta(hours=9)))
    date_str = now_jst.strftime('%Y年%m月%d日 %H:%M')
    date_file = now_jst.strftime('%Y%m%d')

    # カテゴリ分類（重要度はmain()で付与済み）
    cats = {k: [] for k in ('security','ai','cloud','frontend','other')}
    for s in hn: cats[categorize(s.get('title',''), s.get('url',''))].append(s)

    # 各カテゴリ内を重要度順にソート
    for key in cats:
        cats[key] = _by_imp(cats[key])

    webdev = _by_imp([p for p in reddit if p.get('subreddit') == 'webdev'])
    prog   = _by_imp([p for p in reddit if p.get('subreddit') == 'programming'])
    rss_sorted = _by_imp(rss)
    zenn_sorted = _by_imp(zenn)
    total  = len(hn) + len(reddit) + len(zenn) + len(rss)

    # CRITICALが何件あるかカウントしてヘッダーに表示
    critical_count = sum(1 for items in [hn, reddit, rss] for x in items if x.get('importance') == 3)
    critical_note  = (f' <span style="font-size:11px;color:#f85149;font-weight:700">'
                      f'⚠ CRITICAL {critical_count}件</span>') if critical_count > 0 else ''

    arch_html = (f'<a class="arch-link" href="{esc(archive_link)}">📂 過去のアーカイブ</a>' if archive_link else '')

    sec_security = section('🔐','セキュリティ・インシデント','#f85149',
        [rss_card(i) for i in rss_sorted] + [hn_card(s) for s in cats['security'][:4]],
        len(rss)+len(cats['security']))
    sec_ai    = section('🤖','AI・機械学習','#bc8cff',[hn_card(s) for s in cats['ai'][:7]],len(cats['ai']))
    sec_cloud = section('☁️','AWS・Cloudflare・クラウド','#58a6ff',[hn_card(s) for s in cats['cloud'][:7]],len(cats['cloud']))
    sec_fe    = section('⚡','フロントエンド（Next.js/Bun/TypeScript）','#3fb950',[hn_card(s) for s in cats['frontend'][:8]],len(cats['frontend']))
    sec_zenn  = section('📘','Zenn トレンド','#3ea8ff',[zenn_card(a) for a in zenn_sorted[:10]],len(zenn))
    sec_webdev = section('🌐','Reddit r/webdev','#ff4500',[reddit_card(p) for p in webdev[:7]],len(webdev))
    sec_prog   = section('💻','Reddit r/programming','#ff6534',[reddit_card(p) for p in prog[:7]],len(prog))
    sec_other  = section('📰','HN その他注目記事','#6e7681',[hn_card(s) for s in cats['other'][:8]],len(cats['other']))

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="theme-color" content="#0d1117">
<title>📡 Tech News Digest — {date_str}</title>
<style>{CSS}</style>
</head>
<body>
<header class="hdr">
  <div class="htitle">📡 Tech News Digest<span>毎日テックニュースまとめ{critical_note}</span></div>
  <div class="hdate">🕐 {date_str} JST<br>{total}件取得</div>
</header>
<nav class="nav">
  <a href="#sec">🔐 セキュリティ</a>
  <a href="#ai">🤖 AI</a>
  <a href="#cloud">☁️ クラウド</a>
  <a href="#fe">⚡ Frontend</a>
  <a href="#zenn">📘 Zenn</a>
  <a href="#reddit">🌐 Reddit</a>
  <a href="#other">📰 その他</a>
</nav>
<main class="main">
  {arch_html}
  <div id="sec">{sec_security}</div>
  <div class="g2"><div id="ai">{sec_ai}</div><div id="cloud">{sec_cloud}</div></div>
  <div id="fe">{sec_fe}</div>
  <div id="zenn">{sec_zenn}</div>
  <div class="g2" id="reddit">{sec_webdev}{sec_prog}</div>
  <div id="other">{sec_other}</div>
</main>
<footer class="ftr">
  Tech News Digest ｜ Sources: Hacker News · Reddit r/webdev・r/programming · Zenn · Krebs on Security · CISA · Bleeping Computer
</footer>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def build_archive_index(gh_owner, gh_repo, pages_url):
    """
    Generate archive/index.html — a page that lists all past digests.
    Uses the GitHub API via JavaScript (client-side) to enumerate YYYY/MM/YYYY-MM-DD.html files.
    No sensitive data is embedded here.
    """
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="theme-color" content="#0d1117">
<title>📡 Tech News Digest — アーカイブ</title>
<style>
:root{{--bg:#0d1117;--sf:#161b22;--sf2:#21262d;--bd:#30363d;--tx:#e6edf3;--mu:#8b949e;--ac:#58a6ff}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--tx);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans JP',sans-serif;font-size:14px;line-height:1.6;min-height:100vh}}
.hdr{{background:linear-gradient(135deg,#1a1f2e,#0d1117);border-bottom:1px solid var(--bd);padding:16px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10}}
.htitle{{font-size:18px;font-weight:700;color:var(--ac)}}
.htitle span{{color:var(--mu);font-weight:400;font-size:12px;display:block}}
.back{{font-size:13px;color:var(--mu);text-decoration:none;padding:6px 12px;border:1px solid var(--bd);border-radius:6px}}
.back:hover{{color:var(--ac);border-color:var(--ac)}}
.main{{max-width:700px;margin:0 auto;padding:20px 16px 60px}}
h2{{font-size:15px;font-weight:600;color:var(--tx);border-left:3px solid var(--ac);padding:4px 10px;margin:20px 0 10px}}
.month-group{{margin-bottom:16px}}
.month-label{{font-size:12px;color:var(--mu);font-weight:600;padding:4px 0 6px;border-bottom:1px solid var(--bd);margin-bottom:8px}}
.entry{{display:flex;align-items:center;padding:8px 12px;background:var(--sf);border:1px solid var(--bd);border-radius:6px;margin-bottom:5px;text-decoration:none;color:var(--tx);transition:border-color .15s}}
.entry:hover{{border-color:var(--ac);color:var(--ac)}}
.entry-date{{font-size:13px;font-weight:500}}
.entry-arrow{{margin-left:auto;font-size:12px;color:var(--mu)}}
#loading{{color:var(--mu);font-size:13px;padding:20px 0}}
#error{{color:#f85149;font-size:13px;padding:16px;background:var(--sf);border-radius:8px;border:1px solid #f85149}}
</style>
</head>
<body>
<header class="hdr">
  <div class="htitle">📡 Tech News Digest <span>アーカイブ一覧</span></div>
  <a class="back" href="{pages_url}/">← 最新へ</a>
</header>
<main class="main">
  <div id="loading">📂 アーカイブを読み込み中...</div>
  <div id="error" style="display:none"></div>
  <div id="archive-list"></div>
</main>
<script>
// GitHub API でアーカイブファイル一覧を取得（認証不要・公開リポジトリ）
const OWNER = '{gh_owner}';
const REPO  = '{gh_repo}';
const BASE  = '{pages_url}';
const API   = `https://api.github.com/repos/${{OWNER}}/${{REPO}}/git/trees/gh-pages?recursive=1`;

fetch(API, {{headers: {{'Accept': 'application/vnd.github+json'}}}})
  .then(r => {{
    if (!r.ok) throw new Error(`GitHub API: ${{r.status}}`);
    return r.json();
  }})
  .then(data => {{
    const RE = /^(\\d{{4}})\\/(\\d{{2}})\\/(\\d{{4}}-\\d{{2}}-\\d{{2}})\\.html$/;
    const files = (data.tree || [])
      .map(f => f.path)
      .filter(p => RE.test(p))
      .sort()
      .reverse();   // newest first

    document.getElementById('loading').style.display = 'none';

    if (files.length === 0) {{
      document.getElementById('archive-list').innerHTML =
        '<p style="color:var(--mu);font-size:13px;padding-top:16px">アーカイブはまだありません。</p>';
      return;
    }}

    // Group by YYYY-MM
    const grouped = {{}};
    files.forEach(path => {{
      const [, y, m, dateStr] = RE.exec(path);
      const key = `${{y}}年${{m}}月`;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push({{ path, dateStr }});
    }});

    const container = document.getElementById('archive-list');
    const totalEl = document.createElement('p');
    totalEl.style.cssText = 'color:var(--mu);font-size:12px;padding:4px 0 12px';
    totalEl.textContent = `全 ${{files.length}} 件`;
    container.appendChild(totalEl);

    Object.entries(grouped).forEach(([monthLabel, entries]) => {{
      const grp = document.createElement('div');
      grp.className = 'month-group';
      grp.innerHTML = `<div class="month-label">${{monthLabel}}</div>`;
      entries.forEach(({{ path, dateStr }}) => {{
        const [y, m, d] = dateStr.split('-');
        const a = document.createElement('a');
        a.className = 'entry';
        a.href = `${{BASE}}/${{path}}`;
        a.innerHTML = `<span class="entry-date">${{y}}年${{m}}月${{d}}日</span><span class="entry-arrow">→</span>`;
        grp.appendChild(a);
      }});
      container.appendChild(grp);
    }});
  }})
  .catch(err => {{
    document.getElementById('loading').style.display = 'none';
    const el = document.getElementById('error');
    el.style.display = 'block';
    el.textContent = `アーカイブの読み込みに失敗しました: ${{err.message}}`;
  }});
</script>
</body>
</html>"""


def main():
    print("=" * 55)
    print("  Tech News Digest — GitHub Actions Run")
    print("=" * 55)

    # Env vars injected by workflow (no secrets, just public repo info)
    gh_owner  = os.environ.get('GH_OWNER', 'M-Yanagishawa')
    gh_repo   = os.environ.get('GH_REPO',  'tech-news-digest')
    pages_url = os.environ.get('PAGES_URL', f'https://{gh_owner}.github.io/{gh_repo}').rstrip('/')

    # Fetch all data
    print("\n[1/6] Hacker News")
    hn = fetch_hn()

    print("\n[2/6] Reddit")
    reddit = fetch_reddit('webdev') + fetch_reddit('programming')

    print("\n[3/6] Zenn")
    zenn = fetch_zenn()

    print("\n[4/6] RSS Security Feeds")
    rss = []
    rss += fetch_rss('Krebs on Security', 'https://krebsonsecurity.com/feed/')
    rss += fetch_rss('Bleeping Computer',  'https://www.bleepingcomputer.com/feed/')
    rss += fetch_rss('CISA Advisories',    'https://www.cisa.gov/cybersecurity-advisories/all.xml')

    # Translate titles
    print("\n[5/7] Translating titles to Japanese...")
    hn     = add_translations(hn)
    reddit = add_translations(reddit)
    zenn_en_idx = [i for i, a in enumerate(zenn)
                   if not re.search(r'[\u3000-\u9fff]', a.get('title', ''))]
    if zenn_en_idx:
        texts = [zenn[i]['title'] for i in zenn_en_idx]
        translated = translate_batch(texts)
        for i, ja in zip(zenn_en_idx, translated):
            zenn[i]['title_ja'] = ja

    # Importance scoring (pure Python keyword + engagement heuristics)
    print("\n[6/7] Scoring importance...")
    for s in hn:
        cat = categorize(s.get('title', ''), s.get('url', ''))
        s['importance'] = calc_importance(s.get('title', ''), s.get('url', ''),
                                          cat, s.get('score', 0))
    for p in reddit:
        cat = categorize(p.get('title', ''), p.get('url', ''))
        p['importance'] = calc_importance(p.get('title', ''), p.get('url', ''),
                                          cat, p.get('score', 0))
    for a in zenn:
        a['importance'] = calc_importance(a.get('title', ''), a.get('url', ''),
                                          'other', a.get('score', 0))
    for item in rss:
        # RSSはセキュリティソースのみなのでカテゴリは 'security' 固定
        item['importance'] = calc_importance(item.get('title', ''), item.get('url', ''),
                                             'security', 0)

    critical_n = sum(1 for x in hn + reddit + rss if x.get('importance') == 3)
    high_n     = sum(1 for x in hn + reddit + rss if x.get('importance') == 2)
    print(f"  → CRITICAL:{critical_n}  HIGH:{high_n}")

    # Generate HTML
    print("\n[7/7] Building HTML...")
    now_jst   = datetime.now(timezone(timedelta(hours=9)))
    year      = now_jst.strftime('%Y')
    month     = now_jst.strftime('%m')
    date_file = now_jst.strftime('%Y-%m-%d')          # e.g. 2026-03-14

    archive_link = f"{pages_url}/archive/"
    html_content = build_html(hn, reddit, zenn, rss, archive_link)

    # ── Output directory structure ─────────────────────────────────────────
    # dist/
    #   index.html                 ← latest (overwritten every day)
    #   archive/
    #     index.html               ← archive listing page (JS-powered)
    #   YYYY/
    #     MM/
    #       YYYY-MM-DD.html        ← daily archive (kept forever)
    # ──────────────────────────────────────────────────────────────────────

    dist_dir      = 'dist'
    dated_dir     = os.path.join(dist_dir, year, month)
    archive_dir   = os.path.join(dist_dir, 'archive')

    os.makedirs(dated_dir,   exist_ok=True)
    os.makedirs(archive_dir, exist_ok=True)

    # dist/index.html (today's latest)
    with open(os.path.join(dist_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

    # dist/YYYY/MM/YYYY-MM-DD.html (permanent archive copy)
    dated_path = os.path.join(dated_dir, f'{date_file}.html')
    with open(dated_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # dist/archive/index.html (dynamic listing via GitHub API — no sensitive data)
    with open(os.path.join(archive_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(build_archive_index(gh_owner, gh_repo, pages_url))

    total = len(hn) + len(reddit) + len(zenn) + len(rss)
    print(f"\n✅  dist/index.html")
    print(f"✅  dist/{year}/{month}/{date_file}.html")
    print(f"✅  dist/archive/index.html")
    print(f"   HN:{len(hn)} Reddit:{len(reddit)} Zenn:{len(zenn)} RSS:{len(rss)} Total:{total}")
    print("=" * 55)


if __name__ == '__main__':
    main()
