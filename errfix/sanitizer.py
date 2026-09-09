"""Privacy-focused stack trace sanitization and extraction."""

from __future__ import annotations

import re

_PY_TRACE = "Traceback (most recent call last):"
_GO_PANIC = re.compile(r"(?m)^panic:")
_RUST_PANIC = re.compile(r"thread '.+' panicked")
_JS_FRAME = re.compile(r"(?m)^\s+at\s+")
_JS_ERROR = re.compile(
    r"(?m)^(?:[A-Za-z][A-Za-z0-9]*(?:Error|Exception)|UnhandledPromiseRejectionWarning)\s*:",
)

# Match common absolute paths while preserving the final filename. This is
# intentionally conservative: URLs, hostnames, and ordinary error messages
# should not be rewritten merely because they contain a slash.
_ABS_PATH = re.compile(
    r'(?P<prefix>(?:"|file\s+|file://)?)(?P<path>(?:[A-Za-z]:[\\/]|/)(?:[^:\n\r"\s]+[\\/])+)(?P<name>[^/\\\n\r"\s]+\.[A-Za-z0-9]+)',
    re.IGNORECASE,
)
_HOME_PATH = re.compile(r"~(?:[/\\][^\s:'\"]*)?")


def clean_stack_trace(raw_text: str) -> str:
    """Redact local paths and retain the useful portion of a stack trace."""
    if not raw_text or not raw_text.strip():
        return ""

    cleaned = _ABS_PATH.sub(
        lambda match: f'{match.group("prefix")}{match.group("name")}',
        raw_text,
    )
    cleaned = _HOME_PATH.sub("[HOME_DIR]", cleaned)

    extracted = _extract_trace_block(cleaned)
    return extracted.strip()


def _line_start_with_optional_frame(text: str, offset: int) -> int:
    """Return the current line start, including an adjacent source line."""
    line_start = text.rfind("\n", 0, offset) + 1
    previous_end = line_start - 1
    previous_start = text.rfind("\n", 0, previous_end) + 1
    previous_line = text[previous_start:previous_end].lstrip()
    if previous_line.startswith("File ") or previous_line.startswith("at "):
        return previous_start
    return line_start


def _extract_trace_block(text: str) -> str:
    starts = []

    py_at = text.find(_PY_TRACE)
    if py_at != -1:
        starts.append(py_at)

    go_match = _GO_PANIC.search(text)
    if go_match:
        starts.append(go_match.start())

    rust_match = _RUST_PANIC.search(text)
    if rust_match:
        starts.append(rust_match.start())

    js_err = _JS_ERROR.search(text)
    js_frame = _JS_FRAME.search(text)
    if js_err:
        # Preserve an immediately preceding source/frame line when a short
        # trace has no language header, including redacted local paths.
        starts.append(_line_start_with_optional_frame(text, js_err.start()))
    elif js_frame:
        starts.append(js_frame.start())
    elif "TypeError:" in text:
        type_error_at = text.find("TypeError:")
        starts.append(_line_start_with_optional_frame(text, type_error_at))

    if starts:
        return text[min(starts) :]

    lines = text.splitlines()
    return "\n".join(lines[-30:])
