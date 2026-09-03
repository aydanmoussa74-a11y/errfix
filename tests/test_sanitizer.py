from errfix.sanitizer import clean_stack_trace


def test_empty_input_is_empty():
    assert clean_stack_trace("   ") == ""


def test_python_trace_keeps_traceback_and_redacts_unix_path():
    trace = '''noise\nTraceback (most recent call last):\n  File "/home/zayd/project/app.py", line 8, in <module>\n    run()\nNameError: name "run" is not defined'''
    cleaned = clean_stack_trace(trace)
    assert cleaned.startswith("Traceback (most recent call last):")
    assert "/home/zayd" not in cleaned
    assert "app.py" in cleaned


def test_windows_path_is_reduced_to_filename():
    trace = r'''Traceback (most recent call last):\n  File "C:\Users\Zayd\project\app.py", line 3, in <module>\nValueError: bad value'''
    cleaned = clean_stack_trace(trace)
    assert "C:\\Users\\Zayd" not in cleaned
    assert "app.py" in cleaned


def test_home_shortcut_is_redacted():
    cleaned = clean_stack_trace("File ~/private/project/app.py:12\nValueError: bad")
    assert "~/private" not in cleaned
    assert "[HOME_DIR]" in cleaned


def test_unknown_trace_keeps_only_last_thirty_lines():
    raw = "\n".join(f"line {i}" for i in range(40))
    cleaned = clean_stack_trace(raw)
    assert "line 9" not in cleaned
    assert "line 10" in cleaned
    assert "line 39" in cleaned
