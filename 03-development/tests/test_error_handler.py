"""
測試 ErrorHandler 模組

FR 對應：FR-05
"""

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts_project.error_handler import (
    TTSError,
    InputError,
    ToolError,
    ExecutionError,
    SystemError,
    ErrorHandler,
    CircuitBreaker,
)


class TestTTSErrorHierarchy:
    """TTS 錯誤層次結構測試"""
    
    def test_tts_error_base(self):
        """測試基底類別"""
        error = TTSError("base error")
        assert str(error) == "base error"
        assert isinstance(error, Exception)
    
    def test_input_error_l1(self):
        """測試 L1 輸入錯誤"""
        error = InputError("input error")
        assert isinstance(error, TTSError)
        assert isinstance(error, InputError)
        assert "input error" in str(error)
    
    def test_tool_error_l2(self):
        """測試 L2 工具錯誤"""
        error = ToolError("tool error")
        assert isinstance(error, TTSError)
        assert isinstance(error, ToolError)
    
    def test_execution_error_l3(self):
        """測試 L3 執行錯誤"""
        error = ExecutionError("execution error")
        assert isinstance(error, TTSError)
        assert isinstance(error, ExecutionError)
    
    def test_system_error_l4(self):
        """測試 L4 系統錯誤"""
        error = SystemError("system error")
        assert isinstance(error, TTSError)
        assert isinstance(error, SystemError)
    
    def test_error_catching_hierarchy(self):
        """測試錯誤捕捉層次"""
        with pytest.raises(TTSError):
            raise InputError("test")
        
        with pytest.raises(TTSError):
            raise ToolError("test")
        
        with pytest.raises(TTSError):
            raise ExecutionError("test")
        
        with pytest.raises(TTSError):
            raise SystemError("test")


class TestCircuitBreaker:
    """電路熔斷器測試"""
    
    def test_init_state(self):
        """測試初始狀態"""
        cb = CircuitBreaker()
        assert cb.state == "closed"
    
    @pytest.mark.asyncio
    async def test_record_success(self):
        """測試記錄成功"""
        cb = CircuitBreaker()
        await cb.record(success=True)
        assert cb.state == "closed"
        assert await cb.can_execute() == True
    
    @pytest.mark.asyncio
    async def test_record_failure(self):
        """測試記錄失敗"""
        cb = CircuitBreaker()
        await cb.record(success=False)
        assert cb.state == "closed"
        assert await cb.can_execute() == True
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """測試超過閾值後熔斷器打開"""
        cb = CircuitBreaker()
        # 記錄 5 次失敗（達到閾值）
        for _ in range(5):
            await cb.record(success=False)
        assert cb.state == "open"
        assert await cb.can_execute() == False
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_recovery(self):
        """測試恢復後熔斷器關閉"""
        cb = CircuitBreaker()
        # 達到閾值
        for _ in range(5):
            await cb.record(success=False)
        assert cb.state == "open"
        
        # 清理失敗記錄（模擬時間流逝）
        cb._failures = []
        await cb.record(success=True)
        assert cb.state == "closed"
        assert await cb.can_execute() == True
    
    @pytest.mark.asyncio
    async def test_half_open_state(self):
        """測試半開狀態"""
        cb = CircuitBreaker()
        # 達到閾值
        for _ in range(5):
            await cb.record(success=False)
        assert cb.state == "open"
        
        # 模擬時間流逝（更新最後失敗時間）
        import time
        cb._last_failure_time = time.time() - cb.RECOVERY_TIMEOUT - 1
        
        # 檢查是否進入 half-open
        can_exec = await cb.can_execute()
        # 應該返回 True（嘗試恢復）
        assert can_exec == True


class TestErrorHandler:
    """錯誤處理器測試"""
    
    def test_init(self):
        """測試初始化"""
        handler = ErrorHandler()
        assert handler.circuit_breaker_state in ["closed", "open", "half-open"]
    
    def test_sanitize_workspace_path(self):
        """測試路徑過濾 - workspace"""
        msg = "/workspace/tts-project/test.txt"
        result = ErrorHandler._sanitize_error_message(msg)
        assert "[REDACTED]" in result
        assert "/workspace/" not in result
    
    def test_sanitize_home_path(self):
        """測試路徑過濾 - home"""
        msg = "/home/user/file.txt"
        result = ErrorHandler._sanitize_error_message(msg)
        assert "[REDACTED]" in result
        assert "/home/" not in result
    
    def test_sanitize_windows_path(self):
        """測試路徑過濾 - Windows"""
        msg = "C:\\Users\\test\\file.txt"
        result = ErrorHandler._sanitize_error_message(msg)
        assert "[REDACTED]" in result
        assert "C:\\" not in result
    
    def test_sanitize_no_paths(self):
        """測試無路徑時不過濾"""
        msg = "Normal error message"
        result = ErrorHandler._sanitize_error_message(msg)
        assert result == msg
    
    def test_raise_input_error(self):
        """測試拋出 L1 錯誤"""
        with pytest.raises(InputError):
            ErrorHandler.raise_input_error("test input error")
    
    def test_raise_tool_error(self):
        """測試拋出 L2 錯誤"""
        with pytest.raises(ToolError):
            ErrorHandler.raise_tool_error("test tool error")
    
    def test_raise_execution_error(self):
        """測試拋出 L3 錯誤"""
        with pytest.raises(ExecutionError):
            ErrorHandler.raise_execution_error("test execution error")
    
    def test_raise_system_error(self):
        """測試拋出 L4 錯誤"""
        with pytest.raises(SystemError):
            ErrorHandler.raise_system_error("test system error")
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """測試重試成功"""
        handler = ErrorHandler()
        call_count = 0
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await handler.retry_with_backoff(mock_func, max_retries=3)
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_failure(self):
        """測試重試失敗"""
        handler = ErrorHandler()
        call_count = 0
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("test error")
        
        with pytest.raises(ToolError):
            await handler.retry_with_backoff(mock_func, max_retries=3, backoff_base=0.1)
        
        # 應該重試 3 次
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_check(self):
        """測試電路熔斷器檢查"""
        handler = ErrorHandler()
        result = await handler.circuit_breaker_check()
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_record(self):
        """測試電路熔斷器記錄"""
        handler = ErrorHandler()
        await handler.circuit_breaker_record(success=True)
        await handler.circuit_breaker_record(success=False)


class TestErrorHandlerFactory:
    """錯誤處理器工廠測試"""
    
    def test_create_error_handler(self):
        """測試建立錯誤處理器"""
        from tts_project.error_handler import create_error_handler
        handler = create_error_handler()
        assert isinstance(handler, ErrorHandler)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])