# Engineering

errfix is a CLI that turns a raw stderr stream into a two-panel terminal answer: a short problem summary and a proposed fix.

## Pipeline

```
stderr / argv  →  sanitizer  →  llm client  →  rich display
     IPC            privacy       JSON pair        panels
```

1. `errfix.cli` collects input, resolves `ERRFIX_API_KEY`, and drives the run.
2. `errfix.sanitizer.clean_stack_trace` redacts local paths and extracts the useful trace block.
3. `errfix.llm.explain_error` posts the cleaned trace to an OpenAI-compatible chat-completions endpoint and returns `{problem, fix}`.
4. `errfix.display` renders two Rich panels and a status spinner during the HTTP wait.

## Stdin IPC

The intended invocation is a pipe:

```bash
python app.py 2>&1 | errfix
```

`cli._read_input` treats a non-TTY stdin as the source of truth and only falls back to positional arguments when the pipe is empty.

If both stdin is an interactive TTY **and** no positional trace was passed, the process must **not** call `sys.stdin.read()`. That call would block until the user typed EOF. Instead the CLI prints a Rich usage panel and exits.

API-key prompts use `getpass`, so a piped traceback on stdin is never consumed by the secret prompt.

## Privacy sanitization

`clean_stack_trace` runs before the trace is sent to the model:

| Rule | Pattern intent | Replacement |
| --- | --- | --- |
| Absolute POSIX / Windows file paths | `/home/.../app.py`, `C:\Users\...\lib.ts` | basename only (`app.py`) |
| `file://` URLs and `File "..."` prefixes | editor / runtime wrappers | basename |
| Home shortcuts | `~/Projects/app` | `[HOME_DIR]` |

The path sanitizer is deliberately conservative and focuses on file-like paths, preserving ordinary URLs and error text. After redaction the extractor looks for language-specific headers, taking the earliest match:

- Python: `Traceback (most recent call last):`
- Node.js / JS: `TypeError:` / `*Error:` plus `    at ` frames
- Go: `panic:`
- Rust: `thread '...' panicked`

If none of those markers appear, the last 30 lines of the already-redacted stream are kept so unknown runtimes are not dropped.

## LLM client

`explain_error` sends a system prompt requesting a JSON object containing `problem` and `fix`. The HTTP body uses the OpenAI-compatible chat-completions shape so the client can target OpenRouter, Groq, OpenAI, or another compatible endpoint via `ERRFIX_API_URL` and `ERRFIX_MODEL`.

The response parser accepts raw JSON and fenced JSON, then validates that both rendered fields are non-empty strings. Malformed JSON, missing fields, HTTP failures, and unexpected response shapes are converted into a safe structured error result instead of escaping through the CLI.

The request timeout is 10 seconds. The client does not log the API key or the raw unsanitized trace.

## Visual terminal rendering

`display.console` is a Rich `Console` with `color_system="auto"`. Unsupported terminals and `NO_COLOR` degrade to plain text.

- Status: `console.status("[bold cyan]Analyzing stack trace...[/bold cyan]", spinner="dots")` wraps the HTTP call.
- `[ERROR SUMMARY]` — red border, bold yellow body.
- `[PROPOSED FIX]` — green border, cyan body, `Syntax` highlighting (Python, bash, JS, or plain text).
- Permission errors on `~/.errfixrc` use a dedicated CONFIG panel and the process continues with the environment key when available.

## Testing

The repository contains regression tests for path sanitization, trace extraction, unknown-trace truncation, and defensive model-response parsing. CI compiles the package and runs the test suite across supported modern Python versions.
