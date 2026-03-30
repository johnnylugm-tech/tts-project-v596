"""
文本處理器模組 (TextProcessor)

負責文本預處理與智慧分段，確保每段 ≤ 800 字元。

FR 對應：FR-02
"""

from typing import List


class TextProcessor:
    """
    文本預處理與分段器
    
    職責：
    - 文字清洗（移除多餘空白）
    - 智慧分段（800 字限制 + 語義边界保護）
    """
    
    def __init__(
        self,
        max_chunk_size: int = 800,
        semantic_markers: List[str] = None
    ):
        """
        初始化文本處理器
        
        參數：
            max_chunk_size: 最大分段字元數（預設 800）
            semantic_markers: 語義中断點列表
        """
        self._max_chunk_size = max_chunk_size
        self._semantic_markers = semantic_markers or ["。", "！", "？", "\n", "，", "；"]
    
    @property
    def max_chunk_size(self) -> int:
        """取得最大分段大小"""
        return self._max_chunk_size
    
    @property
    def semantic_markers(self) -> List[str]:
        """取得語義中断點列表"""
        return self._semantic_markers.copy()
    
    def _clean_text(self, text: str) -> str:
        """
        清洗文本，移除多餘空白
        
        規則：
        - 移除行首行尾空白
        - 將多個空白合併為單一空白
        - 保留換行符號（作為分段依據）
        """
        if not text:
            return ""
        
        # 移除行首行尾空白
        text = text.strip()
        
        # 將多個空白合併為單一空白
        import re
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 保留換行，但移除多餘換行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def _preprocess_text(self, text: str) -> List[str]:
        """
        預處理並分段文字
        
        步驟：
        1. 清洗文本
        2. 根據換行先分段
        3. 對每個段落執行語義分段
        4. 確保每個 chunk ≤ max_chunk_size
        
        參數：
            text: 原始文字
        
        回傳：分段後的字串列表
        
        FR 對應：FR-02
        
        保証：每個 chunk 長度 ≤ max_chunk_size
        """
        if not text:
            return []
        
        # Step 1: 清洗文本
        cleaned = self._clean_text(text)
        
        if not cleaned:
            return []
        
        # Step 2: 根據換行初步分段
        lines = cleaned.split('\n')
        
        chunks = []
        current_chunk = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 如果單行已經超過限制，需要特殊處理
            if len(line) > self._max_chunk_size:
                # 先輸出當前累積的 chunk
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # 對超長行進行強制分段
                sub_chunks = self._split_at_semantic_boundary(line, self._max_chunk_size)
                chunks.extend(sub_chunks)
            else:
                # 檢查加入這行後是否超過限制
                test_chunk = current_chunk + ("\n" if current_chunk else "") + line
                if len(test_chunk) <= self._max_chunk_size:
                    current_chunk = test_chunk
                else:
                    # 超過限制，先輸出當前 chunk
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    # 嘗試將新行作為下一個 chunk 的起點
                    if len(line) <= self._max_chunk_size:
                        current_chunk = line
                    else:
                        # 新行本身也超長，需要進一步分段
                        sub_chunks = self._split_at_semantic_boundary(line, self._max_chunk_size)
                        if sub_chunks:
                            current_chunk = sub_chunks[0]
                            chunks.extend(sub_chunks[1:])
                        else:
                            current_chunk = ""
        
        # 加入最後一個 chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        # Step 4: 最終驗證 - 嚴格確保每個 chunk ≤ max_chunk_size
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= self._max_chunk_size:
                final_chunks.append(chunk)
            else:
                # 二次分段（強制的字符截斷）
                sub_chunks = self._force_split(chunk, self._max_chunk_size)
                final_chunks.extend(sub_chunks)
        
        return final_chunks
    
    def _find_last_semantic_break(self, text: str, before_index: int) -> int:
        """
        找到指定位置之前的最後一個語義中断點
        
        參數：
            text: 待搜尋文字
            before_index: 參考位置
        
        回傳：最佳分段位置（索引），若找不到則回傳 -1
        """
        if not text or before_index <= 0:
            return -1
        
        # 在 [0, before_index) 範圍內找到最後一個語義中断點
        search_range = text[:before_index]
        
        for marker in self._semantic_markers:
            pos = search_range.rfind(marker)
            if pos != -1:
                # 找到時，將位置調整到標記符號之後（確保標記不被截斷）
                return pos + len(marker)
        
        return -1
    
    def _split_at_semantic_boundary(self, chunk: str, max_size: int) -> List[str]:
        """
        在語義边界分段
        
        優先在語義中断點（。！？，；\n）分段，
        若找不到，則強制在字符边界分段。
        
        參數：
            chunk: 待分段文字
            max_size: 最大分段大小
        
        回傳：分段後的字串列表
        
        FR 對應：FR-02
        """
        if not chunk:
            return []
        
        if len(chunk) <= max_size:
            return [chunk]
        
        # 找到最佳分段位置
        break_point = self._find_last_semantic_break(chunk, max_size)
        
        if break_point == -1:
            # 找不到語義中断點，強制在字符边界分段
            return self._force_split(chunk, max_size)
        
        # 遞迴處理剩餘部分
        first_part = chunk[:break_point].strip()
        remaining = chunk[break_point:].strip()
        
        result = []
        if first_part:
            result.append(first_part)
        
        if remaining:
            # 對剩餘部分繼續分段
            remaining_chunks = self._split_at_semantic_boundary(remaining, max_size)
            result.extend(remaining_chunks)
        
        return result
    
    def _force_split(self, text: str, max_size: int) -> List[str]:
        """
        強制字符截斷分段
        
        當找不到語義中断點時使用，
        直接在 max_size 位置截斷。
        
        參數：
            text: 待分段文字
            max_size: 最大分段大小
        
        回傳：分段後的字串列表
        """
        if not text:
            return []
        
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        while len(text) > max_size:
            chunks.append(text[:max_size])
            text = text[max_size:]
        
        if text:
            chunks.append(text)
        
        return chunks
    
    def get_chunk_count(self, text: str) -> int:
        """
        取得文字分段後的 chunk 數量
        
        參數：
            text: 原始文字
        
        回傳：chunk 數量
        """
        chunks = self._preprocess_text(text)
        return len(chunks)
    
    def validate_chunk(self, chunk: str) -> bool:
        """
        驗證 chunk 是否符合規範
        
        規則：
        - 長度 ≤ max_chunk_size
        - 不為空
        
        參數：
            chunk: 待驗證 chunk
        
        回傳：True 表示合法
        """
        return 0 < len(chunk) <= self._max_chunk_size
    
    def validate_chunks(self, chunks: List[str]) -> bool:
        """
        驗證所有 chunks 是否符合規範
        
        參數：
            chunks: chunk 列表
        
        回傳：True 表示全部合法
        """
        return all(self.validate_chunk(c) for c in chunks)


# ============================================================================
# 快捷工廠函數
# ============================================================================

def create_text_processor(
    max_chunk_size: int = 800,
    semantic_markers: List[str] = None
) -> TextProcessor:
    """
    建立 TextProcessor 實例
    
    參數：
        max_chunk_size: 最大分段大小（預設 800）
        semantic_markers: 語義中断點列表
    
    回傳：TextProcessor 實例
    """
    return TextProcessor(max_chunk_size=max_chunk_size, semantic_markers=semantic_markers) if semantic_markers else TextProcessor(max_chunk_size=max_chunk_size)