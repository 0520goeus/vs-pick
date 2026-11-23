#!/usr/bin/env python3
"""가전·생필품 VS 비교 사전 (0520goeus/vs-pick) — 구매 직전 'A vs B' 검색어 45+페이지 자동 생성기."""
from __future__ import annotations

import html
import itertools
import json
import math
import shutil
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)

SITE_NAME = "가성비 VS 비교 사전"
SITE_URL = "https://0520goeus.github.io/vs-pick"
INDEXNOW_KEY = "b81e5409d12a4f389c71e305a92014c8"
GOOGLE_FILE = "google873809343766a3b6.html"
ADSENSE_CLIENT = "ca-pub-8749404731911210"
COUPANG_TRACKING = "AF9170267"
COUPANG_WIDGET_ID = 1049499

DISCLOSURE = "이 페이지는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
COUPANG_BOX = (
    '<section class="card shop">'
    f'<p class="disc">{DISCLOSURE}</p>'
    '<h3>⚡ 비교 품목 실시간 온라인 최저가·할인 확인</h3>'
    '<script src="https://ads-partners.coupang.com/g.js"></script>'
    f'<script>new PartnersCoupang.G({{"id":{COUPANG_WIDGET_ID},"template":"carousel",'
    f'"trackingCode":"{COUPANG_TRACKING}","width":"100%","height":"145","tsource":""}});</script>'
    "</section>"
)

TARIFF_NORMAL = [(200, 910, 120.0), (400, 1600, 214.6), (999999, 7300, 307.3)]
TARIFF_SUMMER = [(300, 910, 120.0), (450, 1600, 214.6), (999999, 7300, 307.3)]


def _ssl_ctx():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def fetch_json(url: str):
    req = Request(url, headers={"User-Agent": "VsPickBuilder/1.0"})
    with urlopen(req, timeout=20, context=_ssl_ctx()) as resp:
        return json.loads(resp.read().decode("utf-8"))


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def won(n) -> str:
    return f"{int(round(n)):,}원"


def calc_bill(kwh: float, month: int) -> int:
    tiers = TARIFF_SUMMER if month in (7, 8) else TARIFF_NORMAL
    base_fee, energy, prev = tiers[0][1], 0.0, 0.0
    for lim, bf, rate in tiers:
        if kwh > prev:
            base_fee = bf
            energy += (min(kwh, lim) - prev) * rate
            prev = lim
    sub = math.floor(base_fee + energy + 14.0 * kwh)
    vat = int(sub * 0.10 + 0.5)
    fund = math.floor(sub * 0.027 / 10) * 10
    return math.floor((sub + vat + fund) / 10) * 10


CSS = """
:root{--bg:#0b1020;--card:#141d35;--line:#263459;--ink:#f1f5f9;--sub:#94a3b8;--accent:#38d9a9;--warn:#ffb703;--red:#ff4d6d;--blue:#5b8cff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,"Apple SD Gothic Neo",sans-serif}
header{background:#080c18;border-bottom:1px solid var(--line);padding:16px 20px}
.wrap{max-width:940px;margin:0 auto;padding:0 18px}
header .wrap{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
header a{color:var(--sub);text-decoration:none;font-size:14px;font-weight:600}
header .brand{color:#fff;font-size:19px;font-weight:800}
nav{display:flex;gap:14px;flex-wrap:wrap}
main{padding:28px 0 60px;display:grid;gap:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px}
h1{font-size:27px;line-height:1.35;margin:0 0 10px}h2{font-size:20px;margin:0 0 14px}h3{font-size:17px;margin:0 0 10px}
.sub{color:var(--sub);margin:0 0 14px}
.vs-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:640px){.vs-grid{grid-template-columns:1fr}}
.box{background:#0e1528;border:2px solid var(--line);border-radius:14px;padding:20px;display:grid;gap:8px}
.box.win{border-color:var(--accent)}
.badge{display:inline-block;padding:3px 10px;border-radius:99px;font-size:12px;font-weight:800;background:rgba(56,217,169,.15);color:var(--accent);width:fit-content}
.big{font-size:30px;font-weight:800;color:#fff}
table{width:100%;border-collapse:collapse;font-size:14.5px}
th,td{padding:11px 12px;border-bottom:1px solid var(--line);text-align:right}
th:first-child,td:first-child{text-align:left}
thead th{background:#0e1528;color:var(--sub);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.tile{display:grid;gap:4px;padding:15px;border:1px solid var(--line);border-radius:12px;background:#0e1528;color:var(--ink);text-decoration:none}
.tile:hover{border-color:var(--accent)}
.tile b{font-size:15.5px}.tile small{color:var(--sub)}
.faq{background:#0e1528;padding:14px 16px;border-radius:10px;border-left:4px solid var(--accent);margin:10px 0}
.shop .disc{font-size:12.5px;color:var(--sub);margin:0 0 8px}
footer{border-top:1px solid var(--line);padding:24px 0 44px;color:var(--sub);font-size:13.5px}
footer a{color:var(--accent);text-decoration:none}
"""


