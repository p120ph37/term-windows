"""Tests for Window class."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from blessed import Terminal
from blessed.keyboard import Keystroke
from term_windows import Window, Dimensions


class TestWindow:
    """Tests for the Window class."""
    
    def test_default_initialization(self):
        """Test default window initialization."""
        term = Terminal()
        window = Window(term=term)
        
        assert window.title == ""
        assert window.border is True
        assert window.status_bar == '[Esc=Close]'
        assert window.scroll_pos is None
        assert window.closed is False
        assert window.child is None
        assert window.redraw is True
        assert window.term == term
    
    def test_custom_initialization(self):
        """Test custom window initialization."""
        term = Terminal()
        window = Window(
            title="Test Window",
            width=80,
            height=24,
            border=False,
            status_bar="Custom status",
            x=10,
            y=5,
            term=term
        )
        
        assert window.title == "Test Window"
        assert window.border is False
        assert window.status_bar == "Custom status"
        assert window.term == term
    
    def test_term_property_setter(self):
        """Test that setting term triggers handle_resize."""
        term1 = Terminal()
        term2 = Terminal()
        window = Window(term=term1)
        
        # Mock handle_resize to verify it's called
        window.handle_resize = Mock()
        window.term = term2
        
        assert window.term == term2
        window.handle_resize.assert_called_once()
    
    def test_handle_resize(self):
        """Test handle_resize updates constraints."""
        term = Terminal()
        window = Window(term=term)
        
        # Change terminal size (simulated)
        window.term = Terminal()
        window.handle_resize()
        
        # Constraints should match terminal size
        assert window.position.constraints.x == 0
        assert window.position.constraints.y == 0
        assert window.position.constraints.width == window.term.width
        assert window.position.constraints.height == window.term.height
    
    def test_close(self):
        """Test that close() sets closed flag."""
        term = Terminal()
        window = Window(term=term)
        
        assert window.closed is False
        window.close()
        assert window.closed is True
    
    def test_handle_input_escape(self):
        """Test that ESC key closes window."""
        term = Terminal()
        window = Window(term=term)
        
        # Create a mock keystroke
        key = Mock(spec=Keystroke)
        key.name = 'KEY_ESCAPE'
        
        assert window.closed is False
        window.handle_input(key)
        assert window.closed is True
    
    def test_handle_input_other_key(self):
        """Test that other keys don't close window."""
        term = Terminal()
        window = Window(term=term)
        
        # Create a mock keystroke
        key = Mock(spec=Keystroke)
        key.name = 'KEY_ENTER'
        
        assert window.closed is False
        window.handle_input(key)
        assert window.closed is False
    
    def test_tick(self):
        """Test that tick() can be called without error."""
        term = Terminal()
        window = Window(term=term)
        
        # Should not raise
        window.tick()
    
    def test_draw_no_border(self):
        """Test that draw() does nothing when border is False."""
        term = Terminal()
        window = Window(border=False, term=term)
        
        # Should not raise and should set redraw to False
        window.draw()
        assert window.redraw is False
    
    @patch('builtins.print')
    def test_draw_with_border(self, mock_print):
        """Test that draw() draws border when border is True."""
        # Create a mock terminal with required attributes
        term = Mock(spec=Terminal)
        term.move = Mock(return_value='')
        term.width = 80
        term.height = 24
        
        window = Window(
            title="Test",
            width=50,
            height=20,
            term=term
        )
        
        # Calculate expected content height
        content_height = window.content.height
        
        window.draw()
        
        # Should have called print multiple times (top border, bottom border, sides)
        assert mock_print.call_count >= content_height + 2
        assert window.redraw is False
    
    def test_child_window_assignment(self):
        """Test that child windows can be assigned."""
        term = Terminal()
        parent = Window(term=term)
        child = Window(title="Child", term=term)
        
        assert parent.child is None
        parent.child = child
        assert parent.child == child
    
    def test_content_dimensions_with_border(self):
        """Test that content area accounts for border."""
        term = Terminal()
        window = Window(
            width=50,
            height=20,
            border=True,
            term=term
        )
        
        # Content should be offset by 1 and reduced by 2
        assert window.content.x == window.position.x + 1
        assert window.content.y == window.position.y + 1
        assert window.content.width == window.position.width - 2
        assert window.content.height == window.position.height - 2
    
    def test_content_dimensions_without_border(self):
        """Test that content area matches position when no border."""
        term = Terminal()
        window = Window(
            width=50,
            height=20,
            border=False,
            term=term
        )
        
        # Content should match position (no offset)
        assert window.content.x == window.position.x
        assert window.content.y == window.position.y
        assert window.content.width == window.position.width
        assert window.content.height == window.position.height

