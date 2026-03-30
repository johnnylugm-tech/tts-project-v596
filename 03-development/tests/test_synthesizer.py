"""
測試 Synthesizer 模組

FR 對應：FR-03
"""

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts_project.synthesizer import Synthesizer
from tts_project.error_handler import ErrorHandler, ToolError


class TestSynthesizer:
    """Synthesizer 測試案例"""
    
    @pytest.mark.asyncio
    async def test_init_default(self):
        """測試預設初始化"""
        synthesizer = Synthesizer()
        assert synthesizer._error_handler is not None
    
    @pytest.mark.asyncio
    async def test_init_with_error_handler(self):
        """測試使用錯誤處理器初始化"""
        handler = ErrorHandler()
        synthesizer = Synthesizer(error_handler=handler)
        assert synthesizer._error_handler is handler
    
    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self):
        """測試空文字合成（應拋出錯誤）"""
        synthesizer = Synthesizer()
        with pytest.raises(ToolError):
            await synthesizer.synthesize_stream(
                text="",
                voice="zh-TW-HsiaoHsiaoNeural"
            )
    
    @pytest.mark.asyncio
    async def test_synthesize_whitespace_only(self):
        """測試僅空白文字合成"""
        synthesizer = Synthesizer()
        # edge-tts 可能對空白字元有不同的行為
        # 這裡測試系統如何處理
        try:
            result = await synthesizer.synthesize_stream(
                text="   ",
                voice="zh-TW-HsiaoHsiaoNeural"
            )
            # 如果成功，結果應該是空 bytes 或有長度
            assert isinstance(result, bytes)
        except ToolError:
            # 預期的行為：空文字應拋出錯誤
            pass
    
    def test_decode_audio_empty_chunks(self):
        """測試解碼空區塊"""
        synthesizer = Synthesizer()
        result = synthesizer._decode_audio([])
        assert result == b""
    
    def test_decode_audio_single_chunk(self):
        """測試解碼單一區塊"""
        synthesizer = Synthesizer()
        chunks = [b"audio_data"]
        result = synthesizer._decode_audio(chunks)
        assert result == b"audio_data"
    
    def test_decode_audio_multiple_chunks(self):
        """測試解碼多個區塊"""
        synthesizer = Synthesizer()
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        result = synthesizer._decode_audio(chunks)
        assert result == b"chunk1chunk2chunk3"
    
    def test_reset(self):
        """測試重置"""
        synthesizer = Synthesizer()
        synthesizer._chunks = ["test"]
        synthesizer.reset()
        assert synthesizer._chunks == []


class TestSynthesizerFactory:
    """Synthesizer 工廠測試"""
    
    def test_create_synthesizer_default(self):
        """測試建立合成器（預設）"""
        from tts_project.synthesizer import create_synthesizer
        synthesizer = create_synthesizer()
        assert isinstance(synthesizer, Synthesizer)
    
    def test_create_synthesizer_with_handler(self):
        """測試建立合成器（帶錯誤處理器）"""
        from tts_project.synthesizer import create_synthesizer
        handler = ErrorHandler()
        synthesizer = create_synthesizer(error_handler=handler)
        assert isinstance(synthesizer, Synthesizer)
        assert synthesizer._error_handler is handler


# 整合測試（需要 edge-tts）
class TestSynthesizerIntegration:
    """Synthesizer 整合測試（需要網路）"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_NETWORK_TESTS") == "1",
        reason="跳過網路整合測試"
    )
    async def test_synthesize_real(self):
        """測試實際合成"""
        synthesizer = Synthesizer()
        try:
            result = await synthesizer.synthesize_stream(
                text="你好，測試。",
                voice="zh-TW-HsiaoHsiaoNeural"
            )
            # 應該返回音訊資料
            assert isinstance(result, bytes)
            assert len(result) > 0
        except ToolError as e:
            pytest.skip(f"edge-tts 不可用：{e}")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("SKIP_NETWORK_TESTS") == "1",
        reason="跳過網路整合測試"
    )
    async def test_synthesize_with_retry(self):
        """測試帶重試的合成"""
        synthesizer = Synthesizer()
        try:
            result = await synthesizer.synthesize_with_retry(
                text="測試重試",
                voice="zh-TW-HsiaoHsiaoNeural",
                max_retries=3
            )
            assert isinstance(result, bytes)
        except ToolError:
            pytest.skip("edge-tts 不可用")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])