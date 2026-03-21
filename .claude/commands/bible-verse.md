# 聖經經節擷取技巧

此 skill 記錄從 `db/Bible20240820.sqlite` 擷取中文聖經經節（恢復本）的完整知識，包含資料庫結構、查詢邏輯、上標插入演算法，以及 Markdown 輸出格式。

---

## 資料庫位置

```
db/Bible20240820.sqlite
```

---

## 地址系統（四碼座標）

所有表格共用同一套欄位組合來定位經文位置：

| 欄位 | 意義 | 備註 |
|------|------|------|
| `chapter_code` | 書卷代碼 | 1=創世記 … 66=啟示錄 |
| `section_code` | 章 | 從 1 起算 |
| `segment_code` | 節 | 從 1 起算；0 為詩篇章首標題 |
| `unit_code` | 子節段 | 0=整節；1,2…=詩歌體分行 |

---

## 重要資料表

| 表格 | 內容 |
|------|------|
| `volume_all_big5_01` | 書卷列表（繁體），含簡稱 |
| `verse_all_final_big5_06` | 繁體經文本文 |
| `verse_all_final_gb_26` | 簡體經文本文 |
| `footnote_all_big5_09` | 繁體完整註解內文 |
| `footnote_all_gb_27` | 簡體完整註解內文 |
| `foot_all_big5_11` | 繁體串珠（交叉參考） |
| `foot_all_gb_28` | 簡體串珠（交叉參考） |

---

## 1. 讀取經文本文

**表格：** `verse_all_final_big5_06`

```sql
SELECT unit_code, content
FROM verse_all_final_big5_06
WHERE chapter_code = :book
  AND section_code = :chapter
  AND segment_code = :verse
ORDER BY unit_code;
```

- `unit_code = 0`：整節一行，直接使用
- `unit_code = 1, 2, …`：詩歌體分行，需按順序合併：

```python
units = sorted(rows, key=lambda x: x[0])  # 依 unit_code 排序
verse_text = "".join(content for _, content in units)
```

- `segment_code = 0` 僅出現於詩篇（book 19），為章首標題，通常跳過

---

## 2. 讀取註解（腳注）

**表格：** `footnote_all_big5_09`

```sql
SELECT note_loc, note_num, note_content
FROM footnote_all_big5_09
WHERE chapter_code = :book
  AND section_code = :chapter
  AND segment_code = :verse
ORDER BY note_num;
```

| 欄位 | 意義 |
|------|------|
| `note_loc` | 上標在經文字串中的插入位置（1-indexed） |
| `note_num` | 上標編號（1, 2, 3 …） |
| `note_content` | 完整註解文字，以 `ˍ` 分隔段落 |

### 上標插入規則

`note_loc` 為 **1-indexed**，上標插在該位置字元**之前**：

```python
SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

def insert_superscripts(text: str, note_locs: list[tuple[int, int]]) -> str:
    """note_locs: [(note_loc, note_num), ...]"""
    chars = list(text)
    # 從後往前插入，避免位置位移
    for loc, num in sorted(note_locs, key=lambda x: -x[0]):
        insert_pos = loc - 1
        if 0 <= insert_pos <= len(chars):
            chars.insert(insert_pos, str(num).translate(SUP))
    return "".join(chars)
```

範例 — 創 1:1：
- 經文：`起初神創造諸天與地，`
- note_locs：`[(1,1), (3,2), (4,3), (6,4)]`
- 結果：`¹起初²神³創造⁴諸天與地，`

### 解析段落

`ˍ` 是段落分隔符號：

```python
def parse_paragraphs(raw: str) -> list[str]:
    return [p.strip() for p in raw.replace("\r", "").split("ˍ") if p.strip()]
```

---

## 3. 讀取串珠（交叉參考）

**表格：** `foot_all_big5_11`

```sql
SELECT loc, beaded, beaded_content, note
FROM foot_all_big5_11
WHERE chapter_code = :book
  AND section_code = :chapter
  AND segment_code = :verse
ORDER BY loc;
```

| 欄位 | 意義 |
|------|------|
| `loc` | 串珠標記在經文中的字元位置（1-indexed，同 note_loc 規則） |
| `beaded` | 標籤（"a", "b", "c" …） |
| `beaded_content` | 參考經節清單，例如 `"亞十二1，詩三三6"` |
| `note` | 附加說明（多為空或 `^M`，可忽略） |

---

## 4. 書卷簡稱查詢

```sql
SELECT REPLACE(abbreviation, '"', '') AS abbr, chapter_sum
FROM volume_all_big5_01
WHERE chapter_code = :book;
```

---

## Markdown 輸出格式

### 檔名規則

```
verses/{書卷簡稱}/{書卷簡稱}_{章:02d}_{節:02d}.md
```

| 情境 | 檔名 |
|------|------|
| 創世記 1:1 | `verses/創/創_01_01.md` |
| 羅馬書 8:28 | `verses/羅/羅_08_28.md` |
| 詩篇 119:105 | `verses/詩/詩_119_105.md` |

章與節均補零（`02d`）確保字典序與聖經順序一致。

### 檔案內容結構

```markdown
# {書卷簡稱} {章}:{節}

> {含上標的經文}

---

## 註解

**註1**

{段落一}

{段落二}

**註2**

{段落一}
```

- 無註解的經節：省略 `---` 與 `## 註解` 區塊
- 多 unit 詩歌節：先合併再插入上標

---

## 批量擷取腳本

完整腳本位於：`extract_verses.py`

```bash
python3 extract_verses.py
```

**效能設計：**
1. **一次性批量查詢**：全部 verse + footnote 各讀一次存入 `defaultdict`，避免逐節查詢（31,103 節僅 2 條 SQL）
2. **從後往前插入上標**：排序反轉後插入，保持原始字元 index 不失效

**產出：**
- 31,103 個 `.md` 檔案（略過詩篇 116 個章首標題）
- 依書卷分 66 個子目錄

---

## 快速查詢範例（Python）

```python
import sqlite3
from collections import defaultdict

con = sqlite3.connect("db/Bible20240820.sqlite")

# 單節查詢 — 創 1:1
book, ch, seg = 1, 1, 1

verse = "".join(
    c for _, c in sorted(
        con.execute(
            "SELECT unit_code, content FROM verse_all_final_big5_06 "
            "WHERE chapter_code=? AND section_code=? AND segment_code=? ORDER BY unit_code",
            (book, ch, seg)
        ).fetchall()
    )
)

notes = con.execute(
    "SELECT note_loc, note_num, note_content FROM footnote_all_big5_09 "
    "WHERE chapter_code=? AND section_code=? AND segment_code=? ORDER BY note_num",
    (book, ch, seg)
).fetchall()

# 插入上標
SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
chars = list(verse)
for loc, num, _ in sorted(notes, key=lambda x: -x[0]):
    chars.insert(loc - 1, str(num).translate(SUP))
print("".join(chars))
# → ¹起初²神³創造⁴諸天與地，
```
