"""Tests for TextWindow class."""

import pytest
from unittest.mock import Mock, patch
from blessed import Terminal
from blessed.keyboard import Keystroke
from term_windows import TextWindow


def create_mock_terminal(width=80, height=24):
    """Create a mock Terminal with specified dimensions."""
    term = Mock(spec=Terminal)
    term.width = width
    term.height = height
    term.move = Mock(return_value='')
    return term


class TestTextWindow:
    """Tests for the TextWindow class."""
    
    def test_string_text_initialization(self):
        """Test initialization with string text."""
        term = Terminal()
        window = TextWindow(
            text="Line 1\nLine 2\nLine 3",
            term=term
        )
        
        assert window.text == "Line 1\nLine 2\nLine 3"
        assert window.scroll == 0
    
    def test_list_text_initialization(self):
        """Test initialization with list of lines."""
        term = Terminal()
        window = TextWindow(
            text=["Line 1", "Line 2", "Line 3"],
            term=term
        )
        
        assert window.text == "Line 1\nLine 2\nLine 3"
    
    def test_tuple_text_initialization(self):
        """Test initialization with tuple of lines."""
        term = Terminal()
        window = TextWindow(
            text=("Line 1", "Line 2"),
            term=term
        )
        
        assert window.text == "Line 1\nLine 2"
    
    def test_handle_resize_text_wrapping(self):
        """Test that handle_resize wraps text correctly."""
        term = create_mock_terminal(80, 24)
        
        window = TextWindow(
            text="This is a very long line that should be wrapped to fit within the window width",
            term=term
        )
        
        # Trigger resize to calculate wrapped lines
        window.handle_resize()
        
        # Should have wrapped the text
        assert len(window._lines) > 1
        # All lines should fit within max width
        max_content_width = int(term.width * 0.9) + window.content.offsets.width - 2
        for line in window._lines:
            assert len(line) <= max_content_width
    
    def test_handle_input_scroll_down(self):
        """Test scrolling down with arrow key."""
        term = create_mock_terminal(80, 24)
        
        # Create text with many lines
        text = "\n".join(f"Line {i}" for i in range(50))
        window = TextWindow(text=text, term=term)
        window.handle_resize()  # Initialize _lines
        
        initial_scroll = window.scroll
        key = Mock(spec=Keystroke)
        key.name = 'KEY_DOWN'
        
        window.handle_input(key)
        
        # Should have scrolled down if there's room
        if len(window._lines) > window.content.height:
            assert window.scroll > initial_scroll
            assert window.redraw is True
    
    def test_handle_input_scroll_up(self):
        """Test scrolling up with arrow key."""
        term = create_mock_terminal(80, 24)
        
        text = "\n".join(f"Line {i}" for i in range(50))
        window = TextWindow(text=text, term=term)
        window.handle_resize()
        
        # Scroll down first
        window.scroll = 10
        
        key = Mock(spec=Keystroke)
        key.name = 'KEY_UP'
        
        initial_scroll = window.scroll
        window.handle_input(key)
        
        # Should have scrolled up
        assert window.scroll < initial_scroll
        assert window.redraw is True
    
    def test_handle_input_scroll_up_at_top(self):
        """Test that scrolling up at top doesn't go negative."""
        term = create_mock_terminal(80, 24)
        
        text = "\n".join(f"Line {i}" for i in range(50))
        window = TextWindow(text=text, term=term)
        window.handle_resize()
        
        window.scroll = 0
        
        key = Mock(spec=Keystroke)
        key.name = 'KEY_UP'
        
        window.handle_input(key)
        
        # Should still be at 0
        assert window.scroll == 0
    
    def test_handle_input_page_down(self):
        """Test page down scrolling."""
        term = create_mock_terminal(80, 24)
        
        text = "\n".join(f"Line {i}" for i in range(50))
        window = TextWindow(text=text, term=term)
        window.handle_resize()
        
        initial_scroll = window.scroll
        key = Mock(spec=Keystroke)
        key.name = 'KEY_PGDOWN'
        
        window.handle_input(key)
        
        # Should have scrolled by at least one page
        if len(window._lines) > window.content.height:
            assert window.scroll >= initial_scroll + window.content.height
            assert window.redraw is True
    
    def test_handle_input_page_up(self):
        """Test page up scrolling."""
        term = create_mock_terminal(80, 24)
        
        text = "\n".join(f"Line {i}" for i in range(50))
        window = TextWindow(text=text, term=term)
        window.handle_resize()
        
        # Scroll down first
        window.scroll = 30
        
        key = Mock(spec=Keystroke)
        key.name = 'KEY_PGUP'
        
        initial_scroll = window.scroll
        window.handle_input(key)
        
        # Should have scrolled up by at least one page
        assert window.scroll <= initial_scroll - window.content.height
        assert window.redraw is True
    
    def test_handle_input_escape_closes(self):
        """Test that ESC closes the window."""
        term = Terminal()
        window = TextWindow(text="Test", term=term)
        
        key = Mock(spec=Keystroke)
        key.name = 'KEY_ESCAPE'
        
        assert window.closed is False
        window.handle_input(key)
        assert window.closed is True
    
    def test_scroll_pos_calculation(self):
        """Test that scroll_pos is calculated correctly."""
        term = create_mock_terminal(80, 24)
        
        text = "\n".join(f"Line {i}" for i in range(50))
        window = TextWindow(text=text, term=term)
        window.handle_resize()
        
        total_lines = len(window._lines)
        max_height = window.content.height
        
        if total_lines > max_height:
            window.scroll = 10
            window.draw()
            
            # scroll_pos should be between 0 and 1
            assert window.scroll_pos is not None
            assert 0.0 <= window.scroll_pos <= 1.0
        else:
            # No scrolling needed
            window.draw()
            assert window.scroll_pos is None
    
    def test_status_bar_updates(self):
        """Test that status bar updates based on scrollability."""
        term = create_mock_terminal(80, 24)
        
        # Short text (no scrolling)
        window1 = TextWindow(text="Short text", term=term)
        window1.handle_resize()
        window1.draw()
        assert window1.status_bar == '[Esc=Close]'
        
        # Long text (scrolling)
        text = "\n".join(f"Line {i}" for i in range(50))
        window2 = TextWindow(text=text, term=term)
        window2.handle_resize()
        window2.draw()
        assert '[Arrows' in window2.status_bar or '[PgUp' in window2.status_bar
    
    def test_empty_text(self):
        """Test handling of empty text."""
        term = Terminal()
        window = TextWindow(text="", term=term)
        window.handle_resize()
        
        # Should have at least one empty line
        assert len(window._lines) >= 1
    
    def test_window_sizing_to_fit_content(self):
        """Test that window sizes itself to fit content."""
        term = create_mock_terminal(80, 24)
        
        # Short text
        window = TextWindow(text="Short", term=term)
        window.handle_resize()
        
        # Window should be sized appropriately
        assert window.position.width <= int(term.width * 0.9)
        assert window.position.height <= int(term.height * 0.9)
        assert window.position.width >= 10  # Minimum width
        assert window.position.height >= 6   # Minimum height

