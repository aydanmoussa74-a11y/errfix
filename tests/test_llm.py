import pytest

from errfix.llm import _parse_json_content


def test_parse_json_object():
    assert _parse_json_content('{"problem":"bad input","fix":"validate it"}') == {
        "problem": "bad input",
        "fix": "validate it",
    }


def test_parse_fenced_json():
    assert _parse_json_content('```json\n{"problem":"bad input","fix":"validate it"}\n```')["problem"] == "bad input"


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"problem":"","fix":"validate it"}',
        '{"problem":"bad input","fix":""}',
        '{"problem":"bad input"}',
        '[]',
    ],
)
def test_reject_invalid_model_output(content):
    with pytest.raises((ValueError, TypeError)):
        _parse_json_content(content)
