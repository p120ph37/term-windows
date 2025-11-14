# term-windows

A lightweight Python library for creating terminal-based windowed UIs using [Blessed](https://github.com/jquast/blessed). Provides window management, modal dialogs via a window stack, and automatic layout handling.

## Installation

```bash
pip install git+https://github.com/p120ph37/term-windows.git
```

Or with `uv`:

```bash
uv add "term-windows @ git+https://github.com/p120ph37/term-windows.git"
```

## Quick Start

```python
from blessed import Terminal
from term_windows import Window, TextWindow
import signal

term = Terminal()
resize_pending = False

def handle_sigwinch(signum, frame):
    global term, resize_pending
    term = Terminal()
    resize_pending = True

signal.signal(signal.SIGWINCH, handle_sigwinch)

class MainWindow(Window):
    def draw(self):
        super().draw()
        print(
            self.term.move(self.content.y, self.content.x) +
            "Press ? for help, Q to quit",
            end='', flush=True
        )
    
    def handle_input(self, key):
        if key.upper() == 'Q':
            self.close()
        elif key == '?':
            self.child = TextWindow(
                title="Help",
                text="This is a help dialog.\nPress ESC to close.",
                term=self.term
            )

def main():
    global resize_pending, term
    window_stack = [MainWindow(title="My App", term=term)]
    
    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        window_stack[-1].draw()
        
        while window_stack:
            # Handle terminal resize
            if resize_pending:
                resize_pending = False
                print(term.clear(), end='')
                for win in window_stack:
                    win.term = term
                window_stack[-1].draw()
            
            # Get input with timeout
            window = window_stack[-1]
            key = term.inkey(timeout=0.1)
            
            if key:
                window.handle_input(key)
                
                # Handle window lifecycle
                if window.closed:
                    window_stack.pop()
                    if window_stack:
                        window_stack[-1].child = None
                
                if window.child:
                    window_stack.append(window.child)
                    window_stack[-1].draw()
            
            # Periodic updates
            window_stack[-1].tick()

if __name__ == "__main__":
    main()
```

## Core Concepts

### Event Loop

The event loop is the heart of your application. It continuously:

1. **Checks for terminal resize** → Updates all windows if resized
2. **Gets keyboard input** → With timeout (typically 0.1s) to allow periodic updates
3. **Passes input to top window** → Only the active window receives input
4. **Manages window lifecycle** → Opens/closes windows based on state
5. **Calls tick()** → For animations, timers, or background updates

```python
while window_stack:
    # 1. Handle resize
    if resize_pending:
        resize_pending = False
        print(term.clear(), end='')
        for win in window_stack:
            win.term = term
        window_stack[-1].draw()
    
    # 2. Get input
    window = window_stack[-1]
    key = term.inkey(timeout=0.1)
    
    # 3. Handle input
    if key:
        window.handle_input(key)
        
        # 4. Manage lifecycle
        if window.closed:
            window_stack.pop()
            if window_stack:
                window_stack[-1].child = None
        
        if window.child:
            window_stack.append(window.child)
            window_stack[-1].draw()
    
    # 5. Periodic updates
    window_stack[-1].tick()
```

### Window Stack

The window stack manages which window is active. Windows are organized in a stack where:

- **Top window** (last in list) receives all input and is drawn on top
- **Opening a modal**: Set `window.child` to a new window, event loop pushes it onto stack
- **Closing a window**: Set `window.closed = True`, event loop pops it from stack
- **Stack empty**: Application exits

```python
# Stack progression:
[MainWindow]                    # Start
[MainWindow, HelpWindow]        # User pressed '?' → modal opens
[MainWindow]                    # User pressed ESC → modal closes
[]                              # User pressed 'Q' → app exits
```

To open a modal from within `handle_input()`:

```python
def handle_input(self, key):
    if key == '?':
        self.child = TextWindow(
            title="Help",
            text="Help content",
            term=self.term
        )
```

To close a window:

```python
def handle_input(self, key):
    if key.upper() == 'Q':
        self.close()  # Sets self.closed = True
```

#### Window Stack Best Practices

- **Single owner:** Keep one controller (or module-level helper) that owns the `window_stack` and runs the main loop. Child windows should only set `self.child = NewWindow(...)`; the controller is responsible for pushing/popping windows.
- **Input routing:** Always read keyboard input from the top-most window only. After a child is pushed, the parent should no longer receive keys until the child closes:

```python
window = window_stack[-1]
key = term.inkey(timeout=0.1)
if key:
    window.handle_input(key)
    if window.closed:
        window_stack.pop()
        if window_stack:
            window_stack[-1].child = None
    elif window.child:
        window_stack.append(window.child)
        window.child = None
```

- **Redraw semantics:** Let windows request repainting by setting `self.redraw = True`. After each iteration, the controller should check `window_stack[-1].redraw` and call `draw()` if needed so modals and selections stay responsive.
- **Tick & refresh:** Call `tick()` only on the active window. If background work (like refreshing discovery data) belongs to the root window, have that window set a flag in `handle_input()` and let the controller act on it after the tick.
- **Resize handling:** When a `SIGWINCH` fires, rebuild the global `Terminal`, update `win.term` for each window, mark them `redraw = True`, and let the next loop iteration repaint with the new dimensions.

Following this pattern prevents the parent window from consuming input while a modal is open and keeps the UI predictable across complex flows.

### WindowController (New!)

To remove most of the boilerplate required to manage the event loop, you can subclass `WindowController`. It owns the `window_stack`, handles SIGWINCH, routes input to the active window, and enforces the best practices above.

```python
from term_windows import Window, TextWindow, WindowController

class HostWindow(Window):
    ...

class MyApp(WindowController):
    def __init__(self):
        super().__init__(inkey_timeout=0.1)
        self.push_window(HostWindow(term=self.term))

    def on_tick(self):
        # Optional hook executed each loop iteration
        pass

if __name__ == "__main__":
    MyApp().run()
```

Inside your window classes, keep using `self.child = TextWindow(...)` or `self.close()`—the controller automatically pushes/pops windows, redraws them when `self.redraw = True`, and propagates resize events.

### Terminal Resize Handling

Use a signal handler to detect terminal resize events:

```python
term = Terminal()
resize_pending = False

def handle_sigwinch(signum, frame):
    global term, resize_pending
    term = Terminal()  # Refresh terminal dimensions
    resize_pending = True

signal.signal(signal.SIGWINCH, handle_sigwinch)

# In event loop:
if resize_pending:
    resize_pending = False
    print(term.clear(), end='')
    for win in window_stack:
        win.term = term  # Triggers win.handle_resize()
    window_stack[-1].draw()
```

## Window Classes

### Window (Base Class)

Create custom windows by subclassing `Window`:

```python
class MyWindow(Window):
    def __init__(self):
        super().__init__(
            title="My Window",
            width=80,           # Fixed or None for full width
            height=24,          # Fixed or None for full height
            x=None,            # None = centered
            y=None,            # None = centered
            border=True,       # Draw border
            status_bar="[Q=Quit]",
            term=term
        )
    
    def draw(self):
        super().draw()  # MUST call first to draw border
        # Draw your content using self.content dimensions
        print(
            self.term.move(self.content.y, self.content.x) +
            "Your content here",
            end='', flush=True
        )
    
    def handle_input(self, key):
        if key.upper() == 'Q':
            self.close()
        else:
            super().handle_input(key)  # ESC to close
    
    def tick(self):
        # Called every loop iteration (with timeout)
        # Use for animations, timers, etc.
        pass
    
    def handle_resize(self):
        super().handle_resize()  # MUST call first
        # Recalculate any layout-dependent data
```

**Key Properties:**

- `self.content`: Content area inside border (use for drawing)
- `self.position`: Full window dimensions including border
- `self.term`: Blessed Terminal instance
- `self.closed`: Set to `True` to close window
- `self.child`: Set to new Window to open modal
- `self.redraw`: Set to `True` to force redraw

**Important:** Use `self.content.x`, `self.content.y`, `self.content.width`, `self.content.height` for drawing to account for borders.

### TextWindow (Pre-built)

Scrollable text display with automatic wrapping:

```python
window = TextWindow(
    title="Document",
    text="Long text...",  # Or list/tuple of lines
    term=term
)
```

**Features:**
- Auto-wraps text to fit window
- Scrollable with arrow keys and PgUp/PgDn
- Auto-sizes to content (up to 90% of terminal)
- Shows scrollbar indicator when needed

## Layout and Sizing

### Fixed Size

```python
Window(width=80, height=24, x=10, y=5, term=term)
```

### Centered (Default)

```python
Window(width=80, height=24, term=term)  # x=None, y=None → centered
```

### Full Screen

```python
Window(term=term)  # width=None, height=None → full terminal
```

### Relative Size (Dynamic Resizing)

Use floats (0.0-1.0) for responsive layouts that adapt to terminal size:

```python
Window(
    width=0.8,   # 80% of terminal width
    height=0.9,  # 90% of terminal height
    term=term
)
```

When the terminal is resized, windows with relative dimensions automatically resize proportionally, maintaining their layout relationships.

## Practical Patterns

### Main Application Window

```python
class MainWindow(Window):
    def __init__(self, app_data):
        super().__init__(
            title="My Application",
            status_bar="[Arrows=Navigate, Enter=Select, Q=Quit]",
            term=term
        )
        self.selected = 0
        self.items = app_data
    
    def draw(self):
        super().draw()
        for i, item in enumerate(self.items[:self.content.height]):
            style = self.term.on_blue if i == self.selected else ''
            print(
                self.term.move(self.content.y + i, self.content.x) +
                style + item.ljust(self.content.width) + self.term.normal,
                end=''
            )
        print('', end='', flush=True)
    
    def handle_input(self, key):
        if key.name == 'KEY_UP' and self.selected > 0:
            self.selected -= 1
            self.redraw = True
        elif key.name == 'KEY_DOWN' and self.selected < len(self.items) - 1:
            self.selected += 1
            self.redraw = True
        elif key.name == 'KEY_ENTER':
            self.open_detail_window()
        elif key.upper() == 'Q':
            self.close()
    
    def open_detail_window(self):
        self.child = TextWindow(
            title=self.items[self.selected],
            text="Detail view here...",
            term=self.term
        )
```

### Conditional Redrawing

Only redraw when needed to improve performance:

```python
def handle_input(self, key):
    if key.name == 'KEY_UP':
        self.selected -= 1
        self.redraw = True  # Mark for redraw

# In event loop:
if key:
    window.handle_input(key)
    # ... lifecycle management ...
    if window_stack and window_stack[-1].redraw:
        window_stack[-1].draw()
```

### Dynamic Status Bar

```python
def draw(self):
    # Update status before drawing border
    if self.playing:
        self.status_bar = f"[Playing: {self.current_time}]"
    else:
        self.status_bar = "[Space=Play, Q=Quit]"
    
    super().draw()
    # ... draw content ...
```

### Tick for Updates

```python
def tick(self):
    if self.playing:
        current_time = self.get_playback_time()
        if current_time != self.last_time:
            self.last_time = current_time
            self.redraw = True
```

## API Reference

### Window

**Constructor:** `Window(title="", width=None, height=None, x=None, y=None, border=True, status_bar=None, term=None)`

**Methods:**
- `draw()`: Draw window (override, call super() first)
- `handle_input(key)`: Handle input (override)
- `handle_resize()`: Handle resize (override, call super() first)
- `tick()`: Periodic updates (override)
- `close()`: Close window

**Properties:**
- `content`: Content area (use for drawing)
- `position`: Window dimensions
- `term`: Terminal instance
- `closed`: Window closed flag
- `child`: Child window for modals
- `redraw`: Force redraw flag

### TextWindow

**Constructor:** `TextWindow(text, title="", term=None)`

Inherits all Window methods/properties. Text can be string, list, or tuple.

### Dimensions

**Constructor:** `Dimensions(x=None, y=None, width=None, height=None)`

Used internally for layout. Supports integers (pixels) or floats 0.0-1.0 (relative to container).

## Best Practices

1. **Always call `super().draw()` first** in custom draw methods
2. **Use `self.content` for drawing** (accounts for borders)
3. **Set `self.redraw = True`** when content changes
4. **Clear child references** when popping stack: `window_stack[-1].child = None`
5. **Handle SIGWINCH** for terminal resize support
6. **Use `term.inkey(timeout=0.1)`** to allow periodic updates
7. **Flush output** after drawing: `print('', end='', flush=True)`

## License

MIT License

## Contributing

Contributions welcome! Open an issue or submit a pull request at [github.com/p120ph37/term-windows](https://github.com/p120ph37/term-windows).
