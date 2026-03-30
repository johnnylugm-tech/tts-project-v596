"""
音訊拼接器模組 (AudioMerger)

使用 ffmpeg 拼接多個 MP3 檔案為單一輸出。

FR 對應：FR-09
"""

import asyncio
import os
import subprocess
from typing import List, Dict, Any

from .error_handler import ErrorHandler, ExecutionError, ToolError


class AudioMerger:
    """
    音訊拼接器
    
    職責：
    - 使用 ffmpeg 拼接多個 MP3 檔案
    - 驗證檔案存在與格式
    - 取得音訊資訊
    """
    
    def __init__(self, error_handler: ErrorHandler = None):
        """
        初始化音訊拼接器
        
        參數：
            error_handler: 錯誤處理器實例（可選）
        """
        self._error_handler = error_handler or ErrorHandler()
    
    def _validate_files(self, file_paths: List[str]) -> bool:
        """
        驗證檔案是否存在且可讀
        
        參數：
            file_paths: 檔案路徑列表
        
        回傳：True 表示全部檔案存在
        
        拋出：ExecutionError（檔案不存在或不可讀）
        """
        if not file_paths:
            raise ExecutionError("檔案列表為空")
        
        missing = []
        for path in file_paths:
            if not os.path.exists(path):
                missing.append(path)
        
        if missing:
            raise ExecutionError(f"以下檔案不存在：{', '.join(missing)}")
        
        # 檢查讀取權限
        unreadable = []
        for path in file_paths:
            if not os.access(path, os.R_OK):
                unreadable.append(path)
        
        if unreadable:
            raise ExecutionError(f"以下檔案無法讀取：{', '.join(unreadable)}")
        
        return True
    
    def _get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """
        取得音訊檔案資訊
        
        使用 ffprobe 取得檔案的詳細資訊。
        
        參數：
            file_path: 音訊檔案路徑
        
        回傳：包含 duration, format, bitrate 等資訊的字典
        
        拋出：ExecutionError（ffmpeg/ffprobe 不可用或執行失敗）
        """
        try:
            # 使用 ffprobe 取得資訊
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    file_path
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise ExecutionError(f"ffprobe 執行失敗：{result.stderr}")
            
            import json
            info = json.loads(result.stdout)
            
            # 提取音訊流資訊
            audio_stream = None
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_stream = stream
                    break
            
            return {
                "duration": float(info.get("format", {}).get("duration", 0)),
                "format": info.get("format", {}).get("format_name", "unknown"),
                "bitrate": info.get("format", {}).get("bit_rate", "unknown"),
                "audio_codec": audio_stream.get("codec_name", "unknown") if audio_stream else "unknown",
                "sample_rate": audio_stream.get("sample_rate", "unknown") if audio_stream else "unknown",
            }
            
        except subprocess.TimeoutExpired:
            raise ExecutionError("ffprobe 執行逾時")
        except FileNotFoundError:
            raise ToolError("ffmpeg/ffprobe 未安裝，請執行：apt-get install ffmpeg")
        except json.JSONDecodeError:
            raise ExecutionError("無法解析 ffprobe 輸出")
        except Exception as e:
            sanitized = self._error_handler._sanitize_error_message(str(e))
            raise ExecutionError(f"無法取得音訊資訊：{sanitized}")
    
    async def merge_audio_files(self, file_paths: List[str], output_path: str) -> str:
        """
        合併多個音訊檔案為單一檔案
        
        使用 ffmpeg 拼接 MP3 檔案。
        
        參數：
            file_paths: 要合併的 MP3 檔案路徑列表
            output_path: 輸出檔案路徑
        
        回傳：合併後的檔案路徑
        
        拋出：
            ExecutionError：拼接失敗
            ToolError：ffmpeg 未安裝
        
        FR 對應：FR-09
        
        示例：
            >>> merger = AudioMerger()
            >>> merged = await merger.merge_audio_files(
            ...     file_paths=["chunk1.mp3", "chunk2.mp3"],
            ...     output_path="output/final.mp3"
            ... )
        """
        # 驗證輸入
        if not file_paths:
            raise ExecutionError("檔案列表為空")
        
        if len(file_paths) == 1:
            # 只有一個檔案，直接複製
            return await self._copy_single_file(file_paths[0], output_path)
        
        # 驗證所有檔案存在
        self._validate_files(file_paths)
        
        try:
            # 確保輸出目錄存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, mode=0o755, exist_ok=True)
            
            # 建立臨時檔案列表（用於 ffmpeg concat）
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for path in file_paths:
                    # ffmpeg concat 需要绝对路径
                    abs_path = os.path.abspath(path)
                    f.write(f"file '{abs_path}'\n")
                temp_file = f.name
            
            try:
                # 執行 ffmpeg 拼接
                await self._run_ffmpeg_concat(temp_file, output_path)
            finally:
                # 清理臨時檔案
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
            
            # 驗證輸出檔案
            if not os.path.exists(output_path):
                raise ExecutionError("合併後檔案未產生")
            
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                raise ExecutionError("合併後檔案為空")
            
            # 設定檔案權限為 644（SD-02）
            os.chmod(output_path, 0o644)
            
            return output_path
            
        except ExecutionError:
            raise
        except ToolError:
            raise
        except Exception as e:
            sanitized = self._error_handler._sanitize_error_message(str(e))
            raise ExecutionError(f"音訊合併失敗：{sanitized}")
    
    async def _run_ffmpeg_concat(self, file_list_path: str, output_path: str) -> None:
        """
        執行 ffmpeg concat 拼接
        
        參數：
            file_list_path: 包含檔案列表的臨時檔案路徑
            output_path: 輸出檔案路徑
        """
        loop = asyncio.get_event_loop()
        
        try:
            await loop.run_in_executor(
                None,
                self._ffmpeg_concat_sync,
                file_list_path,
                output_path
            )
        except subprocess.CalledProcessError as e:
            sanitized = self._error_handler._sanitize_error_message(str(e))
            raise ExecutionError(f"ffmpeg 拼接失敗：{sanitized}")
    
    def _ffmpeg_concat_sync(self, file_list_path: str, output_path: str) -> None:
        """同步執行 ffmpeg concat"""
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",  # 覆蓋輸出檔案
                "-f", "concat",
                "-safe", "0",
                "-i", file_list_path,
                "-c", "copy",  # 直接複製，不重新編碼（快速）
                "-b:a", "192k",  # 設定音訊位元率（SD-04 品質保証）
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5 分鐘超時
        )
        
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, result.stderr)
    
    async def _copy_single_file(self, source_path: str, dest_path: str) -> str:
        """
        複製單一檔案
        
        當只有一個 chunk 時使用，避免 ffmpeg 開銷。
        """
        loop = asyncio.get_event_loop()
        
        # 確保輸出目錄存在
        output_dir = os.path.dirname(dest_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, mode=0o755, exist_ok=True)
        
        await loop.run_in_executor(
            None,
            self._copy_file_sync,
            source_path,
            dest_path
        )
        
        # 設定檔案權限
        os.chmod(dest_path, 0o644)
        
        return dest_path
    
    def _copy_file_sync(self, source: str, dest: str) -> None:
        """同步複製檔案"""
        import shutil
        shutil.copy2(source, dest)


def create_audio_merger(error_handler: ErrorHandler = None) -> AudioMerger:
    """建立 AudioMerger 實例"""
    return AudioMerger(error_handler=error_handler)
