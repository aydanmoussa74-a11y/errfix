"""Rich terminal rendering for problem summaries and suggested fixes."""

from __future__ import annotations

from typing import Callable, TypeVar

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

# color_system="auto" drops to plain text on dumb terminals / NO_COLOR.
console = Console(soft_wrap=True, highlight=False, color_system="auto")

T = TypeVar("T")


def render_solution(problem: str, fix: str) -> None:
    """Print two panels: [ERROR SUMMARY] then [PROPOSED FIX]."""
    summary = Text(problem or "Unable to summarize this error.", style="bold yellow")
    console.print(
        Panel(
            summary,
            title="[bold red][ERROR SUMMARY][/bold red]",
            title_align="left",
            border_style="red",
            padding=(1, 2),
        )
    )

    if not fix:
        fix_body: Text | Syntax = Text("No fix suggested.", style="dim")
    else:
        lexer = _detect_lexer(fix)
        theme = "monokai" if console.color_system else "ansi_light"
        fix_body = Syntax(
            fix,
            lexer,
            theme=theme,
            line_numbers=False,
            word_wrap=True,
            background_color="default",
        )

    console.print(
        Panel(
            fix_body,
            title="[bold green][PROPOSED FIX][/bold green]",
            title_align="left",
            border_style="green",
            padding=(1, 2),
            style="cyan",
        )
    )


def report_rc_permission_error() -> None:
    """Explain ~/.errfixrc is unreadable/unwritable without aborting."""
    console.print(
        Panel(
            Text(
                "Could not access ~/.errfixrc (permission denied).\n"
                "Falling back to the ERRFIX_API_KEY environment variable. "
                "Fix file permissions or export the key in your shell.",
                style="bold yellow",
            ),
            title="[bold red]CONFIG[/bold red]",
            title_align="left",
            border_style="red",
            padding=(1, 2),
        )
    )


def analyze_with_status(callback: Callable[[], T]) -> T:
    """Show a live spinner while an HTTP/API call runs."""
    with console.status(
        "[bold cyan]Analyzing stack trace...[/bold cyan]",
        spinner="dots",
    ):
        return callback()


def _detect_lexer(text: str) -> str:
    stripped = text.lstrip()
    shell_prefixes = (
        "$ ",
        "# ",
        "pip ",
        "pip3 ",
        "python ",
        "python3 ",
        "export ",
        "cd ",
        "npm ",
        "npx ",
        "cargo ",
        "go ",
        "curl ",
        "sudo ",
        "apt ",
        "brew ",
    )
    if stripped.startswith(shell_prefixes) or stripped.startswith(("git ", "make ")):
        return "bash"
    if any(token in text for token in ("def ", "class ", "import ", "return ", "    ")):
        return "python"
    if stripped.startswith(("function ", "const ", "let ", "var ", "export ")):
        return "javascript"
    return "text"
