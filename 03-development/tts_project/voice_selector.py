"""
音色選擇器模組 (VoiceSelector)

列舉與選擇 TTS 音色，支援台灣國語音色。

FR 對應：FR-08
"""

import asyncio
from typing import List, Optional, Dict, Any

try:
    import edge_tts
except ImportError:
    edge_tts = None

from .error_handler import ErrorHandler, ToolError


class VoiceSelector:
    """
    音色選擇器
    
    職責：
    - 列舉所有可用音色
    - 列舉台灣國語音色
    - 驗證音色是否存在
    """
    
    # 預設音色（台灣國語女聲）
    DEFAULT_VOICE = "zh-TW-HsiaoHsiaoNeural"
    
    # 台灣國語相關的 Locale
    TAIWAN_LOCALES = [
        "zh-TW",
        "zh-CN",  # 包含部分可理解的發音
    ]
    
    # 台灣國語相關的語言代碼
    TAIWAN_LANGUAGES = [
        "Chinese (Taiwan)",
        "Chinese (Mandarin)",
    ]
    
    def __init__(self, error_handler: ErrorHandler = None):
        """
        初始化音色選擇器
        
        參數：
            error_handler: 錯誤處理器實例（可選）
        """
        self._error_handler = error_handler or ErrorHandler()
    
    async def list_voices(self) -> List[Dict[str, Any]]:
        """
        列舉所有可用音色
        
        回傳：音色列表，每個音色為包含名稱、語言、Gender 等資訊的字典
        
        拋出：ToolError（edge-tts 呼叫失敗）
        
        FR 對應：FR-08
        
        示例：
            >>> selector = VoiceSelector()
            >>> voices = await selector.list_voices()
            >>> for voice in voices[:5]:
            ...     print(voice['Name'])
        """
        try:
            if edge_tts is None:
                raise ToolError("edge-tts 套件未安裝，請執行：pip install edge-tts")
            
            communicate = edge_tts.Communicate("")
            voices = await communicate.get_voices()
            await communicate.close()
            
            # 轉換為標準化格式
            return [
                {
                    "Name": v.name,
                    "ShortName": v.short_name,
                    "Gender": v.gender,
                    "Locale": v.locale,
                    "Language": v.language,
                    "FriendlyName": v.friendly_name,
                }
                for v in voices
            ]
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"無法取得音色列表：{e}")
    
    async def list_taiwan_voices(self) -> List[Dict[str, Any]]:
        """
        列舉台灣國語音色
        
        僅返回 Locale 為 zh-TW 的音色
        
        回傳：台灣國語音色列表
        
        拋出：ToolError（edge-tts 呼叫失敗）
        
        FR 對應：FR-08
        
        示例：
            >>> selector = VoiceSelector()
            >>> tw_voices = await selector.list_taiwan_voices()
            >>> for voice in tw_voices:
            ...     print(voice['Name'])
        """
        all_voices = await self.list_voices()
        
        # 過濾台灣國語音色（Locale 為 zh-TW）
        taiwan_voices = [
            v for v in all_voices
            if v["Locale"] in self.TAIWAN_LOCALES or v["Language"] in self.TAIWAN_LANGUAGES
        ]
        
        return taiwan_voices
    
    async def validate_voice(self, voice_name: str) -> bool:
        """
        驗證音色是否存在
        
        參數：
            voice_name: 音色名稱（如 "zh-TW-HsiaoHsiaoNeural"）
        
        回傳：True 表示音色存在，False 表示不存在
        
        拋出：ToolError（edge-tts 呼叫失敗）
        
        FR 對應：FR-08
        
        示例：
            >>> selector = VoiceSelector()
            >>> if await selector.validate_voice("zh-TW-HsiaoHsiaoNeural"):
            ...     print("音色存在")
        """
        try:
            all_voices = await self.list_voices()
            
            # 檢查是否有完全匹配的音色名稱
            for voice in all_voices:
                if voice["Name"] == voice_name:
                    return True
            
            return False
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"無法驗證音色：{e}")
    
    async def get_voice_by_name(self, voice_name: str) -> Optional[Dict[str, Any]]:
        """
        根據音色名稱取得音色資訊
        
        參數：
            voice_name: 音色名稱
        
        回傳：音色資訊字典，若不存在返回 None
        
        拋出：ToolError（edge-tts 呼叫失敗）
        """
        try:
            all_voices = await self.list_voices()
            
            for voice in all_voices:
                if voice["Name"] == voice_name:
                    return voice
            
            return None
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"無法取得音色資訊：{e}")
    
    @staticmethod
    def get_default_voice() -> str:
        """
        取得預設音色
        
        回傳：預設音色名稱
        
        FR 對應：FR-08
        """
        return VoiceSelector.DEFAULT_VOICE
    
    async def filter_voices(
        self,
        locale: str = None,
        gender: str = None,
        language: str = None
    ) -> List[Dict[str, Any]]:
        """
        根據條件過濾音色
        
        參數：
            locale: 地區代碼（如 "zh-TW"）
            gender: 性別（如 "Female", "Male"）
            language: 語言名稱（如 "Chinese (Taiwan)"）
        
        回傳：符合條件的音色列表
        """
        all_voices = await self.list_voices()
        
        result = all_voices
        
        if locale:
            result = [v for v in result if v["Locale"] == locale]
        
        if gender:
            result = [v for v in result if v["Gender"] == gender]
        
        if language:
            result = [v for v in result if language.lower() in v["Language"].lower()]
        
        return result


# ============================================================================
# 快捷工廠函數
# ============================================================================

def create_voice_selector(error_handler: ErrorHandler = None) -> VoiceSelector:
    """
    建立 VoiceSelector 實例
    
    參數：
        error_handler: 錯誤處理器實例（可選）
    
    回傳：VoiceSelector 實例
    """
    return VoiceSelector(error_handler=error_handler)