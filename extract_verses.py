"""
extract_verses.py
擷取 Bible20240820.sqlite 所有經節，輸出 Markdown 至 ./verses/{書卷簡稱}/
"""

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

DB_PATH = Path("db/Bible20240820.sqlite")
OUT_DIR = Path("verses")
SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def superscript(n: int) -> str:
    return str(n).translate(SUP)


def insert_superscripts(text: str, note_locs: list[tuple[int, int]]) -> str:
    """note_locs: [(note_loc, note_num), ...]，note_loc 1-indexed，插在該字元之前"""
    chars = list(text)
    for loc, num in sorted(note_locs, key=lambda x: -x[0]):
        insert_pos = loc - 1
        if 0 <= insert_pos <= len(chars):
            chars.insert(insert_pos, superscript(num))
    return "".join(chars)


def format_footnote_content(raw: str) -> list[str]:
    """將 ˍ 分段的註解內容拆成段落清單"""
    paragraphs = [p.strip() for p in raw.replace("\r", "").split("ˍ")]
    return [p for p in paragraphs if p]


def build_markdown(abbr: str, section: int, segment: int,
                   verse_text: str, footnotes: list[tuple[int, str]]) -> str:
    lines = []
    lines.append(f"# {abbr} {section}:{segment}")
    lines.append("")
    lines.append(f"> {verse_text}")

    if footnotes:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 註解")
        for num, content in footnotes:
            lines.append("")
            lines.append(f"**註{num}**")
            lines.append("")
            for para in format_footnote_content(content):
                lines.append(para)
                lines.append("")

    return "\n".join(lines)


def load_all_data(con: sqlite3.Connection) -> tuple[dict, dict, dict]:
    """一次性讀入全部資料，避免逐節查詢"""

    # 書卷簡稱：chapter_code → abbr
    abbr_map = {}
    for chapter_code, abbr in con.execute(
        "SELECT chapter_code, REPLACE(abbreviation,'\"','') FROM volume_all_big5_01"
    ):
        abbr_map[chapter_code] = abbr

    # 經文：(book, chapter, verse, unit) → content
    verses: dict[tuple, list] = defaultdict(list)
    for book, ch, seg, unit, content in con.execute(
        "SELECT chapter_code, section_code, segment_code, unit_code, content "
        "FROM verse_all_final_big5_06 ORDER BY chapter_code, section_code, segment_code, unit_code"
    ):
        verses[(book, ch, seg)].append((unit, content))

    # 註解：(book, chapter, verse) → [(note_loc, note_num, note_content), ...]
    footnotes: dict[tuple, list] = defaultdict(list)
    for book, ch, seg, note_loc, note_num, content in con.execute(
        "SELECT chapter_code, section_code, segment_code, note_loc, note_num, note_content "
        "FROM footnote_all_big5_09 ORDER BY chapter_code, section_code, segment_code, note_num"
    ):
        footnotes[(book, ch, seg)].append((note_loc, note_num, content))

    return abbr_map, verses, footnotes


def main():
    con = sqlite3.connect(DB_PATH)

    print("載入資料中…")
    abbr_map, verses, footnotes = load_all_data(con)
    con.close()

    total = len(verses)
    print(f"共 {total} 節，開始輸出…")

    done = 0
    skipped = 0

    for (book, chapter, verse_num), units in sorted(verses.keys().__iter__() if False else verses.items()):
        abbr = abbr_map.get(book, f"B{book:02d}")

        # segment_code=0 是詩篇章首標題，跳過（不產生獨立檔案）
        if verse_num == 0:
            skipped += 1
            continue

        # 合併多 unit（詩歌分行）
        units_sorted = sorted(units, key=lambda x: x[0])
        verse_text = "".join(content for _, content in units_sorted)

        # 插入上標
        note_locs_for_verse = [
            (loc, num) for loc, num, _ in footnotes.get((book, chapter, verse_num), [])
        ]
        verse_annotated = insert_superscripts(verse_text, note_locs_for_verse)

        # 整理註解 [(note_num, content)]
        footnote_list = [
            (num, content)
            for _, num, content in footnotes.get((book, chapter, verse_num), [])
        ]

        # 輸出
        md_content = build_markdown(abbr, chapter, verse_num, verse_annotated, footnote_list)

        book_dir = OUT_DIR / abbr
        book_dir.mkdir(parents=True, exist_ok=True)
        filename = book_dir / f"{abbr}_{chapter:02d}_{verse_num:02d}.md"
        filename.write_text(md_content, encoding="utf-8")

        done += 1
        if done % 1000 == 0:
            print(f"  {done}/{total - skipped} 節完成…")

    print(f"完成！輸出 {done} 個檔案，略過 {skipped} 個標題節。")
    print(f"目錄：{OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
