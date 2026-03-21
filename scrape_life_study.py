#!/usr/bin/env python3
"""
生命讀經擷取腳本
平行抓取 https://line.twgbr.org/life-study/ 所有篇次，儲存為 .md 檔案

檔案命名: life-study/{NN}_{書名}_{MMM}.md
"""

import asyncio
import json
import os
import re
import sys
import argparse
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup, Tag
import markdownify

BASE_URL = "https://line.twgbr.org/life-study"
OUTPUT_DIR = Path("life-study")
MANIFEST_FILE = OUTPUT_DIR / "manifest.json"
FAILED_FILE = Path("failed_urls.txt")
CONCURRENCY = 20

BOOKS = {
    1: "創世記", 2: "出埃及記", 3: "利未記", 4: "民數記", 5: "申命記",
    6: "約書亞記", 7: "士師記", 8: "路得記", 9: "撒母耳記上", 10: "撒母耳記下",
    11: "列王紀上", 12: "列王紀下", 13: "歷代志上", 14: "歷代志下", 15: "以斯拉記",
    16: "尼希米記", 17: "以斯帖記", 18: "約伯記", 19: "詩篇", 20: "箴言",
    21: "傳道書", 22: "雅歌", 23: "以賽亞書", 24: "耶利米書", 25: "耶利米哀歌",
    26: "以西結書", 27: "但以理書", 28: "何西阿書", 29: "約珥書", 30: "阿摩司書",
    31: "俄巴底亞書", 32: "約拿書", 33: "彌迦書", 34: "那鴻書", 35: "哈巴谷書",
    36: "西番雅書", 37: "哈該書", 38: "撒迦利亞書", 39: "瑪拉基書",
    40: "馬太福音", 41: "馬可福音", 42: "路加福音", 43: "約翰福音", 44: "使徒行傳",
    45: "羅馬書", 46: "哥林多前書", 47: "哥林多後書", 48: "加拉太書", 49: "以弗所書",
    50: "腓立比書", 51: "歌羅西書", 52: "帖撒羅尼迦前書", 53: "帖撒羅尼迦後書",
    54: "提摩太前書", 55: "提摩太後書", 56: "提多書", 57: "腓利門書", 58: "希伯來書",
    59: "雅各書", 60: "彼得前書", 61: "彼得後書", 62: "約翰一書", 63: "約翰二書",
    64: "約翰三書", 65: "猶大書", 66: "啟示錄",
}


# ── HTML 解析 ────────────────────────────────────────────────

def parse_bible_js(html: str) -> dict:
    """從頁面 JS 中讀取 bible 物件（numChapters, chapterSuffix）"""
    m = re.search(r'var bible\s*=\s*\{([^}]+)\}', html, re.DOTALL)
    if not m:
        return {}
    block = m.group(1)
    result = {}
    for key, val in re.findall(r"(\w+)\s*:\s*['\"]?([^,'\"]+)['\"]?", block):
        result[key.strip()] = val.strip()
    return result


def clean_content(verses_div: Tag) -> str:
    """清理 verses div，移除非正文元素，回傳 markdown 文字"""
    # 移除章節導航 (篇次列表)
    for el in verses_div.select('#chapternav'):
        el.decompose()
    # 移除導航按鈕 (上一篇/下一篇/回目錄)
    for el in verses_div.select('div.button'):
        el.decompose()
    # 移除音訊播放器區塊
    for el in verses_div.select('center'):
        el.decompose()
    for el in verses_div.select('audio'):
        el.decompose()
    # 移除「回報」按鈕
    for el in verses_div.select('input.styled'):
        el.decompose()
    # 移除複製連結按鈕 (透明小按鈕)
    for el in verses_div.select('button[data-trigger="copy"]'):
        el.decompose()
    # 移除所有 script / style
    for el in verses_div.select('script, style'):
        el.decompose()
    # 移除廣告圖片連結
    for el in verses_div.select('a > img'):
        el.parent.decompose()

    # 將小節 div (class O2/O3/O4) 轉成 h4/h5/h6
    for el in verses_div.select('div[class^="O"]'):
        cls = el.get('class', [''])[0]
        level = {'O2': 'h4', 'O3': 'h5', 'O4': 'h6'}.get(cls, 'h4')
        new_tag = BeautifulSoup(f'<{level}></{level}>', 'html.parser').find(level)
        new_tag.string = el.get_text(strip=True)
        el.replace_with(new_tag)

    html_str = str(verses_div)
    md = markdownify.markdownify(html_str, heading_style='ATX', strip=['img', 'button'])
    # 清理多餘空行
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    return md


