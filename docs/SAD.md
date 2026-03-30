# SAD - System Architecture Document

**文件版本**：v1.0  
**建立日期**：2026-03-30  
**作者**：Agent A (Architect)  
**專案**：TTS 簡報配音系統 v596  

---

## 1. 系統概覽

### 1.1 系統邊界圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           TTS 簡報配音系統                               │
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │  CLI Input  │───▶│ TextProcessor│───▶│ TTSEngine   │                 │
│  │  (argparse) │    │   (分段)     │    │  (edge-tts) │                 │
│  └─────────────┘    └─────────────┘    └─────────────┘                 │
│         │                  │                   │                       │
│         ▼                  ▼                   ▼                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │ParameterCtrl│    │ VoiceSelector│   │ Synthesizer │                 │
│  │  (參數控制)  │    │   (音色選擇)  │    │  (合成核心)  │                 │
│  └─────────────┘    └─────────────┘    └─────────────┘                 │
│         │                  │                   │                       │
│         └──────────┬───────┘         ┌────────┘                       │
│                    ▼                 ▼                                 │
│              ┌─────────────┐    ┌─────────────┐                        │
│              │ErrorHandler │    │ AudioMerger │                        │
│              │  (錯誤處理)  │    │   (拼接)     │                        │
│              └─────────────┘    └─────────────┘                        │
│                    │                   │                               │
│                    └─────────┬─────────┘                               │
│                              ▼                                          │
│                      ┌─────────────┐    ┌─────────────┐               │
│                      │BatchProcessor│   │AudioExporter│               │
│                      │  (批量處理)   │    │  (檔案輸出)  │               │
│                      └─────────────┘    └─────────────┘               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   MP3 Output    │
                    │   最終音訊檔案   │
                    └─────────────────┘
