import os

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

# Initialize recording console
console = Console(record=True, width=72)

problem_text = (
    "IndexError: list index out of range at line 14\n"
    "You attempted to access index 3 on an empty list `items`."
)
fix_code = "# Add validation check before indexing:\nif items:\n    val = items[0]"

summary_panel = Panel(
    problem_text,
    title="[bold red]💥 ERROR SUMMARY[/bold red]",
    border_style="red",
    expand=False,
)

syntax = Syntax(fix_code, "python", theme="monokai", line_numbers=False)
fix_panel = Panel(
    syntax,
    title="[bold green]✅ PROPOSED FIX[/bold green]",
    border_style="green",
    expand=False,
)

console.print(summary_panel)
console.print(fix_panel)

# Ensure assets directory exists and save SVG
os.makedirs("assets", exist_ok=True)
console.save_svg("assets/demo.svg", title="errfix Terminal Demo", clear=False)
print("Successfully generated assets/demo.svg")
