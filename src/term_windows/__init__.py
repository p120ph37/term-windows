"""
Terminal Windows Library

A lightweight library for creating terminal-based windowed UIs using the Blessed library.
Provides window management, layout constraints, and a window-stack mechanism for modal dialogs.
"""

from .term_windows import (
    Dimensions,
    ConstrainedDimensions,
    OffsetDimensions,
    Window,
    TextWindow,
)

__all__ = [
    'Dimensions',
    'ConstrainedDimensions',
    'OffsetDimensions',
    'Window',
    'TextWindow',
]

__version__ = '0.1.0'