def extract_message(html: str, book_num: int, msg_num: int) -> tuple[str, str]:
    """
    解析頁面 HTML，回傳 (title, markdown_content)
    msg_num=1 時，從書卷目錄頁萃取第一篇
    """
    soup = BeautifulSoup(html, 'html.parser')
    bible_js = parse_bible_js(html)
    suffix = bible_js.get('chapterSuffix', '')

    verses = soup.find('div', id='verses')
    if not verses:
        return '', ''

    if msg_num == 1:
        # 第一篇嵌在目錄頁，用 anchor id 定位
        anchor_id = f'C1{suffix}' if suffix else None
        h3 = None
        if anchor_id:
            h3 = verses.find('h3', id=anchor_id)
        if not h3:
            # fallback: 找第一個 h3
            h3 = verses.find('h3')
        if not h3:
            return '', ''

        # 只保留從 h3 開始到 clear div 之前的內容
        # 建立一個臨時容器放這段內容
        wrapper = BeautifulSoup('<div></div>', 'html.parser').find('div')
        node = h3
        while node:
            next_node = node.next_sibling
            # 停止條件：clear div
            if isinstance(node, Tag):
                style = node.get('style', '')
                if 'clear' in style and 'both' in style:
                    break
            wrapper.append(node.__copy__() if hasattr(node, '__copy__') else node)
            node = next_node

        title_text = h3.get_text(strip=True)
        # 移除 h3 內的 button
        for btn in wrapper.select('button'):
            btn.decompose()
        md = clean_content(wrapper)
    else:
        # 個別篇次頁
        anchor_id = f'C{msg_num}{suffix}' if suffix else None
        h3 = None
        if anchor_id:
            h3 = verses.find('h3', id=anchor_id)
        if not h3:
            h3 = verses.find('h3')

        title_text = h3.get_text(strip=True) if h3 else f'第{msg_num}篇'
        md = clean_content(verses)

    return title_text, md


def make_filename(book_num: int, msg_num: int) -> Path:
    name = BOOKS.get(book_num, f'書卷{book_num}')
    return OUTPUT_DIR / f"{book_num:02d}_{name}_{msg_num:03d}.md"


def make_md_file(book_num: int, msg_num: int, title: str, content: str, url: str) -> str:
    name = BOOKS.get(book_num, f'書卷{book_num}')
    frontmatter = f"""---
book: {name}
book_num: {book_num}
message: {msg_num}
title: {title}
source: {url}
---

"""
    return frontmatter + content


# ── 網路請求 ─────────────────────────────────────────────────

async def fetch(session: aiohttp.ClientSession, url: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    return await resp.text(encoding='utf-8', errors='replace')
                print(f"  HTTP {resp.status}: {url}")
                return None
        except Exception as e:
            if attempt == retries - 1:
                print(f"  失敗({attempt+1}/{retries}): {url} — {e}")
                return None
            await asyncio.sleep(2 ** attempt)
    return None


# ── Phase 1：取得書卷資訊 ────────────────────────────────────

async def fetch_book_info(session: aiohttp.ClientSession, book_num: int) -> dict | None:
    """抓書卷目錄頁，取得總篇數與第一篇內容"""
    url = f"{BASE_URL}/{book_num}.html"
    html = await fetch(session, url)
    if not html:
        return None

    bible_js = parse_bible_js(html)
    total = int(bible_js.get('numChapters', 0))
    if not total:
        # fallback: 從連結推算
        links = re.findall(rf'href="{book_num}_(\d+)\.html"', html)
        total = max((int(x) for x in links), default=1) if links else 1

    return {
        'book_num': book_num,
        'name': BOOKS.get(book_num, f'書卷{book_num}'),
        'total': total,
        'index_html': html,
        'index_url': url,
    }


# ── Phase 3：抓取並儲存單篇 ──────────────────────────────────

async def scrape_message(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    book_num: int,
    msg_num: int,
    html: str | None,  # 已有 html（第一篇用目錄頁 html）
    force: bool,
    failed: list,
):
    filepath = make_filename(book_num, msg_num)
    if filepath.exists() and not force:
        return  # 跳過已存在

    if msg_num == 1:
        page_html = html
        url = f"{BASE_URL}/{book_num}.html"
    else:
        url = f"{BASE_URL}/{book_num}_{msg_num}.html"
        async with sem:
            page_html = await fetch(session, url)

    if not page_html:
        print(f"  ✗ 無法取得 {url}")
        failed.append(url)
        return

    title, content = extract_message(page_html, book_num, msg_num)
    if not content:
        print(f"  ✗ 內容解析失敗 {url}")
        failed.append(url)
        return

    md_text = make_md_file(book_num, msg_num, title, content, url)
    filepath.write_text(md_text, encoding='utf-8')


# ── 主流程 ────────────────────────────────────────────────────

async def run(book_nums: list[int], force: bool):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; LifeStudyScraper/1.0)'}

    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        # Phase 1：平行抓所有書卷目錄
        print(f"\n=== Phase 1：抓取 {len(book_nums)} 本書卷目錄 ===")
        sem = asyncio.Semaphore(CONCURRENCY)

        async def fetch_book_with_sem(n):
            async with sem:
                return await fetch_book_info(session, n)

        book_infos = await asyncio.gather(*[fetch_book_with_sem(n) for n in book_nums])
        book_infos = [b for b in book_infos if b]

        # 更新 manifest
        manifest = {}
        if MANIFEST_FILE.exists():
            manifest = json.loads(MANIFEST_FILE.read_text())
        for b in book_infos:
            manifest[str(b['book_num'])] = {'name': b['name'], 'total': b['total']}
        MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        print(f"  書卷資訊已寫入 manifest.json")

        total_msgs = sum(b['total'] for b in book_infos)
        print(f"  共 {len(book_infos)} 本書，{total_msgs} 篇")

        # Phase 2 & 3：建立任務並平行抓取
        print(f"\n=== Phase 2/3：平行擷取所有篇次 (concurrency={CONCURRENCY}) ===")
        failed: list[str] = []
        tasks = []
        for b in book_infos:
            for msg_num in range(1, b['total'] + 1):
                html_arg = b['index_html'] if msg_num == 1 else None
                tasks.append(scrape_message(
                    session, sem,
                    b['book_num'], msg_num, html_arg,
                    force, failed
                ))

        # 分批執行，每批顯示進度
        batch_size = 100
        done = 0
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            await asyncio.gather(*batch)
            done += len(batch)
            print(f"  進度: {done}/{len(tasks)}", end='\r')

        print(f"\n  完成 {len(tasks) - len(failed)}/{len(tasks)} 篇")

    if failed:
        FAILED_FILE.write_text('\n'.join(failed), encoding='utf-8')
        print(f"\n  {len(failed)} 個失敗，已記錄至 failed_urls.txt")
    elif FAILED_FILE.exists():
        FAILED_FILE.unlink()


