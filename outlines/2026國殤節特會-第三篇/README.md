# 二〇二六年國殤節國際相調特會 第三篇 — 綱要附經文

總題：**極其需要新的復興**
第三篇：**為着新的復興之神人的生活**

## 內容

本資料夾將原始信息綱要（`E26DLC03zht.pdf`）中每一項所引用的經節索引，
逐節展開，把恢復本聖經**經文本文**完整列在對應綱要項目下面，成為
一份「綱要附經文」，並排版為 PDF。

| 檔案 | 說明 |
|------|------|
| `E26DLC03zht-綱要附經文.pdf`  | 成品 PDF（繁體、A4、直向、明體排版） |
| `E26DLC03zht-綱要附經文.html` | PDF 的原始 HTML |
| `outline_data.py` | 綱要文字＋每項展開後的經節座標（書卷、章、節） |
| `build.py` | 產生器：讀取 `verses/` 經文庫、驗證引用、輸出 HTML |

- 經文取自 `verses/{書卷}/{書卷}_{章}_{節}.md`，僅取經文本文（已去除註解上標）。
- 共引用 **204 個經節**，全部驗證可解析。

## 重新產生

```bash
python3 build.py          # 產生 outline.html
# 再用 Chromium 印成 PDF：
/opt/pw-browsers/chromium-1194/chrome-linux/chrome \
  --headless --no-sandbox --print-to-pdf=outline.pdf \
  --no-pdf-header-footer "file://$PWD/outline.html"
```