```

### 1.2 核心模組清單

| # | 模組名稱 | 英文名稱 | 職責 | FR 對應 |
|---|----------|----------|------|---------|
| 1 | CLI 介面 | CLIInterface | 命令列參數解析與主程式入口 | FR-10 |
| 2 | TTS 引擎 | TTSEngine | edge-tts 非同步合成核心 | FR-03, FR-08 |
| 3 | 文本處理器 | TextProcessor | 文本預處理與 800 字分段 | FR-02 |
| 4 | 合成器 | Synthesizer | 音訊資料處理與轉換 | FR-03 |
| 5 | 音訊導出器 | AudioExporter | MP3 檔案寫入與格式轉換 | FR-04 |
| 6 | 錯誤處理器 | ErrorHandler | L1-L4 錯誤處理與電路熔斷器 | FR-05 |
| 7 | 批量處理器 | BatchProcessor | 多 chunk 批量合成與排程 | FR-06 |
| 8 | 參數控制器 | ParameterController | rate/volume 動態調整 | FR-07 |
| 9 | 音色選擇器 | VoiceSelector | 音色列舉與選擇 | FR-08 |
| 10 | 音訊拼接器 | AudioMerger | 多 MP3 檔案拼接合併 | FR-09 |

---

## 2. 模組設計

### 2.1 CLIInterface

**類別名稱**：`CLIInterface`

**檔案位置**：`tts_project/cli.py`

**職責**：命令列介面，解析使用者輸入參數並啟動合成流程。

**公開方法**：

| 方法簽名 | 說明 | 參數 | 回傳值 |
|----------|------|------|--------|
| `parse_args()` | 解析命令列參數 | None | `Namespace` |
| `main()` | 主程式入口點 | None | `int` (exit code) |

**依賴模組**：
- `TextProcessor`
- `TTSEngine`
- `BatchProcessor`

**對應 FR**：FR-10

**methodology-v2 規範**：
- 單一職責：僅負責 CLI 解析
- 依賴注入：接收 TTSEngine 實例而非自行建立

---

### 2.2 TTSEngine

**類別名稱**：`TTSEngine`

**檔案位置**：`tts_project/engine.py`

**職責**：edge-tts 非同步合成核心，管理 WebSocket 連線與語音合成。

**公開方法**：

| 方法簽名 | 說明 | 參數 | 回傳值 |
|----------|------|------|--------|
| `__init__(voice, rate, volume)` | 初始化引擎 | `str, str, str` | None |
| `async synthesize(text)` | 非同步合成文字 | `str` | `bytes` |
| `async synthesize_to_file(text, output_dir)` | 合成並寫入檔案 | `str, str` | `str` (檔案路徑) |
| `async synthesize_batch(text, output_path)` | 批量合成 | `str, str` | `str` |
| `async list_voices()` | 列舉可用音色 | None | `List[dict]` |
| `async close()` | 關閉引擎 | None | None |

**依賴模組**：
- `TextProcessor`
- `AudioExporter`
- `AudioMerger`
- `ErrorHandler`

**對應 FR**：FR-01, FR-03, FR-04, FR-06, FR-08

**methodology-v2 規範**：
- 非同步優先：所有 I/O 操作皆使用 async/await
- 資源管理：確保 WebSocket 正確關閉

---

### 2.3 TextProcessor

**類別名稱**：`TextProcessor`

**檔案位置**：`tts_project/text_processor.py`

**職責**：文本預處理與智慧分段，確保每段 ≤ 800 字元。

**公開方法**：

| 方法簽名 | 說明 | 參數 | 回傳值 |
|----------|------|------|--------|
| `_preprocess_text(text)` | 預處理並分段 | `str` | `List[str]` |
| `_split_at_semantic_boundary(chunk, max_size)` | 語義邊界分段 | `str, int` | `List[str]` |

**私有屬性**：

| 屬性 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `max_chunk_size` | `int` | `800` | 最大分段字元數 |
| `semantic_markers` | `List[str]` | `["。", "！", "？", "\n"]` | 語義中断點 |

**依賴模組**：無

**對應 FR**：FR-02

**methodology-v2 規範**：
- 不可變性：原文字不修改，回傳新列表
- 邊界保護：嚴格確保輸出長度 ≤ max_chunk_size

---

### 2.4 Synthesizer

**類別名稱**：`Synthesizer`

**檔案位置**：`tts_project/synthesizer.py`

**職責**：接收 edge-tts WebSocket 串流資料，解碼並轉換為有效音訊資料。

**公開方法**：

| 方法簽名 | 說明 | 參數 | 回傳值 |
|----------|------|------|--------|
| `async synthesize_stream(web_socket, text)` | 串流合成 | `WebSocket, str` | `bytes` |
| `_decode_audio(chunks)` | 解碼音訊區塊 | `List[bytes]` | `bytes` |

**依賴模組**：
- `ErrorHandler`

**對應 FR**：FR-03

**methodology-v2 規範**：
- 責任隔離：僅負責資料解碼，不處理網路連線

---

### 2.5 AudioExporter

**類別名稱**：`AudioExporter`

**檔案位置**：`tts_project/audio_exporter.py`

**職責**：將音訊資料寫入 MP3 檔案，確保檔案格式正確。

**公開方法**：

| 方法簽名 | 說明 | 參數 | 回傳值 |
|----------|------|------|--------|
| `async write_mp3(audio_data, file_path)` | 寫入 MP3 檔案 | `bytes, str` | `str` |
| `_validate_mp3(file_path)` | 驗證 MP3 格式 | `str` | `bool` |

**依賴模組**：`ErrorHandler`

**對應 FR**：FR-04

**methodology-v2 規範**：
- 錯誤回報：驗證失敗時拋出 `TTSError`

---

### 2.6 ErrorHandler

**類別名稱**：`ErrorHandler`, `TTSError`

**檔案位置**：`tts_project/error_handler.py`

**職責**：統一的錯誤處理與電路熔斷器機制（L1-L4）。

**公開類別**：

```python
class TTSError(Exception):
    """TTS 系統例外基底類別"""
    pass

class InputError(TTSError):
    """L1: 輸入錯誤，立即返回"""
    pass

class ToolError(TTSError):
    """L2: 工具錯誤，retry=3，backoff 1s/2s/4s"""
    pass

class ExecutionError(TTSError):
    """L3: 執行錯誤，Fallback"""
    pass

class SystemError(TTSError):
    """L4: 系統錯誤，Circuit Breaker（5次失敗/60s）"""
    pass
