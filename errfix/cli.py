"""Command-line entry point for errfix."""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

import click

from errfix import __version__
from errfix.display import analyze_with_status, render_solution, report_rc_permission_error
from errfix.llm import explain_error
from errfix.sanitizer import clean_stack_trace

CONFIG_PATH = Path.home() / ".errfixrc"


def _read_input(trace: tuple[str, ...]) -> str:
    """Prefer piped stdin; otherwise join positional arguments."""
    piped = not sys.stdin.isatty()
    if piped:
        stdin_text = sys.stdin.read()
        if stdin_text.strip():
            return stdin_text
    if trace:
        return " ".join(trace)
    return ""


def _read_saved_key() -> str:
    try:
        if not CONFIG_PATH.is_file():
            return ""
        text = CONFIG_PATH.read_text(encoding="utf-8")
    except PermissionError:
        report_rc_permission_error()
        return ""
    except OSError:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" in line:
            name, _, value = line.partition("=")
            if name.strip() in {"ERRFIX_API_KEY", "API_KEY"}:
                return value.strip().strip("'\"")
        else:
            return line
    return text.strip()


def _save_key(key: str) -> bool:
    try:
        CONFIG_PATH.write_text(f"ERRFIX_API_KEY={key}\n", encoding="utf-8")
        try:
            os.chmod(CONFIG_PATH, 0o600)
        except PermissionError:
            report_rc_permission_error()
        except OSError:
            pass
        return True
    except PermissionError:
        report_rc_permission_error()
        return False


def _prompt_key(message: str) -> str:
    """Prompt on the real TTY so piped stack traces are not consumed."""
    try:
        return getpass.getpass(f"{message} ").strip()
    except (EOFError, OSError, KeyboardInterrupt):
        click.echo(
            "\nerrfix: no TTY available to enter ERRFIX_API_KEY. "
            "Export ERRFIX_API_KEY or write it to ~/.errfixrc.",
            err=True,
        )
        raise SystemExit(1)


def resolve_api_key(reset_key: bool) -> str:
    """Env var → ~/.errfixrc → interactive prompt. Always export into the process env."""
    env_key = (os.getenv("ERRFIX_API_KEY") or "").strip()

    if reset_key:
        key = _prompt_key("Enter new ERRFIX_API_KEY to save to ~/.errfixrc:")
        if not key:
            click.echo("errfix: empty key, nothing saved.", err=True)
            raise SystemExit(1)
        if _save_key(key):
            click.echo(f"Saved API key to {CONFIG_PATH}", err=True)
        os.environ["ERRFIX_API_KEY"] = key
        return key

    if env_key:
        return env_key

    saved = _read_saved_key()
    if saved:
        os.environ["ERRFIX_API_KEY"] = saved
        return saved

    # rc unreadable: fall back to env (already empty) then prompt, but never crash
    key = _prompt_key("ERRFIX_API_KEY not found. Enter key to save to ~/.errfixrc:")
    if not key:
        click.echo("errfix: empty key, aborting.", err=True)
        raise SystemExit(1)
    _save_key(key)
    os.environ["ERRFIX_API_KEY"] = key
    return key


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="errfix")
@click.option(
    "--reset-key",
    is_flag=True,
    help="Overwrite the API key stored in ~/.errfixrc.",
)
@click.argument("trace", nargs=-1)
def main(reset_key: bool, trace: tuple[str, ...]) -> None:
    """Transform a verbose stack trace into a two-line problem + fix.

    Pipe a process:  python script.py 2>&1 | errfix
    Or pass text:    errfix 'Traceback (most recent call last): ...'
    """
    resolve_api_key(reset_key)

    raw_text = _read_input(trace)
    if not raw_text.strip():
        if reset_key:
            return
        click.echo(
            "errfix: no stack trace received. Pipe output or pass text as arguments.\n"
            "Example: python script.py 2>&1 | errfix",
            err=True,
        )
        raise SystemExit(1)

    cleaned = clean_stack_trace(raw_text)
    result = analyze_with_status(lambda: explain_error(cleaned))
    render_solution(result.get("problem", ""), result.get("fix", ""))


if __name__ == "__main__":
    main()
