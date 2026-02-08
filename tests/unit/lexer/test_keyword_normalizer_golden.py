from pathlib import Path

import pytest

from psh.lexer import tokenize


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "keyword_normalizer"

GOLDEN_CASES = {
    "for_in_glob": 'for file in *.txt; do echo "$file"; done',
    "case_nested": "case $opt in\n  start|stop) echo hi;;\n  *) echo default;;\n esac",
    "heredoc_keywords": "cat <<EOF\nif should not change\nfi\nEOF",
}


def _tokens_to_lines(tokens):
    lines = []
    for token in tokens:
        value = token.value
        if value is None:
            value = ""
        value = value.replace("\n", "\\n")
        lines.append(f"{token.type.name}:{value}:{token.is_keyword}")
    return lines


@pytest.mark.parametrize("case_name,source", GOLDEN_CASES.items())
def test_keyword_normalizer_golden(case_name, source):
    tokens = tokenize(source)
    actual = _tokens_to_lines(tokens)

    golden_path = FIXTURE_DIR / f"{case_name}.txt"
    expected = [line.rstrip("\n") for line in golden_path.read_text().splitlines()]

    assert actual == expected, f"Keyword normalizer output changed for {case_name}"
