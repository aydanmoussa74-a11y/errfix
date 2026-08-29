import re


def clean_stack_trace(raw_text: str) -> str:
    if not raw_text or not raw_text.strip():
        return ""

    # Strip absolute POSIX & Windows paths, leaving relative filenames
    cleaned = re.sub(
        r'(?i)(?:"|file\s+)?(?:[a-z]:\\|/)[^:\n\r]+[/\\]([^/\\]+\.py)',
        r"\1",
        raw_text,
    )
    # Sanitize home directory shortcuts
    cleaned = re.sub(r"~[/\\][^\s:]+", "[HOME_DIR]", cleaned)

    # Extract Traceback block if extra output exists
    if "Traceback (most recent call last):" in cleaned:
        cleaned = cleaned[cleaned.find("Traceback (most recent call last):") :]

    return cleaned.strip()
