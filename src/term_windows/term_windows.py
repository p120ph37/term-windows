"""
Core window classes for terminal-based UIs.

This module provides the base classes for creating terminal windows with borders,
layout constraints, input handling, and a reusable controller for window stacks.
"""

import signal
import textwrap
import time
from dataclasses import dataclass
from typing import List, Optional, Union

from blessed import Terminal


@dataclass
class Dimensions:
    """Represents window dimensions (position and size).
    
    All fields are optional and can be None, int, or float.
    Float values are interpreted as relative values (0.0 to 1.0) when used
    in ConstrainedDimensions, representing a fraction of the container size.
    """
    x: Optional[Union[int, float]] = None
    y: Optional[Union[int, float]] = None
    width: Optional[Union[int, float]] = None
    height: Optional[Union[int, float]] = None


class ConstrainedDimensions:
    """Dimensions that are constrained within a parent container.
    
    This class is used to constrain window dimensions within a parent container,
    typically the terminal screen or a parent window. It ensures windows fit
    within the available space by automatically clamping positions and sizes.
    
    This is the primary mechanism for positioning and sizing windows within the
    terminal. When a window is created, its position and size are constrained
    to ensure it fits within the terminal bounds, preventing overflow.
    
    Float values in base dimensions are interpreted as relative values (0.0 to 1.0)
    representing a fraction of the constraint size. For example, width=0.8 means
    80% of the container width. Using relative positioning enables cascading
    dynamic resizing: when the terminal window is resized, all UI elements using
    relative dimensions automatically resize proportionally, maintaining their
    layout relationships.
    
    Attributes:
        base: The base dimensions to constrain (desired position/size)
        constraints: The constraint bounds (typically the terminal or parent window size)
    """
    
    def __init__(self, base: Dimensions, constraints: Dimensions):
        self.base = base
        self.constraints = constraints

    @staticmethod
    def _clamp(val, minval, maxval):
        """Clamp a value between min and max, handling relative float values."""
        if isinstance(val, float):
            # Interpret as relative value (0.0-1.0) and scale to container size
            return max(minval, min(maxval, int(round(minval + val * (maxval - minval)))))
        else:
            return max(minval, min(maxval, val))

    @property
    def x(self):
        """X position, centered if base.x is None."""
        if self.base.x is None:
            return self.constraints.x + (self.constraints.width - self.width) // 2
        else:
            return ConstrainedDimensions._clamp(
                self.base.x, 
                self.constraints.x, 
                self.constraints.x + self.constraints.width
            )

    @property
    def y(self):
        """Y position, centered if base.y is None."""
        if self.base.y is None:
            return self.constraints.y + (self.constraints.height - self.height) // 2
        else:
            return ConstrainedDimensions._clamp(
                self.base.y, 
                self.constraints.y, 
                self.constraints.y + self.constraints.height
            )

    @property
    def width(self):
        """Width, constrained to fit within parent."""
        if self.base.width is None:
            return self.constraints.width
        clamped = ConstrainedDimensions._clamp(
            self.base.width, 
            0, 
            self.constraints.width - (self.base.x or 0)
        )
        return clamped or self.constraints.width

    @property
    def height(self):
        """Height, constrained to fit within parent."""
        if self.base.height is None:
            return self.constraints.height
        clamped = ConstrainedDimensions._clamp(
            self.base.height, 
            0, 
            self.constraints.height - (self.base.y or 0)
        )
        return clamped or self.constraints.height


class OffsetDimensions:
    """Dimensions offset from a base position.
    
    This is used to calculate content area within a window (accounting for borders).
    
    Attributes:
        base: The base dimensions
        offsets: The offset to apply to each dimension
    """
    
    def __init__(self, base: Dimensions, offsets: Dimensions):
        self.base = base
        self.offsets = offsets

    @property
    def x(self):
        """X position with offset applied."""
        return self.base.x + self.offsets.x if self.base.x is not None else None

    @property
    def y(self):
        """Y position with offset applied."""
        return self.base.y + self.offsets.y if self.base.y is not None else None

    @property
    def width(self):
        """Width with offset applied."""
        return self.base.width + self.offsets.width if self.base.width is not None else None

    @property
    def height(self):
        """Height with offset applied."""
        return self.base.height + self.offsets.height if self.base.height is not None else None