def write_page(rel: str, title: str, desc: str, body: str, faq_list: list[tuple[str, str]] | None = None) -> str:
    canon = f"{SITE_URL}/" if rel == "index.html" else f"{SITE_URL}/{rel}"
    ld = ""
    if faq_list:
        ld_obj = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in faq_list
            ],
        }
        ld = f'<script type="application/ld+json">{json.dumps(ld_obj, ensure_ascii=False)}</script>'
    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canon}">
<link rel="stylesheet" href="{SITE_URL}/style.css">
{ld}
</head>
<body>
<header><div class="wrap">
  <a class="brand" href="{SITE_URL}/">⚡ {SITE_NAME}</a>
  <nav>
    <a href="{SITE_URL}/#appliances">가전 유지비 VS</a>
    <a href="{SITE_URL}/#groceries">생필품 최저가 VS</a>
    <a href="https://0520goeus.github.io/elec-calc/">전기세 얼마</a>
    <a href="https://0520goeus.github.io/price-note/">해뎐 가격노트</a>
    <a href="https://0520goeus.github.io/money-calc-kr/">실수령액 계산기</a>
  </nav>
</div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap">
  <p>패밀리 사이트: <a href="https://0520goeus.github.io/price-note/">해뎐 가격노트</a> · <a href="https://0520goeus.github.io/elec-calc/">전기세 얼마</a> · <a href="https://0520goeus.github.io/life-money-lab/">생활비 물가 연구소</a> · <a href="https://0520goeus.github.io/seller-margin-calc/">셀러 마진 계산기</a> · <a href="https://0520goeus.github.io/money-calc-kr/">연봉·금융 계산기</a> · <a href="https://lifefixnote-kr.blogspot.com/">생활해결 노트</a></p>
