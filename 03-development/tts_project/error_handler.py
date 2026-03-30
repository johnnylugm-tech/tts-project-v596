"""
TTS 錯誤處理模組 (ErrorHandler)

定義 L1-L4 錯誤層次與電路熔斷器機制。

FR 對應：FR-05
"""

import asyncio
import logging
import re
import time
from typing import Callable, Any, TypeVar

T = TypeVar('T')

# ============================================================================
# 例外類別層次結構
# ============================================================================

class TTSError(Exception):
    """TTS 系統例外基底類別"""
    pass


class InputError(TTSError):
    """
    L1: 輸入錯誤，立即返回
    
    觸發條件：
    - 文字為空或長度為 0
    - 輸出目錄無寫入權限
    - 音色名稱格式錯誤
    """
    pass


class ToolError(TTSError):
    """
    L2: 工具錯誤，retry=3，backoff 1s/2s/4s
    
    觸發條件：
    - edge-tts WebSocket 連線失敗
    - 網路逾時
    - 遠端伺服器錯誤（5xx）
    """
    pass


class ExecutionError(TTSError):
    """
    L3: 執行錯誤，Fallback
    
    觸發條件：
    - ffmpeg 拼接失敗
    - 磁碟空間不足
    - 檔案寫入失敗（非網路原因）
    """
    pass


class SystemError(TTSError):
    """
    L4: 系統錯誤，Circuit Breaker（5次失敗/60s）
    
    觸發條件：
    - 60 秒內連續 5 次失敗
    - 系統資源耗盡（記憶體、磁碟）
    """
    pass


# ============================================================================
# 電路熔斷器
# ============================================================================

class CircuitBreaker:
    """電路熔斷器，防止系統雪崩"""
    
    FAILURE_THRESHOLD = 5  # 60 秒內失敗次數閾值
    TIMEOUT = 60  # 秒，失敗記錄的有效時間窗口
    RECOVERY_TIMEOUT = 30  # 秒，熔斷後嘗試恢復的間隔
    
    def __init__(self):
        self._failures: list[float] = []
        self._state: str = "closed"  # closed, open, half-open
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> str:
        """取得當前熔斷器狀態"""
        return self._state
    
    async def record(self, success: bool) -> None:
        """記錄請求結果，更新熔斷器狀態"""
        async with self._lock:
            now = time.time()
            
            # 清理過期失敗記錄（超過 TIMEOUT 秒）
            self._failures = [f for f in self._failures if now - f < self.TIMEOUT]
            
            if not success:
                self._failures.append(now)
                self._last_failure_time = now
            
            # 狀態轉換邏輯
            if len(self._failures) >= self.FAILURE_THRESHOLD:
                self._state = "open"
                logging.warning(f"Circuit breaker OPEN: {len(self._failures)} failures in {self.TIMEOUT}s")
            elif self._state == "open":
                if len(self._failures) == 0:
                    self._state = "closed"
                    logging.info("Circuit breaker CLOSED: recovered")
                elif now - self._last_failure_time >= self.RECOVERY_TIMEOUT:
                    self._state = "half-open"
                    logging.info("Circuit breaker HALF-OPEN: attempting recovery")
    
    async def can_execute(self) -> bool:
        """檢查是否可以執行請求"""
        async with self._lock:
            if self._state == "closed":
                return True
            
            if self._state == "open":
                # 檢查是否超過恢復超時
                if self._failures and time.time() - self._failures[-1] >= self.RECOVERY_TIMEOUT:
                    self._state = "half-open"
                    return True
                return False
            
            # half-open 狀態允許執行
            return True


# ============================================================================
# 錯誤處理器
# ============================================================================

class ErrorHandler:
    """
    統一的錯誤處理器
    
    職責：
    - L1-L4 錯誤分類與拋出
    - 重試機制（exponential backoff）
    - 電路熔斷器管理
    """
    
    def __init__(self):
        self._circuit_breaker = CircuitBreaker()
        self._setup_logging("INFO")
    
    def _setup_logging(self, level: str = "INFO") -> None:
        """配置日誌"""
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self._logger = logging.getLogger(__name__)
    
    @staticmethod
    def _sanitize_error_message(msg: str) -> str:
        """
        過濾錯誤訊息中的敏感路徑（SD-03）
        
        將系統路徑替換為 [REDACTED]，防止資訊外洩。
        """
        patterns = [
            r'/workspace/[\w/]+',
            r'C:\\[\w\\]+',
            r'D:\\[\w\\]+',
            r'/home/[\w/]+',
        ]
        for pattern in patterns:
            msg = re.sub(pattern, '[REDACTED]', msg)
        return msg
    
    @staticmethod
    def raise_input_error(message: str) -> None:
        """拋出 L1 輸入錯誤（立即返回）"""
        sanitized = ErrorHandler._sanitize_error_message(message)
        raise InputError(sanitized)
    
    @staticmethod
    def raise_tool_error(message: str) -> None:
        """拋出 L2 工具錯誤（需重試）"""
        sanitized = ErrorHandler._sanitize_error_message(message)
        raise ToolError(sanitized)
    
    @staticmethod
    def raise_execution_error(message: str) -> None:
        """拋出 L3 執行錯誤（需 fallback）"""
        sanitized = ErrorHandler._sanitize_error_message(message)
        raise ExecutionError(sanitized)
    
    @staticmethod
    def raise_system_error(message: str) -> None:
        """拋出 L4 系統錯誤（電路熔斷）"""
        sanitized = ErrorHandler._sanitize_error_message(message)
        raise SystemError(sanitized)
    
    async def retry_with_backoff(
        self,
        func: Callable[..., Any],
        max_retries: int = 3,
        backoff_base: float = 1.0,
        *args,
        **kwargs
    ) -> Any:
        """
        重試包裝器，支援 exponential backoff
        
        參數：
            func: 要執行的非同步函數
            max_retries: 最大重試次數（預設 3）
            backoff_base: 初始 backoff 秒數（預設 1.0）
            *args, **kwargs: 传递给 func 的參數
        
        回傳：func 的執行結果
        
        拋出：ToolError（超過最大重試次數）
        
        FR 對應：FR-05 (L2 重試機制)
        """
        backoff_schedule = [backoff_base * (2 ** i) for i in range(max_retries)]
        
        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = backoff_schedule[attempt]
                    logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    sanitized = self._sanitize_error_message(str(e))
                    raise ToolError(f"Max retries exceeded after {max_retries} attempts: {sanitized}")
        
        # 這裡不應該到達，但為了安全
        raise ToolError("Max retries exceeded: unknown error")
    
    async def circuit_breaker_check(self) -> bool:
        """
        檢查電路熔斷器狀態
        
        回傳：True 表示可以執行，False 表示熔斷中
        
        FR 對應：FR-05 (L4 電路熔斷)
        """
        return await self._circuit_breaker.can_execute()
    
    async def circuit_breaker_record(self, success: bool) -> None:
        """
        記錄請求結果到電路熔斷器
        
        參數：
            success: True 表示成功，False 表示失敗
        """
        await self._circuit_breaker.record(success)
    
    @property
    def circuit_breaker_state(self) -> str:
        """取得當前熔斷器狀態"""
        return self._circuit_breaker.state


# ============================================================================
# 快捷工廠函數
# ============================================================================

def create_error_handler() -> ErrorHandler:
    """建立錯誤處理器實例"""
    return ErrorHandler()