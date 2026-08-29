"""Strip machine-specific paths from stack traces while keeping the signal."""

from __future__ import annotations

import re

# POSIX home directories: /home/alice/..., /Users/bob/...
_POSIX_HOME = re.compile(
    r"(?P<prefix>/(?:home|Users)/)(?P<user>[^/\\]+)(?P<rest>/[^\s:]*)",
    re.IGNORECASE,
)

# Windows user profiles: C:\Users\alice\... (also accepts forward slashes)
_WIN_HOME = re.compile(
    r"(?P<drive>[A-Za-z]:[\\/]Users[\\/])(?P<user>[^\\/]+)(?P<rest>[\\/][^\s:]*)",
    re.IGNORECASE,
)

# Other absolute roots that leak a local machine layout
_ABS_UNIX = re.compile(r"(^|[\s\"'])(/(?:var|tmp|opt|usr|root)/[^\s:]+)")
_FILE_URI = re.compile(r"file:///[^\s:]+", re.IGNORECASE)


def _posix_repl(match: re.Match[str]) -> str:
    rest = match.group("rest").lstrip("/")
    return f"./{rest}" if rest else "./"


def _win_repl(match: re.Match[str]) -> str:
    rest = match.group("rest").lstrip("\\/")
    rest = rest.replace("\\", "/")
    return f"./{rest}" if rest else "./"


def clean_stack_trace(raw_text: str) -> str:
    """Redact absolute local paths from a raw traceback.

    Preserves Traceback headers, line numbers, function names, and exception
    messages. Home-directory prefixes such as ``/home/username/``,
    ``/Users/username/``, and ``C:\\Users\\username\\`` are replaced with a
    generic relative indicator (``./...``).
    """
    if not raw_text:
        return ""

    cleaned = _POSIX_HOME.sub(_posix_repl, raw_text)
    cleaned = _WIN_HOME.sub(_win_repl, cleaned)
    cleaned = _FILE_URI.sub("./", cleaned)
    return cleaned.rstrip() + ("\n" if raw_text.endswith("\n") else "")
