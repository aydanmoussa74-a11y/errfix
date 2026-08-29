# -errfix

![status](https://img.shields.io/badge/status-alpha-yellow)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

Transform verbose, ugly terminal stack traces into instant 2-line solutions.

`-errfix` is a zero-config CLI that reads a traceback from a pipe or argument,
redacts local machine paths, and prints a short problem summary plus a suggested fix.

## Installation

```bash
git clone https://github.com/aydanmoussa74-a11y/-errfix.git
cd -errfix
pip install -e .
```

## Usage

Pipe a failing script:

```bash
python script.py 2>&1 | errfix
```

Pass a captured traceback as arguments:

```bash
errfix 'Traceback (most recent call last): ...'
```

Optional inference settings (otherwise a local heuristic is used):

```bash
export ERRFIX_API_KEY=sk-...
export ERRFIX_API_URL=https://api.openai.com/v1/chat/completions
export ERRFIX_MODEL=gpt-4o-mini
```

## How it works

1. `sanitizer` strips `/home/username/`, `/Users/username/`, and `C:\Users\username\` paths.
2. `llm` asks an inference endpoint for a `{problem, fix}` pair.
3. `display` renders the problem in red/yellow and the fix as a green code block.