class Window:
    """Base class for terminal windows.
    
    Provides border drawing, input handling, and layout management.
    Windows can have child windows that appear on top (modal dialogs).
    
    Attributes:
        title: Window title displayed in top border
        border: Whether to draw a border around the window
        status_bar: Status text displayed in bottom border
        scroll_pos: Scroll position (0.0 to 1.0) for scrollbar display, or None
        closed: Whether the window has been closed
        child: Child window to display on top (for modals)
        position: ConstrainedDimensions for window position and size
        content: OffsetDimensions for content area (inside borders)
        term: Blessed Terminal instance
        redraw: Whether the window needs to be redrawn
    """
    
    def __init__(self, title="", width=None, height=None, border=True, 
                 status_bar=None, x=None, y=None, term=None):
        self.title = title
        self.border = border
        self.status_bar = status_bar or '[Esc=Close]'
        self.scroll_pos = None
        self.closed = False
        self.child = None
        self.controller = None
        
        if term is None:
            term = Terminal()
        
        # Use property setter to trigger handle_resize()
        self._term = None  # Initialize first
        self.position = ConstrainedDimensions(
            Dimensions(x, y, width, height), 
            Dimensions(0, 0, term.width, term.height)
        )
        self.content = OffsetDimensions(
            self.position, 
            Dimensions(1, 1, -2, -2) if self.border else Dimensions(0, 0, 0, 0)
        )
        self.term = term  # Use setter to trigger handle_resize()
        self.redraw = True

    @property
    def term(self):
        """Blessed Terminal instance."""
        return self._term

    @term.setter
    def term(self, value):
        """Set terminal and handle resize."""
        self._term = value
        self.handle_resize()

    def draw(self):
        """Draw the window border and content.
        
        Subclasses should call super().draw() first, then draw their content.
        """
        self.redraw = False
        if not self.border:
            return
        
        # Top border with title
        title_text = f' {self.title} '.center(self.position.width - 2, '-')
        title_text = title_text[:self.position.width - 2]
        corner = '+' if self.scroll_pos is None else '^'
        print(
            self.term.move(self.position.y, self.position.x) +
            '+' + title_text + corner,
            end=''
        )
        
        # Bottom border with status bar
        info = f' {self.status_bar} ' if self.status_bar else ''
        dashes = '-' * max(0, self.position.width - 2 - len(info))
        corner = '+' if self.scroll_pos is None else 'v'
        print(
            self.term.move(self.position.y + self.position.height - 1, self.position.x) +
            '+' + dashes + info + corner,
            end=''
        )
        
        # Left and right borders (with scrollbar indicator)
        scroll_row = None if self.scroll_pos is None else int(self.scroll_pos * self.content.height)
        for row in range(self.content.height):
            right_char = '=' if row == scroll_row else '|'
            print(
                self.term.move(self.content.y + row, self.position.x) +
                '|' +
                (' ' * (self.position.width - 2)) +
                self.term.move(self.content.y + row, self.position.x + self.position.width - 1) +
                right_char,
                end=''
            )
        print('', end='', flush=True)

    def handle_input(self, key):
        """Handle keyboard input.
        
        Args:
            key: Blessed Keystroke object
            
        Subclasses should override this to handle their specific input.
        """
        if key.name == 'KEY_ESCAPE':
            self.close()

    def handle_resize(self):
        """Handle terminal resize.
        
        Updates constraint dimensions to match new terminal size.
        Subclasses should call super().handle_resize() and update their layout.
        """
        self.position.constraints.x = 0
        self.position.constraints.y = 0
        self.position.constraints.width = self.term.width
        self.position.constraints.height = self.term.height

    def close(self):
        """Mark the window as closed.
        
        The window stack manager should remove closed windows from the stack.
        """
        self.closed = True

    def tick(self):
        """Called periodically to update window state.
        
        Subclasses can override this for animations or periodic updates.
        """
        pass