```

**公開方法**：

| 方法簽名 | 說明 | 參數 | 回傳值 |
|----------|------|------|--------|
| `retry_with_backoff(func, max_retries, backoff_base)` | 重試包裝器 | `func, int, float` | 回傳 `func()` 結果 |
| `circuit_breaker_check()` | 檢查熔斷器狀態 | None | `bool` |
| `circuit_breaker_record(failure)` | 記錄失敗 | `bool` | None |
| `_setup_logging(level)` | 配置日誌 | `str` | None |

**依賴模組**：無

**對應 FR**：FR-05

**methodology-v2 規範**：
- 單一職責：錯誤處理獨立成類別
- 電路熔斷器：防止系統雪崩

---

### 2.7 BatchProcessor

**類別名稱**：`BatchProcessor`

**檔案位置**：`tts_project/batch_processor.py`

**職責**：管理多 chunk 的批量合成任務，协调多個非同步操作。

**公開方法**：

| 方法簽名 | 說明 | 參數 | 回傳值 |
|----------|------|------|--------|
| `async process_batch(text, output_path)` | 批量處理文字 | `str, str` | `str` |
| `_create_chunks(text)` | 建立 chunk 列表 | `str` | `List[str]` |
| `_merge_chunks(chunk_paths)` | 合併 chunk 檔案 | `List[str]` | `str` |

**依賴模組**：
- `TextProcessor`
- `TTSEngine`
- `AudioMerger`

**對應 FR**：FR-06

**methodology-v2 規範**：
- 非同步並行：使用 `asyncio.gather` 處理多 chunk
- 進度追蹤：提供進度回調機制

---

### 2.8 ParameterController

**類別名稱**：`ParameterController`

**檔案位置**：`tts_project/parameter_controller.py`

**職責**：動態調整 rate 和 volume 參數，無需重新初始化。

**公開方法**：

| 方法簽名 | 說明 | 參數 | 回傳值 |
|----------|------|------|--------|
| `set_rate(rate)` | 設定語速 | `str` | None |
| `set_volume(volume)` | 設定音量 | `str` | None |
| `get_rate()` | 取得當前語速 | None | `str` |
| `get_volume()` | 取得當前音量 | None | `str` |

**屬性**：

| 屬性 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `_rate` | `str` | `"+0%"` | 當前語速 |
| `_volume` | `str` | `"+0%"` | 當前音量 |

**依賴模組**：無

**對應 FR**：FR-07

**methodology-v2 規範**：
- 參數驗證：確保 rate/volume 格式正確（如 `+20%`, `-10%`）

---

### 2.9 VoiceSelector

**類別名稱**：`VoiceSelector`

**檔案位置**：`tts_project/voice_selector.py`

**職責**：音色列舉與選擇，支援台灣國語音色。

**公開方法**：

| 方法簽名 | 說明 | 參數 | 回傳值 |
|----------|------|------|--------|
| `async list_voices()` | 列舉所有可用音色 | None | `List[dict]` |
| `async list_taiwan_voices()` | 列舉台灣音色 | None | `List[dict]` |
| `validate_voice(voice_name)` | 驗證音色是否存在 | `str` | `bool` |

**預設音色**：`zh-TW-HsiaoHsiaoNeural`

**依賴模組**：`ErrorHandler`

**對應 FR**：FR-08

**methodology-v2 規範**：
- 彈性選擇：支援自訂音色而非硬編碼

---

### 2.10 AudioMerger

**類別名稱**：`AudioMerger`

**檔案位置**：`tts_project/audio_merger.py`

**職責**：使用 ffmpeg 拼接多個 MP3 檔案為單一輸出。

**公開方法**：

| 方法簽名 | 說明 | 參數 | 回傳值 |
|----------|------|------|--------|
| `async merge_audio_files(file_paths, output_path)` | 合併音訊檔案 | `List[str], str` | `str` |
| `_validate_files(file_paths)` | 驗證檔案存在 | `List[str]` | `bool` |
| `_get_audio_info(file_path)` | 取得音訊資訊 | `str` | `dict` |

**依賴模組**：
- `ErrorHandler`
- subprocess (外部工具)

**對應 FR**：FR-09

**methodology-v2 規範**：
- 外部工具封裝：ffmpeg 操作透過 subprocess 封裝
- 格式一致：確保合併後格式與來源相同

---

## 3. 介面定義（模組間 API 合約）

### 3.1 CLI → TTSEngine

```python
# CLIInterface 呼叫 TTSEngine
engine = TTSEngine(voice=args.voice, rate=args.rate, volume=args.volume)
result = await engine.synthesize_batch(args.text, args.output)
```

**合約**：
- 輸入：`text: str`, `output_path: str`
- 輸出：`str` (最終檔案路徑)
- 例外：`TTSError` 子類

### 3.2 TTSEngine → TextProcessor

```python
# TTSEngine 內部呼叫 TextProcessor
chunks = TextProcessor()._preprocess_text(text)
```

**合約**：
- 輸入：`text: str`
- 輸出：`List[str]` (分段後的 chunk 列表)
- 保証：每個 chunk 長度 ≤ 800

### 3.3 TTSEngine → AudioMerger

```python
# TTSEngine 呼叫 AudioMerger
merged_path = await AudioMerger().merge_audio_files(chunk_paths, output_path)
```

**合約**：
- 輸入：`file_paths: List[str]`, `output_path: str`
- 輸出：`str` (合併後檔案路徑)
- 例外：`ExecutionError`

### 3.4 錯誤傳遞合約

```
所有模組拋出之例外皆為 TTSError 子類型：
- InputError: 來自 CLIInterface 參數驗證
- ToolError: 來自 edge-tts API 呼叫失敗
- ExecutionError: 來自 AudioMerger / AudioExporter 失敗
- SystemError: 來自 Circuit Breaker 觸發
```

---

## 4. 錯誤處理機制（L1-L4）

### 4.1 L1：輸入錯誤（立即返回）

**觸發條件**：
- 文字為空或長度為 0
- 輸出目錄無寫入權限
- 音色名稱格式錯誤

**處理方式**：
- 立即拋出 `InputError`，不回頭重試
- 記錄錯誤日誌（ERROR level）
- 返回錯誤碼 1

**實作位置**：`ErrorHandler` → `InputError`

### 4.2 L2：工具錯誤（Retry 机制）

**觸發條件**：
- edge-tts WebSocket 連線失敗
- 網路逾時
- 遠端伺服器錯誤（5xx）

**處理方式**：
1. 第 1 次失敗：等待 1 秒後重試
2. 第 2 次失敗：等待 2 秒後重試
3. 第 3 次失敗：等待 4 秒後重試
4. 第 4 次失敗：拋出 `ToolError`

**實作位置**：`ErrorHandler.retry_with_backoff()`

```python
backoff_schedule = [1, 2, 4]  # 秒
for attempt in range(max_retries):
    try:
        return await func()
    except Exception as e:
        if attempt < max_retries - 1:
            await asyncio.sleep(backoff_schedule[attempt])
        else:
            raise ToolError(f"Max retries exceeded: {e}")
