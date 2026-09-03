# Contributing

Thanks for helping with errfix. Keep changes small, testable, and focused on the stdin → sanitize → explain → render pipeline.

## Local setup

```bash
git clone https://github.com/aydanmoussa74-a11y/errfix.git
cd errfix
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Optional runtime settings:

```bash
export ERRFIX_API_KEY="your_key_here"
export ERRFIX_API_URL="https://openrouter.ai/api/v1/chat/completions"
export ERRFIX_MODEL="meta-llama/llama-3-8b-instruct:free"
```

A key can also live in `~/.errfixrc` as `ERRFIX_API_KEY=...` (mode `600`). `errfix --reset-key` overwrites that file.

## Branch naming

Create a branch from `main`:

| Prefix | Use |
| --- | --- |
| `feat/` | user-visible behavior |
| `fix/` | bug fix |
| `docs/` | markdown / comments only |
| `chore/` | tooling, deps, repo hygiene |

Examples: `feat/rust-panic-extractor`, `fix/stdin-tty-hang`.

## Testing

The repository has regression tests for sanitization and defensive model-response parsing. Run the full suite before opening a PR:

```bash
pytest -q
python -m compileall -q errfix
errfix --help
```

For a local CLI smoke test:

```bash
printf '%s\n' 'Traceback (most recent call last):' '  File "/tmp/app.py", line 1, in <module>' 'NameError: name "x" is not defined' | errfix
```

Also confirm:

- `errfix` with no args on a TTY prints the usage panel and returns immediately.
- A Node `TypeError` / Go `panic:` / Rust `panicked` blob is extracted instead of dropped.
- A fenced JSON model reply still parses after the fence stripper.

Do not commit `~/.errfixrc`, `.env`, or API keys.

## Pull requests

1. One concern per PR.
2. Title uses a conventional prefix (`feat:`, `fix:`, `docs:`).
3. Describe the user-visible change and how you verified it.
4. Do not retarget secrets, expand the LLM prompt into multi-paragraph essays, or log raw unsanitized traces.
5. Wait for review before merging to `main`.
