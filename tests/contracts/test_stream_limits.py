"""The framing allowance is explicit; endpoint JSON budgets remain unchanged."""

import pytest

from yorunge.application.response_json import parse_json
from yorunge.domain.errors import YorungeError
from yorunge.domain.wire_limits import FRAME_LIMIT, JSON_LIMIT


def test_framing_byte_allowance_does_not_change_default_json_limit():
    content = b'"' + b"a" * (FRAME_LIMIT - 2) + b'"'
    with pytest.raises(YorungeError) as caught:
        parse_json(content)
    assert caught.value.code == "invalid_response"
    assert len(parse_json(content, max_bytes=FRAME_LIMIT)) == FRAME_LIMIT - 2
    excess = content[:-1] + b'a"'
    with pytest.raises(YorungeError) as caught:
        parse_json(excess, max_bytes=FRAME_LIMIT)
    assert caught.value.code == "invalid_response"


@pytest.mark.parametrize("limit", [False, 1.0, 0, -1, FRAME_LIMIT + 1, 10**1000])
def test_frame_override_cannot_disable_or_expand_the_wire_budget(limit):
    with pytest.raises(YorungeError) as caught:
        parse_json(b"0", max_bytes=limit)
    assert caught.value.code == "invalid_response"
    assert caught.value.__context__ is None


def test_structural_budgets_are_not_relaxed_by_the_byte_allowance():
    deep = b"[" * 33 + b"0" + b"]" * 33
    with pytest.raises(YorungeError) as caught:
        parse_json(deep, max_bytes=FRAME_LIMIT)
    assert caught.value.code == "invalid_response"
    assert JSON_LIMIT + 1024 == FRAME_LIMIT