class TextWindow(Window):
    """A window that displays scrollable text content.
    
    Automatically wraps text to fit the window width and provides
    keyboard scrolling controls.
    """
    
    def __init__(self, text, *args, **kwargs):
        """Initialize a text window.
        
        Args:
            text: Text content (string, list, or tuple of lines)
            *args, **kwargs: Passed to Window.__init__()
        """
        self.text = "\n".join(text) if isinstance(text, (list, tuple)) else text
        self.scroll = 0
        self._lines = []
        super().__init__(*args, **kwargs)

    def draw(self):
        """Draw the window with text content."""
        max_content_height = self.content.height
        total_lines = len(self._lines)
        below_the_fold = total_lines - max_content_height
        
        # Update scroll position indicator
        self.scroll_pos = None
        if below_the_fold > 0:
            self.scroll_pos = self.scroll / below_the_fold
            self.status_bar = '[Arrows/PgUp/PgDn=Scroll, Esc=Close]'
        else:
            self.status_bar = '[Esc=Close]'
        
        # Draw border
        super().draw()
        
        # Draw text lines
        for i in range(max_content_height):
            line_idx = self.scroll + i
            if line_idx < total_lines:
                line = self._lines[line_idx][:self.content.width - 2]
            else:
                line = ""
            print(
                self.term.move(self.content.y + i, self.content.x + 1) + 
                line.ljust(self.content.width - 2),
                end=''
            )
        print('', end='', flush=True)

    def handle_input(self, key):
        """Handle scrolling input."""
        max_content_height = self.content.height
        total_lines = len(self._lines)
        
        if total_lines > max_content_height:
            match key.name:
                case 'KEY_DOWN':
                    if self.scroll < total_lines - max_content_height:
                        self.scroll += 1
                        self.redraw = True
                case 'KEY_UP':
                    if self.scroll > 0:
                        self.scroll -= 1
                        self.redraw = True
                case 'KEY_PGDOWN':
                    if self.scroll < total_lines - max_content_height:
                        self.scroll = min(
                            self.scroll + max_content_height, 
                            total_lines - max_content_height
                        )
                        self.redraw = True
                case 'KEY_PGUP':
                    if self.scroll > 0:
                        self.scroll = max(self.scroll - max_content_height, 0)
                        self.redraw = True
                case _:
                    super().handle_input(key)
        else:
            super().handle_input(key)

    def handle_resize(self):
        """Recalculate text wrapping on resize."""
        super().handle_resize()
        max_win_width = int(self.position.constraints.width * 0.9)
        max_win_height = int(self.position.constraints.height * 0.9)
        max_content_width = max_win_width + self.content.offsets.width - 2
        
        # Re-wrap text
        self._lines = []
        for line in self.text.splitlines() or ['']:
            self._lines.extend(textwrap.wrap(line, max_content_width) or [''])
        
        # Adjust window size to fit content
        max_line_length = max(len(line) + 2 for line in self._lines) if self._lines else 0
        self.position.base.width = max(
            10, 
            min(max_win_width, max_line_length - self.content.offsets.width)
        )
        self.position.base.height = max(
            6, 
            min(max_win_height, len(self._lines) - self.content.offsets.height)
        )
        self.redraw = True


class WindowController:
    """Abstract helper that manages a window stack and event loop.

    Subclasses are responsible for pushing their initial windows (typically in
    ``__init__``) using :meth:`push_window`. The controller handles keyboard routing,
    redraws, terminal resize, and window lifecycle management.
    """

    def __init__(
        self,
        *,
        term: Optional[Terminal] = None,
        inkey_timeout: float = 0.1,
        idle_sleep: float = 0.01,
        register_resize_handler: bool = True,
    ):
        self.term = term or Terminal()
        self.inkey_timeout = inkey_timeout
        self.idle_sleep = idle_sleep
        self.window_stack: List[Window] = []
        self._resize_pending = False
        if register_resize_handler:
            signal.signal(signal.SIGWINCH, self._handle_sigwinch)

    def _handle_sigwinch(self, signum, frame):
        """Refresh Terminal on resize and trigger a redraw."""
        self.term = Terminal()
        self._resize_pending = True

    def push_window(self, window: Window):
        """Push a window onto the stack."""
        window.term = self.term
        window.redraw = True
        window.controller = self
        self.window_stack.append(window)

    def pop_window(self):
        """Pop the top window off the stack."""
        if self.window_stack:
            popped = self.window_stack.pop()
            popped.controller = None
            if self.window_stack:
                parent = self.window_stack[-1]
                parent.child = None
                parent.redraw = True
            return popped
        return None

    def current_window(self) -> Optional[Window]:
        """Return the top-most window, if any."""
        return self.window_stack[-1] if self.window_stack else None

    def on_tick(self):
        """Optional hook executed once per loop iteration after window ticks."""

    def run(self):
        """Enter the main event loop."""
        if not self.window_stack:
            raise RuntimeError(
                "WindowController.run() called with no windows. "
                "Call push_window() before run()."
            )

        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            self._redraw_top(force=True)

            while self.window_stack:
                if self._resize_pending:
                    self._process_resize()

                window = self.current_window()
                key = self.term.inkey(timeout=self.inkey_timeout)

                if key and window:
                    self._handle_key(window, key)
                    if not self.window_stack:
                        break

                self._redraw_top()

                if self.window_stack:
                    self.window_stack[-1].tick()
                    self.on_tick()

                time.sleep(self.idle_sleep)

    def _handle_key(self, window: Window, key):
        """Dispatch keyboard input to the active window."""
        window.handle_input(key)

        if window.closed:
            self.pop_window()
            return

        if window.child:
            self.push_window(window.child)
            window.child = None

    def _process_resize(self):
        """Re-render windows after a terminal resize."""
        self._resize_pending = False
        print(self.term.clear(), end="")
        for win in self.window_stack:
            win.term = self.term
            win.redraw = True
        self._redraw_top(force=True)

    def _redraw_top(self, force: bool = False):
        """Redraw the top-most window if it requested it."""
        top = self.current_window()
        if not top:
            return
        if force or getattr(top, "redraw", False):
            top.redraw = False
            top.draw()

