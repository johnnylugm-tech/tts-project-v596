# SRS - TTS 簡報配音系統

**文件版本**：v1.0  
**建立日期**：2026-03-29  
**作者**：Agent A (Architect)

---

## 1. 需求概述

### 1.1 系統目標

本系統為基於 `edge-tts` 的高品質簡報配音引擎，專為 Python 環境設計，實現文字轉語音（Text-to-Speech）功能，支援台灣國語音色，具備非同步處理、批量文本分段、MP3 檔案輸出等核心能力。

### 1.2 核心價值

| 價值主張 | 說明 |
|----------|------|
| **免費** | 無需 API key，直接使用微軟 Edge TTS 技術 |
| **高品質** | 自然、韻律、親切的台灣國語語音 |
| **高效率** | asyncio 非同步架構，支援串流輸出 |
| **易整合** | CLI 介面，可嵌入任何 Python 專案 |

### 1.3 目標用戶

- 簡報製作者（需要配音旁白）
- 影片創作者（需要文字轉語音）
- 開發者（需要 TTS 引擎整合）

---

## 2. 功能需求（FR-01 ~ FR-10）

### FR-01：PresentationTTS 初始化

| 項目 | 內容 |
|------|------|
| **FR 編號** | FR-01 |
| **需求描述** | PresentationTTS 類別支援初始化參數：voice（音色名稱）、rate（語速）、volume（音量） |
| **實作函數** | `__init__(self, voice: str, rate: str, volume: str)` |
| **邏輯驗證方法** | 建構成功後，`self.voice == voice`、`self.rate == rate`、`self.volume == volume` 皆為 True |

---

### FR-02：文本預處理與分段

| 項目 | 內容 |
|------|------|
| **FR 編號** | FR-02 |
| **需求描述** | 文本預處理模組，實現自動分段功能：max_chunk_size=800 字元，語義中断點為 `。！？\n` |
| **實作函數** | `_preprocess_text(self, text: str) -> List[str]` |
| **邏輯驗證方法** | 輸出列表中所有分段字元數 ≤ 800，且分段輸出總字符數 = 輸入字符數（不含空白） |

---

### FR-03：非同步語音合成

| 項目 | 內容 |
|------|------|
| **FR 編號** | FR-03 |
| **需求描述** | 使用 asyncio 非同步框架 + WebSocket 協議進行語音合成，具備 retry=3 失敗重試機制 |
| **實作函數** | `async def synthesize(self, text: str) -> bytes` |
| **邏輯驗證方法** | 觸發網路錯誤後，retry 3 次皆失敗，回傳 `TTSError` 例外；正常情況回傳有效 MP3 位元組 |

---

### FR-04：MP3 檔案輸出

| 項目 | 內容 |
|------|------|
| **FR 編號** | FR-04 |
| **需求描述** | 合成後的音訊以 MP3 格式輸出，檔案命名為 `chunk_XXX.mp3`（XXX 為 3 位數序號） |
| **實作函數** | `async def synthesize_to_file(self, text: str, output_dir: str) -> str` |
| **邏輯驗證方法** | 產出檔案存在（`os.path.exists` 回傳 True）且檔案大小 > 0 位元組，且檔案格式為有效 MP3 |

---

### FR-05：錯誤處理與日誌

| 項目 | 內容 |
|------|------|
| **FR 編號** | FR-05 |
| **需求描述** | 系統具備統一的錯誤處理與日誌機制，使用 `logging.basicConfig` 配置日誌輸出 |
| **實作函數** | `def _setup_logging(self)` + 自訂 `TTSError` 例外類別 |
| **邏輯驗證方法** | 觸發錯誤時，日誌檔案中包含 Error Level 記錄，且訊息內容與錯誤原因相符 |

---

### FR-06：批量文本處理

| 項目 | 內容 |
|------|------|
| **FR 編號** | FR-06 |
| **需求描述** | 支援批量文本處理，自動呼叫 FR-02 分段功能，逐一合成後合併輸出 |
| **實作函數** | `async def synthesize_batch(self, text: str, output_path: str) -> str` |
| **邏輯驗證方法** | 輸入 N 字元文本，分段後合併字符數 = 原始字符數（誤差 ±1 個空白），產出單一 MP3 檔案 |

---

### FR-07：參數化控制

| 項目 | 內容 |
|------|------|
| **FR 編號** | FR-07 |
| **需求描述** | 支援即時調整 rate（語速）和 volume（音量）參數，不需重新初始化類別 |
| **實作函數** | `def set_rate(self, rate: str)` + `def set_volume(self, volume: str)` |
| **邏輯驗證方法** | 呼叫 `set_rate("+20%")` 後，`self.rate == "+20%"` 為 True；參數傳遞至 edge-tts API 後語速改變 |

