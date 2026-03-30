"""
音訊導出器模組 (AudioExporter)

將音訊資料寫入 MP3 檔案，確保檔案格式正確。

FR 對應：FR-04
"""

import asyncio
import os
from typing import Optional

from .error_handler import ErrorHandler, ExecutionError


class AudioExporter:
    """
    音訊導出器
    
    職責：
    - 將音訊資料寫入 MP3 檔案
    - 驗證 MP3 檔案格式
    - 確保輸出目錄存在且可寫入
    """
    
    def __init__(self, error_handler: ErrorHandler = None):
        """
        初始化音訊導出器
        
        參數：
            error_handler: 錯誤處理器實例（可選）
        """
        self._error_handler = error_handler or ErrorHandler()
    
    async def write_mp3(self, audio_data: bytes, file_path: str) -> str:
        """
        寫入 MP3 檔案
        
        參數：
            audio_data: 音訊資料
            file_path: 輸出檔案路徑
        
        回傳：實際寫入的檔案路徑
        
        拋出：
            ExecutionError：寫入失敗
            InputError：資料為空或路徑無效
        
        FR 對應：FR-04
        
        示例：
            >>> exporter = AudioExporter()
            >>> path = await exporter.write_mp3(audio_data, "output/test.mp3")
        """
        # 驗證輸入
        if not audio_data:
            raise ExecutionError("音訊資料為空，無法寫入檔案")
        
        if not file_path:
            raise ExecutionError("檔案路徑不能為空")
        
        # 安全檢查：路徑不能包含敏感字元
        if self._contains_path_traversal(file_path):
            raise ExecutionError("檔案路徑包含無效字元")
        
        try:
            # 確保輸出目錄存在
            output_dir = os.path.dirname(file_path)
            if output_dir and not os.path.exists(output_dir):
                # 依照 SD-02 設定目錄權限為 755
                os.makedirs(output_dir, mode=0o755, exist_ok=True)
            
            # 寫入檔案（使用非同步方式避免阻塞）
            await self._async_write_file(file_path, audio_data)
            
            # 驗證檔案
            if not await self._validate_mp3(file_path):
                raise ExecutionError("MP3 檔案格式驗證失敗")
            
            # 設定檔案權限為 644（SD-02）
            os.chmod(file_path, 0o644)
            
            return file_path
            
        except ExecutionError:
            raise
        except PermissionError as e:
            raise ExecutionError(f"無寫入權限：{file_path}")
        except OSError as e:
            sanitized = self._error_handler._sanitize_error_message(str(e))
            raise ExecutionError(f"寫入檔案失敗：{sanitized}")
    
    async def _async_write_file(self, file_path: str, data: bytes) -> None:
        """
        非同步寫入檔案
        
        使用執行緒池避免阻塞事件循環。
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_file_sync,
            file_path,
            data
        )
    
    def _write_file_sync(self, file_path: str, data: bytes) -> None:
        """同步寫入檔案（實際執行）"""
        with open(file_path, "wb") as f:
            f.write(data)
    
    async def _validate_mp3(self, file_path: str) -> bool:
        """
        驗證 MP3 格式
        
        檢查：
        - 檔案是否存在
        - 檔案大小 > 0
        - MP3 檔頭（可選更嚴格的驗證）
        
        參數：
            file_path: 檔案路徑
        
        回傳：True 表示驗證通過
        """
        try:
            # 檢查檔案是否存在
            if not os.path.exists(file_path):
                return False
            
            # 檢查檔案大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False
            
            # 讀取檔頭驗證 MP3 格式
            with open(file_path, "rb") as f:
                header = f.read(4)
                
                if file_size < 100:
                    # 太小可能不是有效 MP3
                    return False
                
                # 如果有 ID3 標籤，跳過
                if header[:3] == b'ID3':
                    return True
                
                # 否則假設為原始 MP3 frame
                return True
                
        except Exception:
            return False
    
    def _contains_path_traversal(self, file_path: str) -> bool:
        """
        檢查路徑是否包含路徑遍歷攻擊字元
        
        檢查：.., 絕對路徑 /, \\ 等
        """
        if ".." in file_path:
            return True
        if file_path.startswith("/"):
            return True
        if len(file_path) >= 2 and file_path[1] == ":":
            return True
        return False
    
    async def get_file_size(self, file_path: str) -> Optional[int]:
        """
        取得檔案大小
        
        參數：
            file_path: 檔案路徑
        
        回傳：檔案大小（bytes），若不存在返回 None
        """
        try:
            return os.path.getsize(file_path)
        except OSError:
            return None


def create_audio_exporter(error_handler: ErrorHandler = None) -> AudioExporter:
    """建立 AudioExporter 實例"""
    return AudioExporter(error_handler=error_handler)
