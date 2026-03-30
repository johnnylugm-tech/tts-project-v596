"""
參數控制器模組 (ParameterController)

動態調整 rate 和 volume 參數，無需重新初始化。

FR 對應：FR-07
"""

import re
from typing import Optional


class ParameterController:
    """
    TTS 參數控制器
    
    職責：
    - 動態調整語速（rate）
    - 動態調整音量（volume）
    - 參數格式驗證
    """
    
    # 預設值
    DEFAULT_RATE = "+0%"
    DEFAULT_VOLUME = "+0%"
    
    # 有效格式正規表示式（edge-tts 格式）
    RATE_PATTERN = re.compile(r'^[-+]\d+%$')
    VOLUME_PATTERN = re.compile(r'^[-+]\d+%$')
    
    # 有效範圍
    MIN_RATE = -100  # -100%
    MAX_RATE = 100   # +100%
    MIN_VOLUME = -100  # -100%
    MAX_VOLUME = 100   # +100%
    
    def __init__(self, rate: str = None, volume: str = None):
        """
        初始化參數控制器
        
        參數：
            rate: 初始語速（格式：+20%、-10%、0%）
            volume: 初始音量（格式：+20%、-10%、0%）
        
        拋出：ValueError（格式錯誤）
        """
        self._rate = self._validate_and_normalize_rate(rate or self.DEFAULT_RATE)
        self._volume = self._validate_and_normalize_volume(volume or self.DEFAULT_VOLUME)
    
    @property
    def rate(self) -> str:
        """取得當前語速設定"""
        return self._rate
    
    @property
    def volume(self) -> str:
        """取得當前音量設定"""
        return self._volume
    
    def _validate_rate(self, rate: str) -> bool:
        """
        驗證語速格式是否正確
        
        格式：+20%、-10%、0%（數字部分可以是任意位數）
        """
        if not self.RATE_PATTERN.match(rate):
            return False
        
        # 解析數值部分
        match = re.match(r'^([-+])(\d+)%$', rate)
        if not match:
            return False
        
        sign = match.group(1)
        value = int(match.group(2))
        
        # 檢查範圍
        return self.MIN_RATE <= value <= self.MAX_RATE
    
    def _validate_volume(self, volume: str) -> bool:
        """
        驗證音量格式是否正確
        
        格式：+20%、-10%、0%（數字部分可以是任意位數）
        """
        if not self.VOLUME_PATTERN.match(volume):
            return False
        
        # 解析數值部分
        match = re.match(r'^([-+])(\d+)%$', volume)
        if not match:
            return False
        
        sign = match.group(1)
        value = int(match.group(2))
        
        # 檢查範圍
        return self.MIN_VOLUME <= value <= self.MAX_VOLUME
    
    def _validate_and_normalize_rate(self, rate: str) -> str:
        """驗證並正規化語速"""
        if not self._validate_rate(rate):
            raise ValueError(f"Invalid rate format: {rate}. Expected format: +20%, -10%, 0%")
        return rate
    
    def _validate_and_normalize_volume(self, volume: str) -> str:
        """驗證並正規化音量"""
        if not self._validate_volume(volume):
            raise ValueError(f"Invalid volume format: {volume}. Expected format: +20%, -10%, 0%")
        return volume
    
    def set_rate(self, rate: str) -> None:
        """
        設定語速
        
        參數：
            rate: 新的語速設定（格式：+20%、-10%、0%）
        
        拋出：ValueError（格式錯誤）
        
        FR 對應：FR-07
        
        示例：
            >>> controller = ParameterController()
            >>> controller.set_rate("+20%")  # 加快 20%
            >>> controller.set_rate("-10%")  # 放慢 10%
            >>> controller.set_rate("+0%")   # 恢復預設
        """
        self._rate = self._validate_and_normalize_rate(rate)
    
    def set_volume(self, volume: str) -> None:
        """
        設定音量
        
        參數：
            volume: 新的音量設定（格式：+20%、-10%、0%）
        
        拋出：ValueError（格式錯誤）
        
        FR 對應：FR-07
        
        示例：
            >>> controller = ParameterController()
            >>> controller.set_volume("+20%")  # 增大 20%
            >>> controller.set_volume("-10%")  # 降低 10%
            >>> controller.set_volume("+0%")   # 恢復預設
        """
        self._volume = self._validate_and_normalize_volume(volume)
    
    def get_rate(self) -> str:
        """
        取得當前語速
        
        回傳：當前語速字串（格式：+20%、-10%、0%）
        
        FR 對應：FR-07
        """
        return self._rate
    
    def get_volume(self) -> str:
        """
        取得當前音量
        
        回傳：當前音量字串（格式：+20%、-10%、0%）
        
        FR 對應：FR-07
        """
        return self._volume
    
    def to_dict(self) -> dict:
        """
        取得參數字典
        
        回傳：包含 rate 和 volume 的字典
        """
        return {
            "rate": self._rate,
            "volume": self._volume
        }
    
    def reset(self) -> None:
        """
        重置為預設值
        
        將 rate 和 volume 恢復為 +0%
        """
        self._rate = self.DEFAULT_RATE
        self._volume = self.DEFAULT_VOLUME
    
    def __repr__(self) -> str:
        return f"ParameterController(rate={self._rate}, volume={self._volume})"


# ============================================================================
# 快捷工廠函數
# ============================================================================

def create_parameter_controller(
    rate: str = None,
    volume: str = None
) -> ParameterController:
    """
    建立 ParameterController 實例
    
    參數：
        rate: 初始語速（預設 None = +0%）
        volume: 初始音量（預設 None = +0%）
    
    回傳：ParameterController 實例
    """
    return ParameterController(rate=rate, volume=volume)