</div></footer>
</body></html>"""
    out = DIST / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return canon


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    (DIST / "style.css").write_text(CSS, encoding="utf-8")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    (DIST / GOOGLE_FILE).write_text(f"google-site-verification: {GOOGLE_FILE}", encoding="utf-8")
    (DIST / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8")
    (DIST / "ads.txt").write_text(f"google.com, {ADSENSE_CLIENT.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")

    apps_raw = fetch_json("https://raw.githubusercontent.com/0520goeus/elec-calc/main/appliances.json")
    base_250 = calc_bill(250, NOW.month)
    apps = {}
    for a in apps_raw:
        w = a["watts"][len(a["watts"]) // 2]
        duty = 0.65 if a.get("cycle") else 1.0
        kwh = round(w * a["hours"] * a["days"] * duty / 1000.0, 1)
        bill = max(0, calc_bill(250 + kwh, NOW.month) - base_250)
        apps[a["slug"]] = {**a, "w_mid": w, "kwh": kwh, "bill": bill}

    # High-buyer-intent appliance VS pairs (all within-category + popular cross-category pairs -> ~60 pairs!)
    by_cat: dict[str, list[str]] = {}
    for slug, a in apps.items():
        by_cat.setdefault(a["cat"], []).append(slug)
    pair_set: list[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for cat_slugs in by_cat.values():
        for s1, s2 in itertools.combinations(cat_slugs, 2):
            pair_set.append((s1, s2))
            seen_pairs.add((s1, s2))
            seen_pairs.add((s2, s1))
    extra_cross = [
        ("jeongiyo", "aircon-wall"), ("onsu-mat", "aircon-wall"), ("jeongi-heater", "aircon-stand"),
        ("jeseupgi", "geonjogi"), ("jeseupgi", "setakgi"), ("gaseupgi", "jeseupgi"),
        ("gaseupgi", "jeongiyo"), ("gaseupgi", "onsu-mat"), ("air-fryer", "siksegi"),
        ("induction", "siksegi"), ("induction", "geonjogi"), ("desktop-pc", "aircon-wall"),
        ("desktop-pc", "jeongi-heater"), ("desktop-pc", "jeongiyo"), ("hair-dryer", "jeongi-pot"),
        ("hair-dryer", "jeonja-range"), ("tv", "gonggi-cheongjeonggi"), ("seonpunggi", "gonggi-cheongjeonggi"),
        ("aircon-wall", "geonjogi"), ("idongsik-aircon", "jeseupgi"), ("radiator", "aircon-stand"),
    ]
    for s1, s2 in extra_cross:
        if (s1, s2) not in seen_pairs and s1 in apps and s2 in apps:
            pair_set.append((s1, s2))
            seen_pairs.add((s1, s2))
    app_pairs = pair_set

    urls: list[str] = []
    app_tiles: list[str] = []

    for s1, s2 in app_pairs:
        if s1 not in apps or s2 not in apps:
            continue
        a1, a2 = apps[s1], apps[s2]
        cheaper = a1 if a1["bill"] <= a2["bill"] else a2
        pricier = a2 if cheaper is a1 else a1
        diff_month = abs(a1["bill"] - a2["bill"])
        diff_season = diff_month * 4
        rel = f"vs/{s1}-vs-{s2}.html"
        title = f"{a1['name']} vs {a2['name']} 전기세·유지비 비교 — 한 달 {won(diff_month)} 차이!"
        desc = f"{a1['name']}({a1['w_mid']}W, 월 +{won(a1['bill'])})과 {a2['name']}({a2['w_mid']}W, 월 +{won(a2['bill'])})의 한전 누진제 전기요금·소비전력·4개월 유지비를 비교합니다."
        faqs = [
            (
                f"{a1['name']}과 {a2['name']} 중 전기세가 더 적게 나오는 것은?",
                f"{cheaper['name']}이(가) 월 약 +{won(cheaper['bill'])}으로 {pricier['name']}(월 +{won(pricier['bill'])})보다 한 달에 약 {won(diff_month)}, 4개월 시즌 기준 약 {won(diff_season)} 저렴합니다.",
            ),
            (
                f"{a1['name']} vs {a2['name']} 소비전력(W) 차이는 얼마인가요?",
                f"대표 소비전력 기준 {a1['name']}은 약 {a1['w_mid']:,}W, {a2['name']}은 약 {a2['w_mid']:,}W입니다.",
            ),
        ]
        body = f"""
        <section class="card">
          <span class="badge">한전 누진제 실계산 VS 리포트</span>
          <h1>{esc(a1['name'])} vs {esc(a2['name'])}, 한 달 전기세 얼마나 차이 날까?</h1>
          <p class="sub">평소 월 250kWh를 사용하는 가구가 두 가전을 각각 사용할 때 늘어나는 한 달 전기요금과 4개월 시즌 총유지비를 비교했습니다.</p>
          <div class="vs-grid">
            <div class="box {'win' if cheaper is a1 else ''}">
              <span class="badge">{'⚡ 전기세 절약 승자' if cheaper is a1 else '비교 대상 A'}</span>
              <h2>{esc(a1['name'])} <small style="color:var(--sub);font-size:14px">({esc(a1['aka'])})</small></h2>
              <div class="big">월 +{won(a1['bill'])}</div>
              <div class="sub">대표 {a1['w_mid']:,}W · 하루 {a1['hours']}시간 · 월 {a1['kwh']}kWh</div>
            </div>
            <div class="box {'win' if cheaper is a2 else ''}">
              <span class="badge">{'⚡ 전기세 절약 승자' if cheaper is a2 else '비교 대상 B'}</span>
              <h2>{esc(a2['name'])} <small style="color:var(--sub);font-size:14px">({esc(a2['aka'])})</small></h2>
              <div class="big">월 +{won(a2['bill'])}</div>
              <div class="sub">대표 {a2['w_mid']:,}W · 하루 {a2['hours']}시간 · 월 {a2['kwh']}kWh</div>
            </div>
          </div>
        </section>
        {COUPANG_BOX}
        <section class="card">
          <h2>항목별 1:1 상세 비교표</h2>
          <table>
            <thead><tr><th>비교 항목</th><th>{esc(a1['name'])}</th><th>{esc(a2['name'])}</th></tr></thead>
            <tbody>
              <tr><td>대표 소비전력 (W)</td><td>{a1['w_mid']:,}W</td><td>{a2['w_mid']:,}W</td></tr>
              <tr><td>기준 사용 시간</td><td>하루 {a1['hours']}시간 ({a1['days']}일)</td><td>하루 {a2['hours']}시간 ({a2['days']}일)</td></tr>
              <tr><td>월간 전력 소비량</td><td>{a1['kwh']} kWh</td><td>{a2['kwh']} kWh</td></tr>
              <tr><td><strong>월 추가 전기요금 (250kWh 가구)</strong></td><td><strong>+{won(a1['bill'])}</strong></td><td><strong>+{won(a2['bill'])}</strong></td></tr>
              <tr><td><strong>4개월(한 시즌) 누적 전기세</strong></td><td><strong>+{won(a1['bill']*4)}</strong></td><td><strong>+{won(a2['bill']*4)}</strong></td></tr>
            </tbody>
          </table>
          <p class="sub" style="margin-top:14px">💡 <strong>결론:</strong> 유지비 측면에서는 <strong>{esc(cheaper['name'])}</strong>을(를) 선택하면 4개월 동안 약 <strong>{won(diff_season)}</strong>의 전기요금을 아낄 수 있습니다. 내 사용 시간에 맞춘 정밀 계산은 <a href="https://0520goeus.github.io/elec-calc/a/{cheaper['slug']}/" style="color:var(--accent)">{esc(cheaper['name'])} 계산기</a>에서 확인하세요.</p>
        </section>
        <section class="card">
          <h2>자주 묻는 질문</h2>
          {"".join(f'<div class="faq"><strong>Q. {esc(q)}</strong><p class="sub" style="margin:6px 0 0">A. {esc(a)}</p></div>' for q, a in faqs)}
        </section>
        """
        urls.append(write_page(rel, title, desc, body, faqs))
        app_tiles.append(
            f'<a class="tile" href="{SITE_URL}/{rel}"><b>{esc(a1["name"])} vs {esc(a2["name"])}</b>'
            f'<small>월 {won(diff_month)} 차이 · 승자: {esc(cheaper["name"])} →</small></a>'
        )

    # Now build 22 Grocery Brand A vs Brand B comparison pages from live price-note data!
    ref = fetch_json("https://raw.githubusercontent.com/0520goeus/price-note/main/data/ref.json")
    goods_raw = fetch_json("https://raw.githubusercontent.com/0520goeus/price-note/main/data/goods.json")
    by_cls: dict[str, list[dict]] = {}
    for gid, g in goods_raw.items():
        h = g.get("history") or []
        if len(h) < 2:
            continue
        r = ref.get("goods", {}).get(gid, {})
        cls = (r.get("cls") or "").strip()
        name = (r.get("name") or "").strip()
        if not cls or not name or h[-1][4] < 15:
            continue
        by_cls.setdefault(cls, []).append({
            "id": gid,
            "name": name,
            "cls": cls,
            "cur": int(h[-1][1]),
            "min": int(h[-1][2]),
            "max": int(h[-1][3]),
            "n": int(h[-1][4]),
        })

    groc_tiles: list[str] = []
    for cls, g_list in sorted(by_cls.items(), key=lambda kv: -len(kv[1])):
        if len(g_list) < 2 or len(groc_tiles) >= 65:
            continue
        g_sorted = sorted(g_list, key=lambda x: -x["n"])
        sub_pairs = [(g_sorted[0], g_sorted[1])]
        if len(g_sorted) >= 3:
            sub_pairs.append((g_sorted[0], g_sorted[2]))
        for g1, g2 in sub_pairs:
            if len(groc_tiles) >= 65:
                break
            cheaper = g1 if g1["cur"] <= g2["cur"] else g2
            diff = abs(g1["cur"] - g2["cur"])
            rel = f"vs/g-{g1['id']}-vs-{g2['id']}.html"
            title = f"{g1['name']} vs {g2['name']} 가격 비교 ({cls}) — 평균가·최저가 어디가 더 쌀까?"
            desc = f"한국소비자원 전국 매장 실측 기준 {g1['name']}(평균 {won(g1['cur'])}, 최저 {won(g1['min'])})과 {g2['name']}(평균 {won(g2['cur'])}, 최저 {won(g2['min'])}) 가격을 1:1 비교합니다."
            faqs = [
                (
                    f"{g1['name']}과 {g2['name']} 중 전국 평균가가 더 저렴한 제품은?",
                    f"{cheaper['name']}이(가) 평균 {won(cheaper['cur'])}(최저 {won(cheaper['min'])})으로 약 {won(diff)} 더 저렴합니다.",
                )
            ]
            body = f"""
            <section class="card">
              <span class="badge">한국소비자원 전국 매장 실측 · {esc(cls)}</span>
              <h1>{esc(g1['name'])} vs {esc(g2['name'])} 가격 1:1 비교</h1>
              <p class="sub">전국 마트·슈퍼·편의점 실제 판매가 기준 두 인기 {esc(cls)} 제품의 평균가와 최저가를 비교했습니다.</p>
              <div class="vs-grid">
                <div class="box {'win' if cheaper is g1 else ''}">
                  <span class="badge">{'🛒 가성비 우위' if cheaper is g1 else '비교 제품 A'}</span>
                  <h2>{esc(g1['name'])}</h2>
                  <div class="big">평균 {won(g1['cur'])}</div>
                  <div class="sub">전국 최저 {won(g1['min'])} ~ 최고 {won(g1['max'])} ({g1['n']}개 매장)</div>
                </div>
                <div class="box {'win' if cheaper is g2 else ''}">
                  <span class="badge">{'🛒 가성비 우위' if cheaper is g2 else '비교 제품 B'}</span>
                  <h2>{esc(g2['name'])}</h2>
                  <div class="big">평균 {won(g2['cur'])}</div>
                  <div class="sub">전국 최저 {won(g2['min'])} ~ 최고 {won(g2['max'])} ({g2['n']}개 매장)</div>
                </div>
              </div>
            </section>
            {COUPANG_BOX}
            <section class="card">
              <h2>전국 매장 가격 상세 비교표</h2>
              <table>
                <thead><tr><th>항목</th><th>{esc(g1['name'])}</th><th>{esc(g2['name'])}</th></tr></thead>
                <tbody>
                  <tr><td>전국 평균 판매가</td><td><strong>{won(g1['cur'])}</strong></td><td><strong>{won(g2['cur'])}</strong></td></tr>
                  <tr><td>전국 최저 매장가</td><td style="color:var(--accent)">{won(g1['min'])}</td><td style="color:var(--accent)">{won(g2['min'])}</td></tr>
                  <tr><td>전국 최고 매장가</td><td>{won(g1['max'])}</td><td>{won(g2['max'])}</td></tr>
                  <tr><td>매장 간 최대 가격차</td><td>{won(g1['max']-g1['min'])}</td><td>{won(g2['max']-g2['min'])}</td></tr>
                </tbody>
              </table>
              <p class="sub" style="margin-top:14px">👉 주간 가격 변동 그래프: <a href="https://0520goeus.github.io/price-note/p/{g1['id']}.html" style="color:var(--accent)">{esc(g1['name'])}</a> · <a href="https://0520goeus.github.io/price-note/p/{g2['id']}.html" style="color:var(--accent)">{esc(g2['name'])}</a></p>
            </section>
            """
            urls.append(write_page(rel, title, desc, body, faqs))
            groc_tiles.append(
                f'<a class="tile" href="{SITE_URL}/{rel}"><b>{esc(g1["name"][:14])} vs {esc(g2["name"][:14])}</b>'
                f'<small>{esc(cls)} · 평균 {won(diff)} 차이 →</small></a>'
            )

    # Homepage
    home_body = f"""
    <section class="card">
      <span class="badge">구매 직전 필수 체크 · 총 {len(urls)}개 1:1 실측 비교</span>
      <h1>가전 전기세 & 생필품 최저가 1:1 VS 비교 사전</h1>
      <p class="sub">살까 말까 고민되는 두 제품의 한전 누진제 전기요금과 한국소비자원 전국 매장 실제 가격을 1:1로 비교해 가장 돈 아끼는 선택을 알려드립니다.</p>
    </section>
    {COUPANG_BOX}
    <section class="card" id="appliances">
      <h2>⚡ 가전제품 전기세·유지비 1:1 대결 ({len(app_tiles)}종)</h2>
      <div class="grid">{"".join(app_tiles)}</div>
    </section>
    <section class="card" id="groceries">
      <h2>🛒 인기 생필품 브랜드 가격 1:1 대결 ({len(groc_tiles)}종)</h2>
      <div class="grid">{"".join(groc_tiles)}</div>
    </section>
    """
    urls.insert(0, write_page(
        "index.html",
        f"{SITE_NAME} | 전기요 vs 온수매트·가전 전기세·생필품 가격 1:1 비교",
        f"가전 24종 전기요금 1:1 비교와 한국소비자원 생필품 브랜드별 최저가 비교 사전 ({len(urls)+1}개 비교 페이지).",
        home_body,
    ))

    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc><lastmod>{NOW.strftime('%Y-%m-%d')}</lastmod></url>\n" for u in urls)
        + "</urlset>\n",
        encoding="utf-8",
    )
    (DIST / "urls.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")
    print(f"가성비 VS 비교 사전 빌드 완료: 총 {len(urls)}페이지")


if __name__ == "__main__":
    main()