---

### FR-08：台灣音色

| 項目 | 內容 |
|------|------|
| **FR 編號** | FR-08 |
| **需求描述** | 預設音色為 `zh-TW-HsiaoHsiaoNeural`（台灣國語女聲），並支援列舉可用音色 |
| **實作函數** | `async def list_voices(self) -> List[dict]` + 預設音色驗證 |
| **邏輯驗證方法** | `voice` 參數預設值等於 `"zh-TW-HsiaoHsiaoNeural"`；列舉音色包含 `zh-TW` 前綴的音色 ≥ 1 個 |

---

### FR-09：拼接後音訊格式一致

| 項目 | 內容 |
|------|------|
| **FR 編號** | FR-09 |
| **需求描述** | 多個 chunk 拼接後的最終音訊格式，與單一 chunk 输出的格式完全一致（MP3、相同位元率） |
| **實作函數** | `async def merge_audio_files(self, file_paths: List[str], output_path: str)` |
| **邏輯驗證方法** | 單一檔案與合併檔案的 MIME Type 均為 `audio/mpeg`，且檔案大小比例合理（合併 ≈ 各檔案總和） |

---

### FR-10：CLI 介面

| 項目 | 內容 |
|------|------|
| **FR 編號** | FR-10 |
| **需求描述** | 支援命令列執行，提供 `--text`、`--voice`、`--rate`、`--volume`、`--output` 等參數 |
| **實作函數** | `def main()` + `argparse.ArgumentParser` |
| **邏輯驗證方法** | 執行 `python -m tts_project --text "測試" --output ./test.mp3` 回傳成功（exit code 0），產出檔案有效 |

---

## 3. 非功能需求（NFR-01 ~ NFR-07）

| ID | 需求描述 | 量化目標 | 驗證方式 |
|----|----------|----------|----------|
| **NFR-01** | 語音品質 | 自然、韻律、親切（台灣國語） | 人工聆聽測試，MOS 分數 ≥ 4.0 |
| **NFR-02** | 回應速度 | WebSocket 串流，降低首位元組時間 | 首次音訊輸出時間 < 500ms（網路正常） |
| **NFR-03** | 穩定性 | 3 次 retry 機制 | 模擬網路失敗，確認重試 3 次後拋出例外 |
| **NFR-04** | 成本 | 免 API key | 無需註冊或付費即可使用 |
| **NFR-05** | 文本分段 | 500-1000 字，建議 800 | 分段測試：輸入 500/800/1000 字，分段正確 |
| **NFR-06** | Python 版本 | 3.8+ | `python --version` 回傳 ≥ 3.8 |
| **NFR-07** | 非同步架構 | asyncio 框架 | 同時處理 2 個請求，總時間 < 串列處理時間 × 0.7 |

---

## 4. 限制條件

| 限制項目 | 說明 |
|----------|------|
| **網路依賴** | edge-tts 依賴微軟伺服器，需要網路連線 |
| **字符限制** | 單次請求建議分段 ≤ 800 字元（edge-tts 限制） |
| **音色限制** | 音色選擇受限於 edge-tts 提供的音色清單 |
| **平台相容性** | 需 Python 3.8+、支援 asyncio 的作業系統 |

---

## 5. 術語表

| 術語 | 定義 |
|------|------|
| **TTS** | Text-to-Speech，文字轉語音技術 |
| **edge-tts** | 微軟 Edge 瀏覽器內建的 TTS 技術，基於 WebSocket 協議 |
| **chunk** | 文本分段，将长文本分割为多个小段以符合 API 限制 |
| **WebSocket** | 即時通訊協議，用於 edge-tts 的串流音訊傳輸 |
| **asyncio** | Python 異步框架，支援非同步 I/O 操作 |
| **MOS** | Mean Opinion Score，語音品質主觀評估指標 |
| **CLI** | Command Line Interface，命令列介面 |

---

## 6. Spec Logic Mapping

