# Engineering

errfix is a zero-config CLI that turns a raw stderr stream into a two-panel
terminal answer: a short problem summary and a proposed fix.

## Pipeline

```
stderr / argv  →  sanitizer  →  llm client  →  rich display
     IPC            privacy       JSON pair        panels
```

1. `errfix.cli` collects input, resolves `ERRFIX_API_KEY`, and drives the run.
2. `errfix.sanitizer.clean_stack_trace` redacts machine paths and extracts the
   useful trace block.
3. `errfix.llm.explain_error` posts the cleaned trace to an OpenAI-compatible
   chat-completions endpoint and returns `{problem, fix}`.
4. `errfix.display` renders two Rich panels and a status spinner during the
   HTTP wait.

## Stdin IPC

The intended invocation is a pipe:

```bash
python app.py 2>&1 | errfix
```

`cli._read_input` treats a non-TTY stdin as the source of truth and only falls
back to positional arguments when the pipe is empty.

If both stdin is an interactive TTY **and** no positional trace was passed,
the process must **not** call `sys.stdin.read()`. That call would block until
the user typed EOF. Instead the CLI prints a Rich usage panel
(`python app.py 2>&1 | errfix` and language-equivalent pipes) and exits.

API-key prompts use `getpass`, which reads `/dev/tty`, so a piped traceback on
stdin is never consumed by the secret prompt.

## Privacy sanitization

`clean_stack_trace` runs before any bytes leave the machine:

| Rule | Pattern intent | Replacement |
| --- | --- | --- |
| Absolute POSIX / Windows file paths | `/home/.../app.py`, `C:\Users\...\lib.ts` | basename only (`app.py`) |
| `file://` URLs and `File "..."` prefixes | editor / runtime wrappers | basename |
| Home shortcuts | `~/Projects/app` | `[HOME_DIR]` |

After redaction the extractor looks for language-specific headers, taking the
earliest match:

- Python: `Traceback (most recent call last):`
- Node.js / JS: `TypeError:` / `*Error:` plus `    at ` frames
- Go: `panic:`
- Rust: `thread '...' panicked`

If none of those markers appear, the last 30 lines of the (already redacted)
stream are kept so unknown runtimes are not dropped.

## LLM prompt constraints

`explain_error` sends a system prompt that requires **raw JSON only**, with
exactly two keys:

- `problem` — one or two sentences on the root cause
- `fix` — the code change or terminal command

The HTTP body uses the OpenAI-compatible chat-completions shape so the same
client can target OpenRouter, Groq, or OpenAI via `ERRFIX_API_URL` and
`ERRFIX_MODEL`. `response_format: {type: json_object}` is requested when the
host supports it.

Models still wrap JSON in Markdown fences. Before `json.loads`, content is
passed through:

```python
re.sub(r'^```json\s*|\s*```$', '', content.strip(), flags=re.MULTILINE)
```

Network, HTTP, and parse failures return a structured `{problem, fix}` pair
instead of raising out of the CLI.

## Visual terminal rendering

`display.console` is a Rich `Console` with `color_system="auto"`. Unsupported
terminals and `NO_COLOR` degrade to plain text.

- Status: `console.status("[bold cyan]Analyzing stack trace...[/bold cyan]", spinner="dots")` wraps the HTTP call.
- `[ERROR SUMMARY]` — red border, bold yellow body.
- `[PROPOSED FIX]` — green border, cyan body, `Syntax` highlighting (Python,
  bash, JS, or plain text).
- Permission errors on `~/.errfixrc` use a dedicated CONFIG panel and the
  process continues with `ERRFIX_API_KEY`.
