"""
批量處理器模組 (BatchProcessor)

管理多 chunk 的批量合成任務，协调多個非同步操作。

FR 對應：FR-06
"""

import asyncio
import os
from typing import List, Optional, Callable

from .text_processor import TextProcessor
from .tts_engine import TTSEngine
from .audio_merger import AudioMerger
from .error_handler import ErrorHandler, ExecutionError, SystemError


class BatchProcessor:
    """
    批量處理器
    
    職責：
    - 管理多 chunk 的批量合成任務
    - 協調非同步操作
    - 提供進度回調
    - 實作 fallback 策略
    """
    
    def __init__(
        self,
        tts_engine: TTSEngine,
        error_handler: ErrorHandler = None
    ):
        """
        初始化批量處理器
        
        參數：
            tts_engine: TTS 引擎實例
            error_handler: 錯誤處理器實例（可選）
        """
        self._tts_engine = tts_engine
        self._text_processor = TextProcessor()
        self._audio_merger = AudioMerger(error_handler=error_handler)
        self._error_handler = error_handler or ErrorHandler()
    
    def _create_chunks(self, text: str) -> List[str]:
        """
        建立 chunk 列表
        
        使用 TextProcessor 進行分段。
        
        參數：
            text: 原始文字
        
        回傳：分段後的 chunk 列表
        
        FR 對應：FR-06
        """
        return self._text_processor._preprocess_text(text)
    
    async def _synthesize_single_chunk(
        self,
        chunk: str,
        index: int,
        output_dir: str
    ) -> str:
        """
        合成單一 chunk
        
        參數：
            chunk: 要合成的文字
            index: chunk 索引
            output_dir: 輸出目錄
        
        回傳：產生的音訊檔案路徑
        """
        audio_data = await self._tts_engine.synthesize(chunk)
        file_path = os.path.join(output_dir, f"batch_chunk_{index:04d}.mp3")
        return await self._tts_engine._audio_exporter.write_mp3(audio_data, file_path)
    
    async def _merge_chunks(self, chunk_paths: List[str], output_path: str) -> str:
        """
        合併 chunk 檔案
        
        失敗時嘗試 fallback 策略（L3）。
        
        參數：
            chunk_paths: chunk 檔案路徑列表
            output_path: 輸出檔案路徑
        
        回傳：合併後的檔案路徑
        
        拋出：ExecutionError（fallback 也失敗）
        
        FR 對應：FR-06, FR-09 (L3 fallback)
        """
        try:
            return await self._audio_merger.merge_audio_files(chunk_paths, output_path)
        except Exception as e:
            # L3 Fallback：嘗試單一 chunk 直接輸出（不合併）
            if len(chunk_paths) == 1:
                # 複製單一 chunk 作為輸出
                import shutil
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, mode=0o755, exist_ok=True)
                shutil.copy2(chunk_paths[0], output_path)
                return output_path
            
            # 多個 chunk 且合併失敗，拋出 ExecutionError
            sanitized = self._error_handler._sanitize_error_message(str(e))
            raise ExecutionError(f"合併失敗，fallback 也失敗：{sanitized}")
    
    async def process_batch(
        self,
        text: str,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """
        批量處理文字
        
        將長文字分段後并行合成，最後合併為單一檔案。
        
        參數：
            text: 要處理的長文字
            output_path: 輸出檔案路徑
            progress_callback: 進度回調函數 (completed, total)
        
        回傳：最終輸出檔案路徑
        
        拋出：
            ExecutionError：處理失敗
            SystemError：電路熔斷觸發
        
        FR 對應：FR-06
        
        示例：
            >>> engine = TTSEngine()
            >>> processor = BatchProcessor(engine)
            >>> result = await processor.process_batch(
            ...     text="很長的文字內容...",
            ...     output_path="output/batch_result.mp3",
            ...     progress_callback=lambda done, total: print(f"{done}/{total}")
            ... )
        """
        # 驗證電路熔斷器
        if not await self._error_handler.circuit_breaker_check():
            raise SystemError("系統熔斷中，請稍後再試")
        
        # 分段
        chunks = self._create_chunks(text)
        
        if not chunks:
            raise ExecutionError("無法分段文字")
        
        total = len(chunks)
        
        # 確保輸出目錄存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, mode=0o755, exist_ok=True)
        
        chunk_paths = []
        completed = 0
        
        try:
            # 順序處理每個 chunk（可優化為並行）
            for i, chunk in enumerate(chunks):
                try:
                    path = await self._synthesize_single_chunk(chunk, i, output_dir)
                    chunk_paths.append(path)
                    completed += 1
                    
                    # 進度回調
                    if progress_callback:
                        progress_callback(completed, total)
                    
                    await self._error_handler.circuit_breaker_record(success=True)
                    
                except Exception as e:
                    # 某個 chunk 失敗
                    await self._error_handler.circuit_breaker_record(success=False)
                    sanitized = self._error_handler._sanitize_error_message(str(e))
                    raise ExecutionError(f"Chunk {i} 合成失敗：{sanitized}")
            
            # 合併
            result = await self._merge_chunks(chunk_paths, output_path)
            
            # 清理 chunk 檔案
            for path in chunk_paths:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            
            return result
            
        except Exception as e:
            # 清理已產生的 chunk 檔案
            for path in chunk_paths:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            raise
    
    async def process_batch_parallel(
        self,
        text: str,
        output_path: str,
        max_concurrency: int = 2,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """
        並行批量處理
        
        使用 semaphore 控制並發數量。
        
        參數：
            text: 要處理的長文字
            output_path: 輸出檔案路徑
            max_concurrency: 最大並發數（預設 2，符合 NF-07）
            progress_callback: 進度回調函數
        
        回傳：最終輸出檔案路徑
        
        FR 對應：FR-06, NF-07 (並發處理)
        """
        if not await self._error_handler.circuit_breaker_check():
            raise SystemError("系統熔斷中，請稍後再試")
        
        chunks = self._create_chunks(text)
        
        if not chunks:
            raise ExecutionError("無法分段文字")
        
        total = len(chunks)
        
        # 確保輸出目錄存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, mode=0o755, exist_ok=True)
        
        semaphore = asyncio.Semaphore(max_concurrency)
        chunk_paths = []
        completed = 0
        
        async def process_one(index: int, chunk: str) -> str:
            nonlocal completed
            async with semaphore:
                path = await self._synthesize_single_chunk(chunk, index, output_dir)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                return path
        
        try:
            # 建立所有任務
            tasks = [process_one(i, chunk) for i, chunk in enumerate(chunks)]
            
            # 並行執行
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 檢查結果
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    await self._error_handler.circuit_breaker_record(success=False)
                    sanitized = self._error_handler._sanitize_error_message(str(result))
                    raise ExecutionError(f"Chunk {i} 合成失敗：{sanitized}")
                else:
                    chunk_paths.append(result)
                    await self._error_handler.circuit_breaker_record(success=True)
            
            # 合併
            final_result = await self._merge_chunks(chunk_paths, output_path)
            
            # 清理
            for path in chunk_paths:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            
            return final_result
            
        except Exception as e:
            # 清理
            for path in chunk_paths:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            raise


def create_batch_processor(
    tts_engine: TTSEngine,
    error_handler: ErrorHandler = None
) -> BatchProcessor:
    """
    建立 BatchProcessor 實例
    
    參數：
        tts_engine: TTS 引擎實例
        error_handler: 錯誤處理器實例
    
    回傳：BatchProcessor 實例
    """
    return BatchProcessor(tts_engine=tts_engine, error_handler=error_handler)
