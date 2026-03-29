# TRACEABILITY_MATRIX.md - 需求追蹤矩陣

**文件版本**：v1.0  
**建立日期**：2026-03-29  
**作者**：Agent A (Architect)

---

## 1. 四欄追蹤：FR → 設計 → 代碼 → 測試

### 1.1 Phase 1 完成狀態（功能需求）

| FR ID | 功能需求 | SAD 模組 | 代碼檔案 | 測試案例 | 狀態 |
|-------|----------|----------|----------|----------|------|
| FR-01 | PresentationTTS 初始化 | TTSEngine | - | - | ✅ 已規格化 |
| FR-02 | 文本預處理與分段 | TextProcessor | - | - | ✅ 已規格化 |
| FR-03 | 非同步語音合成 | Synthesizer | - | - | ✅ 已規格化 |
| FR-04 | MP3 檔案輸出 | AudioExporter | - | - | ✅ 已規格化 |
| FR-05 | 錯誤處理與日誌 | ErrorHandler | - | - | ✅ 已規格化 |
| FR-06 | 批量文本處理 | BatchProcessor | - | - | ✅ 已規格化 |
| FR-07 | 參數化控制 | ParameterController | - | - | ✅ 已規格化 |
| FR-08 | 台灣音色 | VoiceSelector | - | - | ✅ 已規格化 |
| FR-09 | 拼接格式一致 | AudioMerger | - | - | ✅ 已規格化 |
| FR-10 | CLI 介面 | CLIInterface | - | - | ✅ 已規格化 |

### 1.2 Phase 2 完成後更新（SAD 模組）

| FR ID | SAD 模組 | 模組責任 | 預計行數 |
|-------|----------|----------|----------|
| FR-01 | TTSEngine | TTS 引擎核心，封裝 edge-tts | ~50 |
| FR-02 | TextProcessor | 文本分段邏輯 | ~80 |
| FR-03 | Synthesizer | 非同步合成，retry 機制 | ~60 |
| FR-04 | AudioExporter | MP3 檔案寫入 | ~40 |
| FR-05 | ErrorHandler | 統一錯誤處理，日誌設定 | ~30 |
| FR-06 | BatchProcessor | 批量處理協調 | ~50 |
| FR-07 | ParameterController | rate/volume 參數控制 | ~30 |
| FR-08 | VoiceSelector | 音色列舉與選擇 | ~40 |
| FR-09 | AudioMerger | 音訊拼接 | ~60 |
| FR-10 | CLIInterface | 命令列介面 | ~50 |

### 1.3 Phase 3 完成後更新（代碼檔案）

（待 Phase 3 代碼實作完成後填寫）

### 1.4 Phase 4 完成後更新（測試案例）

（待 Phase 4 測試撰寫完成後填寫）

---

## 2. NFR 追蹤

| NFR ID | 非功能需求 | 量化目標 | 驗證方式 | 狀態 |
|--------|------------|----------|----------|------|
| NFR-01 | 語音品質 | MOS ≥ 4.0 | 人工聆聽測試 | ✅ 已規格化 |
| NFR-02 | 回應速度 | 首位元組 < 500ms | 效能測試 | ✅ 已規格化 |
| NFR-03 | 穩定性 | retry 3 次 | 單元測試 | ✅ 已規格化 |
| NFR-04 | 成本 | 免費 | 無 API key | ✅ 已規格化 |
| NFR-05 | 文本分段 | 500-1000 字 | 分段測試 | ✅ 已規格化 |
| NFR-06 | Python 版本 | ≥ 3.8 | 版本檢查 | ✅ 已規格化 |
| NFR-07 | 非同步架構 | 並發加速比 > 0.7 | 效能測試 | ✅ 已規格化 |

---

## 3. 依赖关系

### 3.1 FR 間依赖

```
FR-02 (文本分段) ──┐
                  ├──> FR-03 (語音合成) ──> FR-04 (檔案輸出)
FR-06 (批量處理) ──┘                        │
                  └──> FR-09 (音訊拼接) ──> FR-06 (最終輸出)
                  
FR-01 (初始化) ──> FR-07 (參數控制)
                  
FR-08 (音色) ──> FR-03 (音色傳遞)
```

### 3.2 模組間依赖

```
CLIInterface (FR-10)
    └──> TTSEngine (FR-01)
            ├──> TextProcessor (FR-02)
            ├──> Synthesizer (FR-03)
            ├──> AudioExporter (FR-04)
            ├──> ErrorHandler (FR-05)
            ├──> BatchProcessor (FR-06)
            ├──> ParameterController (FR-07)
            ├──> VoiceSelector (FR-08)
            └──> AudioMerger (FR-09)
```

---

## 4. 測試矩陣（規劃）

| 測試類型 | 測試目標 | 覆蓋 FR | 工具 |
|----------|----------|---------|------|
| 單元測試 | 各模組獨立功能 | FR-01~10 | pytest |
| 整合測試 | 端到端流程 | FR-06+10 | pytest + requests |
| 效能測試 | 並發、延遲 | NFR-02, NFR-07 | pytest-benchmark |
| 失敗注入測試 | retry 機制 | NFR-03 | pytest-mock |

---

## 5. 變更記錄

| 日期 | 版本 | 變更內容 | 作者 |
|------|------|----------|------|
| 2026-03-29 | v1.0 | 初始建立 | Agent A |