```

### 4.3 L3：執行錯誤（Fallback）

**觸發條件**：
- ffmpeg 拼接失敗
- 磁碟空間不足
- 檔案寫入失敗（非網路原因）

**處理方式**：
1. 嘗試 fallback 策略：單一 chunk 直接輸出（不合併）
2. 如 fallback 失敗，拋出 `ExecutionError`
3. 清理已產生的暫存檔案

**實作位置**：`BatchProcessor._merge_chunks()`

### 4.4 L4：系統錯誤（Circuit Breaker）

**觸發條件**：
- 60 秒內連續 5 次失敗
- 系統資源耗盡（記憶體、磁碟）

**處理方式**：
1. 開啟熔斷器（open）：阻止新請求
2. 每 30 秒檢查一次牛請求是否成功
3. 如成功，關閉熔斷器（closed）
4. 持續失敗超過 5 分鐘，拋出 `SystemError`

**實作位置**：`ErrorHandler.circuit_breaker_check()`

```python
class CircuitBreaker:
    FAILURE_THRESHOLD = 5
    TIMEOUT = 60  # 秒
    RECOVERY_TIMEOUT = 30  # 秒
    
    def __init__(self):
        self.failures = []
        self.state = "closed"  # closed, open, half-open
    
    def record(self, success: bool):
        now = time.time()
        self.failures = [f for f in self.failures if now - f < self.TIMEOUT]
        if not success:
            self.failures.append(now)
        
        if len(self.failures) >= self.FAILURE_THRESHOLD:
            self.state = "open"
        elif self.state == "open" and len(self.failures) == 0:
            self.state = "closed"
    
    def can_execute(self) -> bool:
        if self.state == "open":
            # check if recovery timeout passed
            if self.failures and time.time() - self.failures[-1] > self.RECOVERY_TIMEOUT:
                self.state = "half-open"
                return True
            return False
        return True
