"""Tiny ANSI colour helpers. Colour only when writing to a terminal; NO_COLOR disables it, FORCE_COLOR forces it."""
import os, sys

def _on(stream) -> bool:
    """Whether to emit colour for `stream`: off if NO_COLOR, on if FORCE_COLOR, else only for a terminal."""
    if os.environ.get("NO_COLOR"): return False
    return bool(os.environ.get("FORCE_COLOR")) or stream.isatty()

def _paint(code: str, text: str, stream=None) -> str:
    """Wrap `text` in the ANSI colour `code` if colour is on for `stream` (default stdout)."""
    return f"\033[{code}m{text}\033[0m" if _on(stream or sys.stdout) else text

def red(t, stream=None):
    """Bold red text."""
    return _paint("31;1", t, stream)

def green(t, stream=None):
    """Green text."""
    return _paint("32", t, stream)

def yellow(t, stream=None):
    """Yellow text."""
    return _paint("33", t, stream)

def cyan(t, stream=None):
    """Cyan text."""
    return _paint("36", t, stream)

def dim(t, stream=None):
    """Dimmed text."""
    return _paint("2", t, stream)

def bold(t, stream=None):
    """Bold text."""
    return _paint("1", t, stream)

def die(msg: str):
    """Print an error in red to stderr and exit non-zero."""
    print(red(msg, sys.stderr), file=sys.stderr)
    raise SystemExit(1)

def pretty_tracebacks():
    """Coloured tracebacks (Python 3.12 has none built in) when stderr is a terminal."""
    if _on(sys.stderr):
        try:
            from rich.traceback import install
            install(show_locals=False, width=120)
        except ImportError: pass
