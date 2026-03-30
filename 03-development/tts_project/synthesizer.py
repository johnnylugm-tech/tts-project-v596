"""
合成器模組 (Synthesizer)

接收 edge-tts WebSocket 串流資料，解碼並轉換為有效音訊資料。

FR 對應：FR-03
"""

import asyncio
from typing import List, Optional

try:
    import edge_tts
except ImportError:
    edge_tts = None

from .error_handler import ErrorHandler, ToolError


class Synthesizer:
    """
    音訊合成器
    
    職責：
    - 接收 WebSocket 串流資料
    - 解碼音訊區塊
    - 轉換為有效音訊資料
    """
    
    def __init__(self, error_handler: ErrorHandler = None):
        """
        初始化合成器
        
        參數：
            error_handler: 錯誤處理器實例（可選）
        """
        self._error_handler = error_handler or ErrorHandler()
        self._chunks: List[bytes] = []
    
    async def synthesize_stream(self, text: str, voice: str, rate: str = "+0%", volume: str = "+0%") -> bytes:
        """
        串流合成文字為音訊
        
        使用 edge-tts 的非同步 API 進行合成，
        接收所有音訊區塊並合併為完整音訊資料。
        
        參數：
            text: 要合成為語音的文字
            voice: 音色名稱
            rate: 語速調整（格式：+20%、-10%、0%）
            volume: 音量調整（格式：+20%、-10%、0%）
        
        回傳：合併後的音訊資料（bytes）
        
        拋出：
            ToolError：edge-tts 呼叫失敗
            InputError：輸入文字為空
        
        FR 對應：FR-03
        
        示例：
            >>> synthesizer = Synthesizer()
            >>> audio_data = await synthesizer.synthesize_stream(
            ...     text="你好，歡迎使用 TTS 系統",
            ...     voice="zh-TW-HsiaoHsiaoNeural",
            ...     rate="+0%",
            ...     volume="+0%"
            ... )
        """
        if not text:
            raise ToolError("合成文字不能為空")
        
        if edge_tts is None:
            raise ToolError("edge-tts 套件未安裝，請執行：pip install edge-tts")
        
        try:
            # 建立通訊物件
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume
            )
            
            # 收集所有音訊區塊
            chunks = []
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            
            await communicate.close()
            
            # 合併音訊區塊
            audio_data = self._decode_audio(chunks)
            
            return audio_data
            
        except asyncio.CancelledError:
            raise ToolError("合成操作被取消")
        except Exception as e:
            sanitized = self._error_handler._sanitize_error_message(str(e))
            raise ToolError(f"音訊合成失敗：{sanitized}")
    
    def _decode_audio(self, chunks: List[bytes]) -> bytes:
        """
        解碼音訊區塊
        
        將多個音訊區塊合併為單一音訊資料。
        
        參數：
            chunks: 音訊區塊列表
        
        回傳：合併後的音訊資料
        
        FR 對應：FR-03
        """
        if not chunks:
            return b""
        
        # 直接拼接所有區塊（edge-tts 輸出為 MP3 格式，可直接拼接）
        return b"".join(chunks)
    
    async def synthesize_with_retry(
        self,
        text: str,
        voice: str,
        rate: str = "+0%",
        volume: str = "+0%",
        max_retries: int = 3
    ) -> bytes:
        """
        帶重試機制的串流合成
        
        失敗時使用 exponential backoff 重試。
        
        參數：
            text: 要合成為語音的文字
            voice: 音色名稱
            rate: 語速調整
            volume: 音量調整
            max_retries: 最大重試次數（預設 3）
        
        回傳：合併後的音訊資料
        
        拋出：ToolError（超過最大重試次數）
        
        FR 對應：FR-03, FR-05 (L2 重試)
        """
        return await self._error_handler.retry_with_backoff(
            self.synthesize_stream,
            max_retries=max_retries,
            backoff_base=1.0,
            text=text,
            voice=voice,
            rate=rate,
            volume=volume
        )
    
    def reset(self) -> None:
        """重置內部狀態"""
        self._chunks = []


# ============================================================================
# 快捷工廠函數
# ============================================================================

def create_synthesizer(error_handler: ErrorHandler = None) -> Synthesizer:
    """
    建立 Synthesizer 實例
    
    參數：
        error_handler: 錯誤處理器實例（可選）
    
    回傳：Synthesizer 實例
    """
    return Synthesizer(error_handler=error_handler)