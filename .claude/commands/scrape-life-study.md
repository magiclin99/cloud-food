# 生命讀經擷取技巧

此 skill 記錄從 https://line.twgbr.org/life-study/ 擷取生命讀經的完整知識，包含網站結構、HTML 解析策略，以及已驗證可用的腳本。

---

## 網站結構

**Base URL:** `https://line.twgbr.org/life-study/`

| 層級 | URL 格式 | 說明 |
|------|----------|------|
| 主目錄 | `/index.html` | 66 卷書列表，`#nt` 錨點跳新約 |
| 書卷目錄 | `/{N}.html` | 列出所有篇次；**第 1 篇內容直接嵌入此頁** |
| 個別篇次 | `/{N}_{M}.html` | 第 2 篇起獨立頁面 |

- 書卷編號 N: 1（創世記）→ 66（啟示錄）
- 總計 66 卷、**2,058 篇**

---

## 取得書卷篇數的方法

頁面內嵌 JavaScript 物件，直接讀取最可靠：

```js
var bible = {
    ot_nt:         'ot',
    currBook:      1,
    numChapters:   120,   // ← 總篇數
    bookMP4Prefix: 'Gen',
    chapterPrefix: 'C',
    chapterSuffix: 'Gen', // ← 用於第 1 篇 anchor id
};
```

正規表達式：
```python
re.search(r'var bible\s*=\s*\{([^}]+)\}', html)
```

---

## HTML 結構重點

### 主容器
```html
<div id="verses">
  <div id="chapternav">…篇次連結…</div>   <!-- 只在書卷目錄頁 -->
  <div class="button">…上一篇/下一篇…</div>
  <h3 id="C2Gen">第二篇　標題 <button …/></h3>
  <center><audio id="player">…</audio></center>
  <div id="O1" class="O2">ａ 小節標題</div>
  <p class="calibre2">正文段落 <input class="styled" …>回報</p>
  …
  <div style="clear: both;"></div>   <!-- 正文結束標記 -->
</div>
```

### 第 1 篇的 anchor
- id 格式：`C1{chapterSuffix}`，例如 `C1Gen`、`C1Matt`
- 位於書卷目錄頁（`{N}.html`）內的 `<div id="verses">` 中

### 其他篇次的 anchor
- id 格式：`C{M}{chapterSuffix}`，例如 `C2Gen`、`C5Matt`

---

## 需要過濾的元素

| 選擇器 | 說明 |
|--------|------|
| `#chapternav` | 篇次導航列表（目錄頁才有） |
| `div.button` | 上一篇／下一篇／回目錄按鈕 |
| `center` | 音訊播放器容器 |
| `audio` | 音訊元素 |
| `input.styled` | 每段落末的「回報」按鈕 |
| `button[data-trigger="copy"]` | 複製連結按鈕 |
| `script, style` | 腳本與樣式 |
| `a > img` | 廣告圖片連結 |

---

## 小節標題轉換

```python
# div.O2 → h4、div.O3 → h5、div.O4 → h6
level_map = {'O2': 'h4', 'O3': 'h5', 'O4': 'h6'}
```

---

## 檔案命名規則

```
life-study/{NN}_{書名}_{MMM}.md
```

範例：`01_創世記_001.md`、`40_馬太福音_072.md`

---

## Frontmatter 格式

```markdown
---
book: 創世記
book_num: 1
message: 2
title: 第二篇　撒但的背叛與敗壞
source: https://line.twgbr.org/life-study/1_2.html
---
```

---

## 已驗證腳本

完整腳本位於：`scrape_life_study.py`

### 執行方式（由 Claude 主控）

```bash
# 依賴（使用 python3.11，系統 python3 為 externally-managed）
python3.11 -m pip install aiohttp beautifulsoup4 markdownify

# 試跑特定書卷
python3.11 scrape_life_study.py --books 1,40

# 全量執行（自動驗證）
python3.11 scrape_life_study.py

# 補跑失敗項目
python3.11 scrape_life_study.py --retry-failed

# 單獨驗證
python3.11 scrape_life_study.py --verify
```

### 重要實作細節

1. **並發控制**：`asyncio.Semaphore(20)` 限制同時連線數
2. **Manifest**：Phase 1 寫入 `life-study/manifest.json`，記錄每書卷篇數，供驗證使用
3. **第 1 篇特例**：直接重用 Phase 1 已抓的 index HTML，不重複請求
4. **Retry**：每個 URL 最多 3 次，指數退避
5. **Skip**：`.md` 已存在時跳過，`--force` 可強制覆蓋
6. **python 版本**：macOS 系統 python3 是 externally-managed，用 `python3.11` 執行

---

## 書卷對照表

| N | 書名 | N | 書名 |
|---|------|---|------|
| 1 | 創世記 | 40 | 馬太福音 |
| 2 | 出埃及記 | 41 | 馬可福音 |
| 3 | 利未記 | 42 | 路加福音 |
| 4 | 民數記 | 43 | 約翰福音 |
| 5 | 申命記 | 44 | 使徒行傳 |
| 6 | 約書亞記 | 45 | 羅馬書 |
| 7 | 士師記 | 46 | 哥林多前書 |
| 8 | 路得記 | 47 | 哥林多後書 |
| 9 | 撒母耳記上 | 48 | 加拉太書 |
| 10 | 撒母耳記下 | 49 | 以弗所書 |
| 11 | 列王紀上 | 50 | 腓立比書 |
| 12 | 列王紀下 | 51 | 歌羅西書 |
| 13 | 歷代志上 | 52 | 帖撒羅尼迦前書 |
| 14 | 歷代志下 | 53 | 帖撒羅尼迦後書 |
| 15 | 以斯拉記 | 54 | 提摩太前書 |
| 16 | 尼希米記 | 55 | 提摩太後書 |
| 17 | 以斯帖記 | 56 | 提多書 |
| 18 | 約伯記 | 57 | 腓利門書 |
| 19 | 詩篇 | 58 | 希伯來書 |
| 20 | 箴言 | 59 | 雅各書 |
| 21 | 傳道書 | 60 | 彼得前書 |
| 22 | 雅歌 | 61 | 彼得後書 |
| 23 | 以賽亞書 | 62 | 約翰一書 |
| 24 | 耶利米書 | 63 | 約翰二書 |
| 25 | 耶利米哀歌 | 64 | 約翰三書 |
| 26 | 以西結書 | 65 | 猶大書 |
| 27 | 但以理書 | 66 | 啟示錄 |
| 28–39 | 小先知書 | | |
