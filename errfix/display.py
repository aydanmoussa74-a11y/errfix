"""Rich terminal rendering for problem summaries and suggested fixes."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

_console = Console()


def render_solution(problem: str, fix: str) -> None:
    """Print a two-panel view: the problem in bold red/yellow, the fix in green."""
    problem_text = Text()
    problem_text.append("PROBLEM\n", style="bold red")
    problem_text.append(problem or "Unable to summarize this error.", style="bold yellow")

    _console.print(
        Panel(
            problem_text,
            border_style="red",
            title="errfix",
            title_align="left",
        )
    )

    code_like = _looks_like_code(fix)
    if code_like:
        body = Syntax(
            fix,
            "python",
            theme="monokai",
            line_numbers=False,
            word_wrap=True,
        )
    else:
        body = Markdown(f"```python\n{fix}\n```") if fix else Text("No fix suggested.", style="dim")

    _console.print(
        Panel(
            body,
            border_style="green",
            title="[bold green]FIX[/bold green]",
            title_align="left",
        )
    )


def _looks_like_code(text: str) -> bool:
    if not text:
        return False
    markers = ("def ", "class ", "import ", "return ", "=", "    ", "\t")
    return any(token in text for token in markers)