| FR ID | 需求描述 | 實作函數（預估）| 邏輯驗證方法 |
|--------|----------|----------------|-------------|
| FR-01 | PresentationTTS 初始化 | `__init__(voice, rate, volume)` | 屬性等於設定值 |
| FR-02 | 文本預處理與分段 | `_preprocess_text(text)` | 輸出≤800字，總字符數相等 |
| FR-03 | 非同步語音合成 | `synthesize(text)` | retry 3次後失敗回傳 error |
| FR-04 | MP3 檔案輸出 | `synthesize_to_file(text, output_dir)` | 檔案存在且大小 > 0 |
| FR-05 | 錯誤處理與日誌 | `_setup_logging()` + `TTSError` | 錯誤寫入日誌 |
| FR-06 | 批量文本處理 | `synthesize_batch(text, output_path)` | 分段合併字符數等於原始 |
| FR-07 | 參數化控制 | `set_rate(rate)` + `set_volume(volume)` | 參數傳遞正確 |
| FR-08 | 台灣音色 | `list_voices()` + 預設音色 | 音色名稱正確 |
| FR-09 | 拼接格式一致 | `merge_audio_files(file_paths, output_path)` | MIME Type 一致 |
| FR-10 | CLI 介面 | `main()` + `argparse` | exit code = 0 |

---

## 7. 版本管理與審查狀態（VR-01 ~ VR-04）

| ID | 需求描述 | 量化目標 | 驗證方式 |
|----|----------|----------|----------|
| **VR-01** | 版本控制 | 所有需求文件受 Git 版本控制，每次變更有 commit log | Git commit 存在 |
| **VR-02** | 審查狀態 | Phase 1 文件已通過 A/B 審查，具備雙方 session_id | Agent B APPROVE 記錄存在 |
| **VR-03** | 可追蹤性 | TRACEABILITY_MATRIX.md 每個需求 ID 已填入 | 矩陣無空白 ID |
| **VR-04** | 模組化依賴 | 所有模組依賴關係已定義，無循環依賴 | Dependency check passed |

---

## 8. 安全需求（SR-01 ~ SR-06）

| ID | 需求描述 | 量化目標 | 驗證方式 |
|----|----------|----------|----------|
| **SR-01** | 網路傳輸加密（encryption）| edge-tts 使用 HTTPS/WSS，無 HTTP 明文傳輸 | 網路監控驗證無 HTTP 明文 |
| **SR-02** | 身分驗證（authentication）| 外部 API 呼叫需有 API key 或 token 機制 | 確認憑證不硬編碼在原始碼 |
| **SR-03** | 存取授權（authorization）| 檔案輸出目錄需有存取權限控制 | 確認 output_dir 權限非 777 |
| **SR-04** | 資料保護（data protection）| 語音資料不本地長期儲存，暫存後自動刪除 | 確認暫存檔案存在時間 < 5 分鐘 |
| **SR-05** | 依賴安全 | edge-tts 為可信賴開源套件（GitHub 10k+ stars）| 檢查 pip show edge-tts 無已知漏洞 |
| **SR-06** | 錯誤訊息安全 | 錯誤訊息不洩露系統內部路徑或 API 端點 | 錯誤訊息不含 `/workspace/`、`C:\` 等路徑 |

---

## 9. 可維護性需求（MR-01 ~ MR-05）

| ID | 需求描述 | 量化目標 | 對應架構 |
|----|----------|----------|----------|
| **MR-01** | 模組化設計 | 每個 FR 對應獨立類別/模組，耦合度 ≤ 1 | PresentationTTS 類模組化 |
| **MR-02** | 錯誤處理隔離 | L1-L6 錯誤各有獨立處理分支，無交叉依賴 | TTSError 層次結構 |
| **MR-03** | 可測試性 | 每個公開方法都有對應單元測試，覆蓋率 ≥ 80% | pytest 測試框架 |
| **MR-04** | 可擴展音色 | 新增音色僅需修改 `voice` 參數，不改核心代碼 | VoiceSelector 參數化 |
| **MR-05** | 日誌可配置 | 日誌輸出層級/目標可透過參數調整，不硬編譯 | logging.basicConfig 動態 |

---

## 10. 衝突點記錄（Conflict Log）

| 日期 | 衝突項目 | 衝突描述 | 解決方案 | 狀態 |
|------|----------|----------|----------|------|
| - | 無 | 目前規格設計書與 methodology-v2 SKILL.md 無衝突 | N/A | N/A |

---

## 8. 附錄

### A. 驗證矩陣摘要

| 類別 | 數量 | 已定義驗證方法 |
|------|----------------|----------------|
| 功能需求（FR）| 10 | 10 (100%) |
| 非功能需求（NFR）| 7 | 7 (100%) |
| 安全需求（SR）| 4 | 4 (100%) |
| **總計** | **21** | **21 (100%)** |

### B. 參考文獻

- edge-tts 官方文檔：https://github.com/rany2/edge-tts
- Python asyncio 文檔：https://docs.python.org/3/library/asyncio.html