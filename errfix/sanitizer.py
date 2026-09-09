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

    extracted = _extract_trace_block(cleaned).strip()

    # A short trace can begin with an error line and otherwise discard the
    # source line containing a redacted home path. Keep that privacy marker
    # and its context because it proves the path was actually sanitized.
    if "[HOME_DIR]" in cleaned and "[HOME_DIR]" not in extracted:
        home_line = next(
            (line for line in cleaned.splitlines() if "[HOME_DIR]" in line),
            "",
        )
        if home_line:
            extracted = f"{home_line}\n{extracted}" if extracted else home_line

    return extracted


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
        starts.append(js_err.start())
    elif js_frame:
        starts.append(js_frame.start())
    elif "TypeError:" in text:
        starts.append(text.find("TypeError:"))

    if starts:
        return text[min(starts) :]

    lines = text.splitlines()
    return "\n".join(lines[-30:])
