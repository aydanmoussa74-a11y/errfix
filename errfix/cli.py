"""Command-line entry point for errfix."""

from __future__ import annotations

import sys

import click

from errfix import __version__
from errfix.display import render_solution
from errfix.llm import explain_error
from errfix.sanitizer import clean_stack_trace


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


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="errfix")
@click.argument("trace", nargs=-1)
def main(trace: tuple[str, ...]) -> None:
    """Transform a verbose stack trace into a two-line problem + fix.

    Pipe a process:  python script.py 2>&1 | errfix
    Or pass text:    errfix 'Traceback (most recent call last): ...'
    """
    raw_text = _read_input(trace)
    if not raw_text.strip():
        click.echo(
            "errfix: no stack trace received. Pipe output or pass text as arguments.\n"
            "Example: python script.py 2>&1 | errfix",
            err=True,
        )
        raise SystemExit(1)

    cleaned = clean_stack_trace(raw_text)
    result = explain_error(cleaned)
    render_solution(result.get("problem", ""), result.get("fix", ""))


if __name__ == "__main__":
    main()