async def run_retry_failed():
    if not FAILED_FILE.exists():
        print("failed_urls.txt 不存在")
        return
    urls = [u.strip() for u in FAILED_FILE.read_text().splitlines() if u.strip()]
    print(f"重試 {len(urls)} 個失敗 URL")

    # 解析 URL 取得 book_num / msg_num
    pattern = re.compile(r'/(\d+)(?:_(\d+))?\.html$')
    failed = []

    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; LifeStudyScraper/1.0)'}
    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = []
        for url in urls:
            m = pattern.search(url)
            if not m:
                continue
            book_num = int(m.group(1))
            msg_num = int(m.group(2)) if m.group(2) else 1
            tasks.append(scrape_message(session, sem, book_num, msg_num, None, True, failed))
        await asyncio.gather(*tasks)

    if failed:
        FAILED_FILE.write_text('\n'.join(failed))
        print(f"仍有 {len(failed)} 個失敗")
    else:
        FAILED_FILE.unlink(missing_ok=True)
        print("全部補齊！")


def run_verify(book_nums: list[int] | None = None):
    if not MANIFEST_FILE.exists():
        print("manifest.json 不存在，請先執行抓取")
        return
    manifest = json.loads(MANIFEST_FILE.read_text())
    all_ok = True
    for num_str, info in sorted(manifest.items(), key=lambda x: int(x[0])):
        n = int(num_str)
        if book_nums and n not in book_nums:
            continue
        name = info['name']
        expected = info['total']
        prefix = f"{n:02d}_{name}_"
        actual = len(list(OUTPUT_DIR.glob(f"{prefix}*.md")))
        status = '✓' if actual == expected else '✗'
        if actual != expected:
            all_ok = False
            # 找出缺少的篇次
            existing = set()
            for f in OUTPUT_DIR.glob(f"{prefix}*.md"):
                m = re.search(r'_(\d+)\.md$', f.name)
                if m:
                    existing.add(int(m.group(1)))
            missing = sorted(set(range(1, expected + 1)) - existing)
            print(f"  {status} {prefix:<25} 預期:{expected:>4}  實際:{actual:>4}  缺少: {missing[:10]}{'...' if len(missing)>10 else ''}")
        else:
            print(f"  {status} {prefix:<25} 預期:{expected:>4}  實際:{actual:>4}")
    if all_ok:
        print("\n全部驗證通過！")


# ── CLI ───────────────────────────────────────────────────────

def parse_books_arg(s: str) -> list[int]:
    result = []
    for part in s.split(','):
        part = part.strip()
        if '-' in part:
            a, b = part.split('-', 1)
            result.extend(range(int(a), int(b) + 1))
        else:
            result.append(int(part))
    return sorted(set(result))


def main():
    parser = argparse.ArgumentParser(description='生命讀經擷取工具')
    parser.add_argument('--books', help='指定書卷，如 1 或 40,41,42 或 1-5（預設全部）')
    parser.add_argument('--force', action='store_true', help='強制重新抓取（覆蓋已存在）')
    parser.add_argument('--verify', action='store_true', help='驗證模式（比對 manifest vs 實際檔案）')
    parser.add_argument('--retry-failed', action='store_true', help='重跑 failed_urls.txt 中的項目')
    args = parser.parse_args()

    if args.retry_failed:
        asyncio.run(run_retry_failed())
        return

    book_nums = parse_books_arg(args.books) if args.books else list(range(1, 67))

    if args.verify:
        run_verify(book_nums)
        return

    asyncio.run(run(book_nums, args.force))
    if not args.verify:
        print("\n=== 驗證 ===")
        run_verify(book_nums)


if __name__ == '__main__':
    main()