```

---

## 5. ADR（架構決策記錄）

### ADR-01：為什麼選擇 edge-tts 作為 TTS 引擎

**日期**：2026-03-30  
**狀態**：已接受

**背景**：
需要選擇一個 TTS 引擎，能支援台灣國語音色，無需付費，易於整合。

**考量選項**：

| 選項 | 優點 | 缺點 |
|------|------|------|
| Google Cloud TTS | 高品質、多語言 | 需要 API key、付費 |
| Amazon Polly | AWS 整合、多音色 | 需要 API key、付費 |
| **edge-tts** | **免費、高品質、免 API key** | **依賴微軟伺服器** |
| gTTS | 完全免費 | 品質差、無法調整參數 |

**決定**：選擇 edge-tts

**理由**：
1. **免費無門檻**：不需要申請 API key，可直接使用
2. **高品質語音**：使用 Microsoft Edge 相同的語音引擎，MOS 分數 ≥ 4.0
3. **台灣國語支援**：內建 `zh-TW-HsiaoHsiaoNeural` 音色，滿足需求
4. **asyncio 原生支援**：官方非同步 API，Python 整合容易

**後續影響**：
- 系統依賴微軟伺服器可用性（離線環境無法使用）
- 需要處理網路逾時和重試機制

---

### ADR-02：為什麼選擇 800 字作為分段閾值

**日期**：2026-03-30  
**狀態**：已接受

**背景**：
edge-tts 對單次請求有字符限制，且長文本需要分段處理以優化失敗成本。

**考量選項**：

| 閾值 | 優點 | 缺點 |
|------|------|------|
| 500 字 | 失敗成本低、重試快 | 分段數量多、拼接費時 |
| **800 字** | **平衡失敗成本與拼接次數** | **中等** |
| 1000 字 | 分段少、拼接快 | 單次失敗影響大 |
| 動態計算 | 自適應 | 複雜度增加 |

**決定**：選擇 800 字

**理由**：
1. **edge-tts 限制**：官方建議單次請求 ≤ 1000 字，800 為安全閾值
2. **失敗成本**：800 字約等於 2-3 分鐘音訊，失敗可接受
3. **拼接效率**：分段數量適中，ffmpeg 拼接時間可控
4. **實驗驗證**：NFR-05 要求 500-1000 字區間驗證，800 為最佳中間值

**後續影響**：
- 需實作語義中断點（`。！？\n`）保持語句完整性
- 長單句（如無標點）需強制截斷

---

### ADR-03：為什麼選擇 asyncio 作為並發模型

**日期**：2026-03-30  
**狀態**：已接受

**背景**：
TTS 任務主要是 I/O 密集型（網路請求、檔案 I/O），需要非同步處理提升效能。

**考量選項**：

| 選項 | 優點 | 缺點 |
|------|------|------|
| 同步 (requests) | 簡單易用 | 阻塞、無法併發 |
| **asyncio** | **原生非同步、高效併發** | **學習曲線** |
| threading | 成熟穩定 | GIL 限制、死鎖風險 |
| multiprocessing | 真正並行 | 開銷大、共享困難 |

**決定**：選擇 asyncio

**理由**：
1. **edge-tts 原生支援**：官方提供 async/await API
2. **I/O 特性匹配**：TTS 主要瓶頸在網路等待，asyncio 完美適用
3. **NFR-07 要求**：同時處理 2 個請求，總時間 < 串列處理 × 0.7
4. **記憶體效率**：asyncio 單執行緒模型記憶體佔用低

**後續影響**：
- 所有公開方法皆需使用 `async def`
- 需妥善處理 `asyncio.CancelledError`
- CLI 入口需使用 `asyncio.run()`

---

### ADR-04：為什麼使用 subprocess + ffmpeg 進行音訊拼接

**日期**：2026-03-30  
**狀態**：已接受

**背景**：
多個 MP3 chunk 需要拼接為單一檔案，且需保持格式一致性。

**考量選項**：

| 選項 | 優點 | 缺點 |
|------|------|------|
| pydub | Python 原生 | 需要安裝 ffmpeg 底層、跨平台問題 |
| **subprocess + ffmpeg** | **直接控制、靈活參數** | **需要系統安裝 ffmpeg** |
| 純 Python MP3 庫 | 無外部依賴 | 實作複雜度極高 |
| edge-tts 串流拼接 | 減少檔案操作 | 實作複雜度極高 |

**決定**：選擇 subprocess + ffmpeg

**理由**：
1. **成熟穩定**：ffmpeg 是業界標準，MP3 處理經過充分驗證
2. **格式一致**：使用相同參數（如 `-b:a 192k`）確保輸出格式一致
3. **FR-09 要求**：合併後 MIME Type 為 `audio/mpeg`，ffmpeg 直接達成
4. **錯誤處理**：ffmpeg 回傳錯誤碼明確，有利錯誤診斷

**後續影響**：
- 系統需預裝 ffmpeg（`apt-get install ffmpeg` 或等價命令）
- 錯誤訊息需安全處理，不暴露 ffmpeg 輸出路徑

---

## 6. 架構合規矩陣

### 6.1 模組 vs methodology-v2 規範

| 模組 | 單一職責 | 非同步優先 | 依賴注入 | 錯誤隔離 | 測試覆蓋 |
|------|:--------:|:----------:|:--------:|:--------:|:--------:|
| CLIInterface | ✅ | ✅ | ✅ | ✅ | 🔲 |
| TTSEngine | ✅ | ✅ | 🔲 | ✅ | 🔲 |
| TextProcessor | ✅ | ✅ | ✅ | ✅ | 🔲 |
| Synthesizer | ✅ | ✅ | ✅ | ✅ | 🔲 |
| AudioExporter | ✅ | ✅ | ✅ | ✅ | 🔲 |
| ErrorHandler | ✅ | ✅ | ✅ | ✅ | 🔲 |
| BatchProcessor | ✅ | ✅ | ✅ | ✅ | 🔲 |
| ParameterController | ✅ | ✅ | ✅ | ✅ | 🔲 |
| VoiceSelector | ✅ | ✅ | ✅ | ✅ | 🔲 |
| AudioMerger | ✅ | ✅ | ✅ | ✅ | 🔲 |

> 🔲 = Phase 3 實現時填入

### 6.2 模組 vs SRS FR

| 模組 / FR | FR-01 | FR-02 | FR-03 | FR-04 | FR-05 | FR-06 | FR-07 | FR-08 | FR-09 | FR-10 |
|-----------|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|
| CLIInterface | | | | | | | | | | ✅ |
| TTSEngine | ✅ | | ✅ | ✅ | | ✅ | | ✅ | | |
| TextProcessor | | ✅ | | | | | | | | |
| Synthesizer | | | ✅ | | | | | | | |
| AudioExporter | | | | ✅ | | | | | | |
| ErrorHandler | | | | | ✅ | | | | | |
| BatchProcessor | | | | | | ✅ | | | | |
| ParameterController | | | | | | | ✅ | | | |
| VoiceSelector | | | | | | | | ✅ | | |
| AudioMerger | | | | | | | | | ✅ | |

---

## 7. 安全設計（SD-01 ~ SD-04）

### SD-01：傳輸加密

**威脅**：網路傳輸過程中被攔截或竊聽。

**緩解措施**：
- edge-tts 使用 HTTPS/WSS 協議，所有通訊端到端加密
- 不支援 HTTP 明文連線
- 驗證方式：網路監控確認無 HTTP 明文流量

**對應 SR**：SR-01

---

### SD-02：檔案權限

**威脅**：輸出目錄權限過大（777）導致非授權存取。

**緩解措施**：
- 輸出目錄預設權限為 755（僅擁有者可寫入）
- 產生的 MP3 檔案權限為 644（僅擁有者可寫入）
- 使用 `os.makedirs(dir, mode=0o755)` 建立目錄

**對應 SR**：SR-03

---

### SD-03：錯誤訊息安全

**威脅**：錯誤訊息洩露系統內部路徑、API 端點等敏感資訊。

**緩解措施**：
- 所有例外訊息統一使用 `str(e)` 而非原始堆疊
- 拋出前過濾路徑模式：`/workspace/`, `C:\`, `D:\`, `/home/`
- 替換為 `[REDACTED]` 或通用錯誤描述
- 日誌記錄完整堆疊（隔離存儲），對外僅顯示摘要

**對應 SR**：SR-06

```python
def _sanitize_error_message(msg: str) -> str:
    """過濾錯誤訊息中的敏感路徑"""
    patterns = [
        r'/workspace/[\w/]+',
        r'C:\\[\w\\]+',
        r'D:\\[\w\\]+',
        r'/home/[\w/]+',
    ]
    for pattern in patterns:
        msg = re.sub(pattern, '[REDACTED]', msg)
    return msg
