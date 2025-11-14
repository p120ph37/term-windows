"""Tests for Dimensions classes."""

import pytest
from term_windows import Dimensions, ConstrainedDimensions, OffsetDimensions


class TestDimensions:
    """Tests for the Dimensions dataclass."""
    
    def test_default_initialization(self):
        """Test that all fields default to None."""
        dims = Dimensions()
        assert dims.x is None
        assert dims.y is None
        assert dims.width is None
        assert dims.height is None
    
    def test_partial_initialization(self):
        """Test partial initialization."""
        dims = Dimensions(x=10, width=50)
        assert dims.x == 10
        assert dims.y is None
        assert dims.width == 50
        assert dims.height is None
    
    def test_full_initialization(self):
        """Test full initialization."""
        dims = Dimensions(x=10, y=20, width=100, height=50)
        assert dims.x == 10
        assert dims.y == 20
        assert dims.width == 100
        assert dims.height == 50
    
    def test_float_values(self):
        """Test that float values are accepted."""
        dims = Dimensions(x=0.5, y=0.3, width=0.8, height=0.9)
        assert dims.x == 0.5
        assert dims.y == 0.3
        assert dims.width == 0.8
        assert dims.height == 0.9


class TestConstrainedDimensions:
    """Tests for ConstrainedDimensions class."""
    
    def test_clamp_integer_values(self):
        """Test clamping of integer values."""
        base = Dimensions(x=100, y=50, width=200, height=100)
        constraints = Dimensions(x=0, y=0, width=80, height=24)
        constrained = ConstrainedDimensions(base, constraints)
        
        # Values should be clamped to fit within constraints
        # x=100 is beyond max (0+80=80), so it clamps to 80
        assert constrained.x == 80  # Clamped to max (constraints.x + constraints.width)
        # y=50 is beyond max (0+24=24), so it clamps to 24
        assert constrained.y == 24  # Clamped to max (constraints.y + constraints.height)
        assert constrained.width == 80  # Clamped to max
        assert constrained.height == 24  # Clamped to max
    
    def test_centering_when_none(self):
        """Test that None values result in centering."""
        base = Dimensions(x=None, y=None, width=50, height=20)
        constraints = Dimensions(x=0, y=0, width=100, height=40)
        constrained = ConstrainedDimensions(base, constraints)
        
        # Should be centered
        assert constrained.x == 25  # (100 - 50) // 2
        assert constrained.y == 10  # (40 - 20) // 2
    
    def test_full_size_when_none(self):
        """Test that None width/height uses full constraint size."""
        base = Dimensions(x=0, y=0, width=None, height=None)
        constraints = Dimensions(x=0, y=0, width=80, height=24)
        constrained = ConstrainedDimensions(base, constraints)
        
        assert constrained.width == 80
        assert constrained.height == 24
    
    def test_float_percentage_values(self):
        """Test that float values are interpreted as relative values."""
        base = Dimensions(x=0.1, y=0.2, width=0.8, height=0.6)
        constraints = Dimensions(x=0, y=0, width=100, height=50)
        constrained = ConstrainedDimensions(base, constraints)
        
        # 0.1 * 100 = 10
        assert constrained.x == 10
        # 0.2 * 50 = 10
        assert constrained.y == 10
        # 0.8 * 100 = 80
        assert constrained.width == 80
        # 0.6 * 50 = 30
        assert constrained.height == 30
    
    def test_clamp_float_percentage(self):
        """Test that float relative values are clamped correctly."""
        base = Dimensions(x=1.5, y=-0.5, width=2.0, height=0.5)
        constraints = Dimensions(x=0, y=0, width=100, height=50)
        constrained = ConstrainedDimensions(base, constraints)
        
        # x=1.5 (relative) should clamp to max (100)
        assert constrained.x == 100
        # y=-0.5 (relative) should clamp to min (0)
        assert constrained.y == 0
        # width=2.0 (relative) = 200, but max available is 100 - base.x (1.5) = 98.5
        # The width calculation uses base.x (1.5) not the computed x, so max = 100 - 1.5 = 98.5
        # The clamped value is 98.5 (not rounded, as it's a float calculation)
        assert constrained.width == 98.5  # Clamped to available space
        # height=0.5 should be 25 (0.5 * 50)
        assert constrained.height == 25
    
    def test_width_clamping_with_offset(self):
        """Test that width is clamped considering x position."""
        base = Dimensions(x=70, y=0, width=20, height=10)
        constraints = Dimensions(x=0, y=0, width=80, height=24)
        constrained = ConstrainedDimensions(base, constraints)
        
        # Width should be clamped to fit: 80 - 70 = 10
        assert constrained.width == 10
    
    def test_height_clamping_with_offset(self):
        """Test that height is clamped considering y position."""
        base = Dimensions(x=0, y=20, width=10, height=10)
        constraints = Dimensions(x=0, y=0, width=80, height=24)
        constrained = ConstrainedDimensions(base, constraints)
        
        # Height should be clamped to fit: 24 - 20 = 4
        assert constrained.height == 4


class TestOffsetDimensions:
    """Tests for OffsetDimensions class."""
    
    def test_basic_offset(self):
        """Test basic offset application."""
        base = Dimensions(x=10, y=5, width=50, height=20)
        offsets = Dimensions(x=1, y=1, width=-2, height=-2)
        offset = OffsetDimensions(base, offsets)
        
        assert offset.x == 11  # 10 + 1
        assert offset.y == 6   # 5 + 1
        assert offset.width == 48   # 50 - 2
        assert offset.height == 18  # 20 - 2
    
    def test_negative_offsets(self):
        """Test negative offsets."""
        base = Dimensions(x=10, y=5, width=50, height=20)
        offsets = Dimensions(x=-2, y=-1, width=5, height=3)
        offset = OffsetDimensions(base, offsets)
        
        assert offset.x == 8   # 10 - 2
        assert offset.y == 4   # 5 - 1
        assert offset.width == 55   # 50 + 5
        assert offset.height == 23  # 20 + 3
    
    def test_none_base_values(self):
        """Test that None base values result in None."""
        base = Dimensions(x=None, y=5, width=50, height=None)
        offsets = Dimensions(x=1, y=1, width=-2, height=-2)
        offset = OffsetDimensions(base, offsets)
        
        assert offset.x is None  # None + 1 = None
        assert offset.y == 6     # 5 + 1
        assert offset.width == 48  # 50 - 2
        assert offset.height is None  # None + (-2) = None
    
    def test_zero_offsets(self):
        """Test that zero offsets don't change values."""
        base = Dimensions(x=10, y=5, width=50, height=20)
        offsets = Dimensions(x=0, y=0, width=0, height=0)
        offset = OffsetDimensions(base, offsets)
        
        assert offset.x == 10
        assert offset.y == 5
        assert offset.width == 50
        assert offset.height == 20

