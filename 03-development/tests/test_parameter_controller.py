"""
測試 ParameterController 模組

FR 對應：FR-07
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts_project.parameter_controller import ParameterController


class TestParameterController:
    """ParameterController 測試案例"""
    
    def test_init_default(self):
        """測試預設初始化"""
        controller = ParameterController()
        assert controller.rate == "+0%"
        assert controller.volume == "+0%"
    
    def test_init_custom_rate(self):
        """測試自訂語速"""
        controller = ParameterController(rate="+20%")
        assert controller.rate == "+20%"
    
    def test_set_rate_valid(self):
        """測試設定有效語速"""
        controller = ParameterController()
        controller.set_rate("+30%")
        assert controller.rate == "+30%"
    
    def test_set_rate_invalid(self):
        """測試設定無效格式"""
        controller = ParameterController()
        with pytest.raises(ValueError):
            controller.set_rate("invalid")
    
    def test_set_volume_valid(self):
        """測試設定有效音量"""
        controller = ParameterController()
        controller.set_volume("+20%")
        assert controller.volume == "+20%"
    
    def test_get_rate(self):
        """測試取得語速"""
        controller = ParameterController(rate="+50%")
        assert controller.get_rate() == "+50%"
    
    def test_get_volume(self):
        """測試取得音量"""
        controller = ParameterController(volume="-20%")
        assert controller.get_volume() == "-20%"
    
    def test_to_dict(self):
        """測試轉換為字典"""
        controller = ParameterController(rate="+20%", volume="+10%")
        result = controller.to_dict()
        assert result == {"rate": "+20%", "volume": "+10%"}
    
    def test_reset(self):
        """測試重置"""
        controller = ParameterController(rate="+50%", volume="-30%")
        controller.reset()
        assert controller.rate == "+0%"
        assert controller.volume == "+0%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
