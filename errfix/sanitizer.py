import re

_PY_TRACE = "Traceback (most recent call last):"
_GO_PANIC = re.compile(r"(?m)^panic:")
_RUST_PANIC = re.compile(r"thread '.+' panicked")
_JS_FRAME = re.compile(r"(?m)^\s+at\s+")
_JS_ERROR = re.compile(
    r"(?m)^(?:[A-Za-z]*Error|UnhandledPromiseRejectionWarning)\s*:",
)


def clean_stack_trace(raw_text: str) -> str:
    if not raw_text or not raw_text.strip():
        return ""

    # Strip absolute POSIX & Windows paths, leaving relative filenames
    cleaned = re.sub(
        r'(?i)(?:"|file\s+|file://)?(?:[a-z]:\\|/)[^:\n\r]+[/\\]([^/\\]+\.[A-Za-z0-9]+)',
        r"\1",
        raw_text,
    )
    # Sanitize home directory shortcuts
    cleaned = re.sub(r"~[/\\][^\s:]+", "[HOME_DIR]", cleaned)

    extracted = _extract_trace_block(cleaned)
    return extracted.strip()


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
