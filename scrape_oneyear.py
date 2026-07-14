"""
Scrape the one-year Bible reading plan from:
  https://line.twgbr.org/recoveryversion/oneyear/

Two tracks:
  NT: n001.html – n365.html
  OT: o001.html – o365.html

Output: data/oneyear_plan.json
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import date, timedelta

BASE = "https://line.twgbr.org/recoveryversion/oneyear/"
CA = "/root/.ccr/ca-bundle.crt"
OUT = Path("/home/user/cloud-food/data/oneyear_plan.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.verify = CA

# ── Chinese numeral → integer ──────────────────────────────────────────────
_ONES = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
         "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

def cn2int(s: str) -> int:
    """Convert Chinese chapter number string (from 一 to 一百五十) to int."""
    s = s.strip()
    if not s:
        return 0
    # Handle hundreds: 一百…
    hundreds = 0
    if "百" in s:
        idx = s.index("百")
        h_part = s[:idx]
        hundreds = _ONES.get(h_part, 1) * 100
        s = s[idx + 1:]
        if s.startswith("零"):
            s = s[1:]
    # Handle tens
    tens = 0
    if "十" in s:
        idx = s.index("十")
        t_part = s[:idx]
        tens = _ONES.get(t_part, 1) * 10
        s = s[idx + 1:]
    # Handle ones
    ones = _ONES.get(s, 0) if s else 0
    return hundreds + tens + ones


def _title_book(soup) -> str:
    t = soup.title.string if soup.title else ""
    # Format: "读经一年一遍第001天-马太福音"
    m = re.search(r"[-–](.+)$", t)
    return m.group(1).strip() if m else ""


def parse_page(html: str, prev_chapter: int = None):
    """
    Parse one day's page HTML.

    Returns dict:
      book, start_ch, start_v, end_ch, end_v, key_verse, tomorrow_hint
    prev_chapter: the chapter number we were in at the end of the previous day
                  (used when the page starts mid-chapter with no chapter header).
    """
    soup = BeautifulSoup(html, "html.parser")
    book = _title_book(soup)

    # Walk all <b> and <sup> in document order
    # <b>第X章</b>  → chapter header
    # <sup>N</sup> without <a> child → verse number
    current_ch = prev_chapter  # may be None
    first_pos = None   # (ch, v)
    last_pos = None    # (ch, v)

    for elem in soup.find_all(["b", "sup"]):
        if elem.name == "b":
            t = elem.get_text(strip=True)
            m = re.match(r"^第(.+?)[章篇]$", t)
            if m:
                ch = cn2int(m.group(1))
                if ch > 0:
                    current_ch = ch
        elif elem.name == "sup" and not elem.find("a"):
            v_text = elem.get_text(strip=True).strip()
            if v_text.isdigit() and current_ch is not None:
                v = int(v_text)
                if v == 0:  # Psalm titles are verse 0; skip for range tracking
                    continue
                pos = (current_ch, v)
                if first_pos is None:
                    first_pos = pos
                last_pos = pos

    # Key verse and tomorrow hint (in <b> tags)
    key_verse = ""
    tomorrow_hint = ""
    for b in soup.find_all("b"):
        t = b.get_text(strip=True)
        if t.startswith("重点经节") or t.startswith("重點經節"):
            key_verse = t
        elif t.startswith("明天:") or t.startswith("明天："):
            tomorrow_hint = t

    return {
        "book": book,
        "start_ch": first_pos[0] if first_pos else None,
        "start_v": first_pos[1] if first_pos else None,
        "end_ch": last_pos[0] if last_pos else None,
        "end_v": last_pos[1] if last_pos else None,
        "key_verse": key_verse,
        "tomorrow_hint": tomorrow_hint,
        "_end_chapter": last_pos[0] if last_pos else prev_chapter,
    }


def fetch(url: str, retries: int = 4) -> str:
    delay = 2
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=20)
            r.encoding = "utf-8"
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print(f"  Error {url}: {e}")
        if attempt < retries - 1:
            time.sleep(delay)
            delay *= 2
    return ""


def scrape_track(prefix: str, label: str, year: int = 2026):
    """Scrape one track (NT or OT) and return list of 365 dicts."""
    results = []
    current_chapter = None
    start_date = date(year, 1, 1)

    for day in range(1, 366):
        url = f"{BASE}{prefix}{day:03d}.html"
        d = start_date + timedelta(days=day - 1)
        print(f"  [{label}] Day {day:3d} {d}  {url}")

        html = fetch(url)
        if not html:
            print(f"    !! FAILED to fetch day {day}")
            results.append({
                "day": day,
                "date": str(d),
                "track": label,
                "book": None,
                "start_ch": None,
                "start_v": None,
                "end_ch": None,
                "end_v": None,
                "range": None,
                "key_verse": "",
                "tomorrow_hint": "",
            })
            continue

        info = parse_page(html, prev_chapter=current_chapter)
        current_chapter = info["_end_chapter"]

        # Format range string
        sc, sv = info["start_ch"], info["start_v"]
        ec, ev = info["end_ch"], info["end_v"]
        if sc and sv and ec and ev:
            if sc == ec:
                range_str = f"{info['book']} {sc}:{sv}-{ev}"
            else:
                range_str = f"{info['book']} {sc}:{sv}-{ec}:{ev}"
        else:
            range_str = None

        results.append({
            "day": day,
            "date": str(d),
            "track": label,
            "book": info["book"],
            "start_ch": sc,
            "start_v": sv,
            "end_ch": ec,
            "end_v": ev,
            "range": range_str,
            "key_verse": info["key_verse"],
            "tomorrow_hint": info["tomorrow_hint"],
        })

        # small polite delay
        time.sleep(0.1)

    return results


def main():
    print("Scraping NT track (n001–n365)…")
    nt = scrape_track("n", "NT")

    print()
    print("Scraping OT track (o001–o365)…")
    ot = scrape_track("o", "OT")

    # Merge by day
    plan = {}
    for rec in nt:
        day = rec["day"]
        plan[day] = {"day": day, "date": rec["date"], "nt": rec, "ot": None}
    for rec in ot:
        day = rec["day"]
        if day in plan:
            plan[day]["ot"] = rec
        else:
            plan[day] = {"day": day, "date": rec["date"], "nt": None, "ot": rec}

    output = [plan[d] for d in sorted(plan.keys())]
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\nSaved {len(output)} days → {OUT}")

    # Quick sanity check
    print("\nSample entries:")
    for d in [1, 32, 60, 100, 200, 300, 365]:
        entry = plan.get(d, {})
        nt_r = entry.get("nt", {}) or {}
        ot_r = entry.get("ot", {}) or {}
        print(f"  Day {d:3d}: NT={nt_r.get('range','?')}  OT={ot_r.get('range','?')}")


if __name__ == "__main__":
    main()
