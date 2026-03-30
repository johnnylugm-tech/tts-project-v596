"""
TTS 引擎模組 (TTSEngine)

edge-tts 非同步合成核心，管理 WebSocket 連線與語音合成。

FR 對應：FR-01, FR-03, FR-08
"""

import asyncio
import os
from typing import List, Optional

from .text_processor import TextProcessor
from .synthesizer import Synthesizer
from .audio_exporter import AudioExporter
from .audio_merger import AudioMerger
from .parameter_controller import ParameterController
from .voice_selector import VoiceSelector
from .error_handler import ErrorHandler, TTSError, InputError


class TTSEngine:
    """
    TTS 合成引擎
    
    職責：
    - 協調所有子模組
    - 管理語音合成流程
    - 處理批量合成任務
    """
    
    def __init__(
        self,
        voice: str = None,
        rate: str = None,
        volume: str = None,
        error_handler: ErrorHandler = None
    ):
        """
        初始化 TTS 引擎
        
        參數：
            voice: 音色名稱（預設 zh-TW-HsiaoHsiaoNeural）
            rate: 語速調整（預設 +0%）
            volume: 音量調整（預設 +0%）
            error_handler: 錯誤處理器實例（可選）
        
        FR 對應：FR-01, FR-03, FR-08
        """
        self._voice = voice or VoiceSelector.get_default_voice()
        self._error_handler = error_handler or ErrorHandler()
        self._text_processor = TextProcessor()
        self._parameter_controller = ParameterController(rate=rate, volume=volume)
        self._synthesizer = Synthesizer(error_handler=self._error_handler)
        self._audio_exporter = AudioExporter(error_handler=self._error_handler)
        self._audio_merger = AudioMerger(error_handler=self._error_handler)
        self._voice_selector = VoiceSelector(error_handler=self._error_handler)
    
    @property
    def voice(self) -> str:
        """取得當前音色"""
        return self._voice
    
    @property
    def rate(self) -> str:
        """取得當前語速"""
        return self._parameter_controller.get_rate()
    
    @property
    def volume(self) -> str:
        """取得當前音量"""
        return self._parameter_controller.get_volume()
    
    def set_voice(self, voice: str) -> None:
        """設定音色"""
        self._voice = voice
    
    def set_rate(self, rate: str) -> None:
        """設定語速"""
        self._parameter_controller.set_rate(rate)
    
    def set_volume(self, volume: str) -> None:
        """設定音量"""
        self._parameter_controller.set_volume(volume)
    
    async def synthesize(self, text: str) -> bytes:
        """
        合成單一文字為音訊
        
        參數：
            text: 要合成的文字
        
        回傳：音訊資料（bytes）
        
        拋出：
            InputError：輸入無效
            TTSError：合成失敗
        
        FR 對應：FR-01, FR-03
        
        示例：
            >>> engine = TTSEngine()
            >>> audio = await engine.synthesize("你好，世界")
        """
        # 驗證輸入
        if not text or not text.strip():
            raise InputError("合成文字不能為空")
        
        # 電路熔斷器檢查
        if not await self._error_handler.circuit_breaker_check():
            raise TTSError("系統熔斷中，請稍後再試")
        
        try:
            audio_data = await self._synthesizer.synthesize_with_retry(
                text=text,
                voice=self._voice,
                rate=self.rate,
                volume=self.volume
            )
            
            # 記錄成功到電路熔斷器
            await self._error_handler.circuit_breaker_record(success=True)
            
            return audio_data
            
        except Exception as e:
            await self._error_handler.circuit_breaker_record(success=False)
            raise
    
    async def synthesize_to_file(self, text: str, output_dir: str) -> str:
        """
        合成並寫入檔案
        
        將單一文字合成為音訊並寫入檔案。
        
        參數：
            text: 要合成的文字
            output_dir: 輸出目錄
        
        回傳：輸出檔案路徑
        
        拋出：
            InputError：輸入無效
            ExecutionError：寫入失敗
        
        FR 對應：FR-01, FR-04
        """
        if not text or not text.strip():
            raise InputError("合成文字不能為空")
        
        if not output_dir:
            raise InputError("輸出目錄不能為空")
        
        # 電路熔斷器檢查
        if not await self._error_handler.circuit_breaker_check():
            raise TTSError("系統熔斷中，請稍後再試")
        
        try:
            # 合成音訊
            audio_data = await self._synthesizer.synthesize_with_retry(
                text=text,
                voice=self._voice,
                rate=self.rate,
                volume=self.volume
            )
            
            # 產生檔案名稱
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            file_name = f"tts_{text_hash}.mp3"
            file_path = os.path.join(output_dir, file_name)
            
            # 寫入檔案
            result_path = await self._audio_exporter.write_mp3(audio_data, file_path)
            
            # 記錄成功
            await self._error_handler.circuit_breaker_record(success=True)
            
            return result_path
            
        except Exception as e:
            await self._error_handler.circuit_breaker_record(success=False)
            raise
    
    async def synthesize_batch(self, text: str, output_path: str) -> str:
        """
        批量合成
        
        將長文字分段處理，最後合併為單一檔案。
        
        參數：
            text: 要合成的長文字
            output_path: 輸出檔案路徑
        
        回傳：最終輸出檔案路徑
        
        拋出：
            InputError：輸入無效
            ExecutionError：處理失敗
        
        FR 對應：FR-01, FR-03, FR-06, FR-09
        
        示例：
            >>> engine = TTSEngine()
            >>> result = await engine.synthesize_batch(
            ...     text="這是一段很長的文字，需要分段處理...",
            ...     output_path="output/final.mp3"
            ... )
        """
        if not text or not text.strip():
            raise InputError("合成文字不能為空")
        
        if not output_path:
            raise InputError("輸出路徑不能為空")
        
        # 電路熔斷器檢查
        if not await self._error_handler.circuit_breaker_check():
            raise TTSError("系統熔斷中，請稍後再試")
        
        # 分段處理
        chunks = self._text_processor._preprocess_text(text)
        
        if not chunks:
            raise InputError("無法分段文字")
        
        # 如果只有一個 chunk，直接合成
        if len(chunks) == 1:
            audio_data = await self._synthesizer.synthesize_with_retry(
                text=chunks[0],
                voice=self._voice,
                rate=self.rate,
                volume=self.volume
            )
            result = await self._audio_exporter.write_mp3(audio_data, output_path)
            await self._error_handler.circuit_breaker_record(success=True)
            return result
        
        # 多個 chunk：分別合成後合併
        try:
            chunk_paths = []
            
            # 確保輸出目錄存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, mode=0o755, exist_ok=True)
            
            # 分段合成（可優化為並行）
            for i, chunk in enumerate(chunks):
                try:
                    audio_data = await self._synthesizer.synthesize_with_retry(
                        text=chunk,
                        voice=self._voice,
                        rate=self.rate,
                        volume=self.volume
                    )
                    
                    chunk_file = os.path.join(output_dir, f"chunk_{i:04d}.mp3")
                    await self._audio_exporter.write_mp3(audio_data, chunk_file)
                    chunk_paths.append(chunk_file)
                    
                except Exception as e:
                    # 如果某個 chunk 失敗，嘗試 fallback
                    if len(chunk_paths) > 0:
                        # 返回已成功合併的部分
                        pass
                    raise
            
            # 合併所有 chunk
            result = await self._audio_merger.merge_audio_files(chunk_paths, output_path)
            
            # 清理 chunk 檔案（可選）
            for path in chunk_paths:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            
            # 記錄成功
            await self._error_handler.circuit_breaker_record(success=True)
            
            return result
            
        except Exception as e:
            await self._error_handler.circuit_breaker_record(success=False)
            raise
    
    async def list_voices(self) -> List[dict]:
        """
        列舉所有可用音色
        
        回傳：音色列表
        
        拋出：ToolError（edge-tts 呼叫失敗）
        
        FR 對應：FR-08
        """
        return await self._voice_selector.list_voices()
    
    async def list_taiwan_voices(self) -> List[dict]:
        """
        列舉台灣國語音色
        
        回傳：台灣國語音色列表
        
        拋出：ToolError（edge-tts 呼叫失敗）
        
        FR 對應：FR-08
        """
        return await self._voice_selector.list_taiwan_voices()
    
    async def validate_voice(self, voice_name: str) -> bool:
        """
        驗證音色是否存在
        
        參數：
            voice_name: 音色名稱
        
        回傳：True 表示存在
        
        拋出：ToolError（edge-tts 呼叫失敗）
        
        FR 對應：FR-08
        """
        return await self._voice_selector.validate_voice(voice_name)
    
    async def close(self) -> None:
        """
        關閉引擎，釋放資源
        
        FR 對應：FR-01
        """
        # 目前沒有需要關閉的資源
        # 預留擴展介面
        pass


def create_tts_engine(
    voice: str = None,
    rate: str = None,
    volume: str = None,
    error_handler: ErrorHandler = None
) -> TTSEngine:
    """
    建立 TTSEngine 實例
    
    參數：
        voice: 音色名稱
        rate: 語速
        volume: 音量
        error_handler: 錯誤處理器
    
    回傳：TTSEngine 實例
    """
    return TTSEngine(
        voice=voice,
        rate=rate,
        volume=volume,
        error_handler=error_handler
    )
