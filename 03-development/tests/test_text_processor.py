"""
測試 TextProcessor 模組

FR 對應：FR-02
"""

import pytest
import sys
import os

# 將專案目錄加入路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts_project.text_processor import TextProcessor


class TestTextProcessor:
    """TextProcessor 測試案例"""
    
    def test_init_default_values(self):
        """測試預設值"""
        processor = TextProcessor()
        assert processor.max_chunk_size == 800
        assert "。" in processor.semantic_markers
        assert "！" in processor.semantic_markers
        assert "？" in processor.semantic_markers
    
    def test_init_custom_values(self):
        """測試自訂值"""
        processor = TextProcessor(max_chunk_size=500, semantic_markers=["。", "！"])
        assert processor.max_chunk_size == 500
        assert len(processor.semantic_markers) == 2
    
    def test_empty_text(self):
        """測試空文字"""
        processor = TextProcessor()
        result = processor._preprocess_text("")
        assert result == []
    
    def test_whitespace_only(self):
        """測試僅空白文字"""
        processor = TextProcessor()
        result = processor._preprocess_text("   \n\t  ")
        assert result == []
    
    def test_single_short_text(self):
        """測試單一短文字（少於 800 字）"""
        processor = TextProcessor()
        text = "這是一段測試文字。"
        result = processor._preprocess_text(text)
        assert len(result) == 1
        assert result[0] == text
    
    def test_single_chunk_800_chars(self):
        """測試單一 chunk 正好 800 字"""
        processor = TextProcessor(max_chunk_size=800)
        text = "測" * 800
        result = processor._preprocess_text(text)
        assert len(result) == 1
        assert len(result[0]) == 800
    
    def test_two_chunks_1600_chars(self):
        """測試兩個 chunk 1600 字"""
        processor = TextProcessor(max_chunk_size=800)
        text = "測" * 1600
        result = processor._preprocess_text(text)
        assert len(result) == 2
        assert all(len(c) <= 800 for c in result)
    
    def test_semantic_split_at_period(self):
        """測試在句號處分段"""
        processor = TextProcessor(max_chunk_size=800)
        text = "第一句。" + "測" * 900 + "第二句。"
        result = processor._preprocess_text(text)
        # 應該在句號處分段
        assert len(result) >= 2
    
    def test_newline_split(self):
        """測試換行分段"""
        processor = TextProcessor()
        text = "第一行\n第二行\n第三行"
        result = processor._preprocess_text(text)
        # 換行應該被視為分段點
        assert len(result) >= 1
    
    def test_long_sentence_without_punctuation(self):
        """測試無標點長句（需強制截斷）"""
        processor = TextProcessor(max_chunk_size=800)
        text = "測" * 1200  # 沒有標點的長句
        result = processor._preprocess_text(text)
        # 應該被強制分段
        assert len(result) >= 2
        assert all(len(c) <= 800 for c in result)
    
    def test_mixed_content(self):
        """測試混合內容（段落、標點、空行）"""
        processor = TextProcessor()
        text = """
這是一個測試。

第一段文字，包含多個句子。第一句話。第二句話。第三句話。

第二段文字，同樣包含多個句子。
"""
        result = processor._preprocess_text(text)
        assert len(result) >= 1
        assert all(len(c) <= 800 for c in result)
    
    def test_validate_chunk_valid(self):
        """測試 chunk 驗證 - 合法"""
        processor = TextProcessor()
        assert processor.validate_chunk("合法 chunk") == True
    
    def test_validate_chunk_empty(self):
        """測試 chunk 驗證 - 空"""
        processor = TextProcessor()
        assert processor.validate_chunk("") == False
    
    def test_validate_chunk_too_long(self):
        """測試 chunk 驗證 - 過長"""
        processor = TextProcessor(max_chunk_size=100)
        assert processor.validate_chunk("x" * 101) == False
    
    def test_validate_chunks(self):
        """測試多個 chunks 驗證"""
        processor = TextProcessor()
        chunks = ["chunk1", "chunk2", "chunk3"]
        assert processor.validate_chunks(chunks) == True
    
    def test_get_chunk_count(self):
        """測試取得 chunk 數量"""
        processor = TextProcessor(max_chunk_size=800)
        text = "測" * 2000
        count = processor.get_chunk_count(text)
        assert count >= 2
    
    def test_clean_text(self):
        """測試文字清洗"""
        processor = TextProcessor()
        text = "  多个   空白   "
        result = processor._clean_text(text)
        assert "  " not in result
    
    def test_preserve_meaningful_newlines(self):
        """測試保留有意義的換行"""
        processor = TextProcessor()
        text = "第一行\n第二行\n\n第四行"
        result = processor._clean_text(text)
        assert "\n" in result
        # 多餘換行應被合併
        assert "\n\n\n" not in result


class TestTextProcessorEdgeCases:
    """TextProcessor 邊界案例測試"""
    
    def test_unicode_text(self):
        """測試 Unicode 文字（中文）"""
        processor = TextProcessor()
        text = "這是繁體中文字。測試內容。"
        result = processor._preprocess_text(text)
        assert len(result) >= 1
    
    def test_mixed_language(self):
        """測試混合語言"""
        processor = TextProcessor()
        text = "Hello World 你好世界 123 ABC"
        result = processor._preprocess_text(text)
        assert len(result) >= 1
    
    def test_special_characters(self):
        """測試特殊字元"""
        processor = TextProcessor()
        text = "特殊字元：@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = processor._preprocess_text(text)
        assert len(result) >= 1
    
    def test_max_chunk_size_boundary(self):
        """測試最大 chunk 大小邊界"""
        processor = TextProcessor(max_chunk_size=1)
        text = "AB"
        result = processor._preprocess_text(text)
        assert len(result) == 2
        assert all(len(c) == 1 for c in result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])