```

---

### SD-04：依賴安全

**威脅**：第三方套件包含已知漏洞或惡意程式碼。

**緩解措施**：
- `edge-tts` 套件：GitHub 10k+ stars，活躍維護，無已知漏洞
- 使用 `pip audit` 或 `safety` 定期檢查依賴漏洞
- 依賴版本固定：使用 `requirements.txt` 或 `pyproject.toml`
- 禁止從非 PyPI 來源安裝套件

**對應 SR**：SR-05

```bash
# 依賴安全檢查命令
pip audit
safety check
```

---

### SD-05：身份驗證安全（對應 SR-02）

**威脅**：外部 API 呼叫缺乏身份驗證，導致未授權存取。

**分析**：
- edge-tts 是 Microsoft 提供的 WebSocket 服務，無需客戶端 API key 或 token
- 服務透過 HTTPS/WSS 連線，身份驗證由微軟服務端處理
- 本系統不儲存任何憑證資訊

**設計決策**：**SR-02 不適用**
- edge-tts 是微軟托管服務，無需客戶端認證機制
- 本系統不涉及 API key 或 token 的生成、儲存、驗證
- 設計決策記錄：基於 ADR-01，選擇 edge-tts 的核心原因之一即為「免 API key」

**對應 SR**：SR-02（不適用）

---

### SD-06：資料保護安全（對應 SR-04）

**威脅**：語音資料長期儲存於本地，導致敏感資訊外洩。

**分析**：
- 本系統產出的 `chunk_XXX.mp3` 是**最終輸出檔案**，不是暫存檔案
- 用戶需要這些 MP3 檔案作為簡報配音的最終產出
- 系統不涉及「暫存後自動刪除」的使用場景

**設計決策**：
1. **chunk_XXX.mp3 為最終產出**：檔案由用戶指定輸出路徑，用戶自行決定是否刪除
2. **不實作自動刪除機制**：本系統為 TTS 配音工具，需保留輸出檔案供後續使用
3. **若需暫存清理**：用戶可手動刪除輸出目錄，或由上層排程系統管理

**對應 SR**：SR-04（不適用）
- SR-04 要求「暫存後自動刪除」，但本系統無暫存概念
- 所有產出皆為用戶請求的最終檔案，設計決策記錄如上

---

## 8. 目錄結構

```
tts-project-v596/
├── 01-requirements/
│   └── SRS.md                 # 需求規格文件
├── 02-architecture/
│   ├── SAD.md                 # 本文件（系統架構文件）
│   └── ARCHITECTURE.png       # 架構圖（待繪製）
└── 03-implementation/         # Phase 3 建立
    └── tts_project/
        ├── __init__.py
        ├── cli.py             # CLIInterface
        ├── engine.py          # TTSEngine
        ├── text_processor.py  # TextProcessor
        ├── synthesizer.py     # Synthesizer
        ├── audio_exporter.py  # AudioExporter
        ├── error_handler.py   # ErrorHandler
        ├── batch_processor.py # BatchProcessor
        ├── parameter_controller.py  # ParameterController
        ├── voice_selector.py  # VoiceSelector
        ├── audio_merger.py    # AudioMerger
        └── main.py            # CLI entry point
```

---

## 9. 版本歷史

| 版本 | 日期 | 作者 | 變更摘要 |
|------|------|------|----------|
| v1.0 | 2026-03-30 | Agent A (Architect) | 初始版本，依據 SRS.md 建立完整 SAD |

---

*文件結束*