"""P02-R10: the one guidance line for unaccepted LLM terms, in the text view only.

The line observes what the server reports and what Yörünge does not do. It must not depend on
``is_material``, must not appear when the terms are accepted, and must not carry a command, a URL,
an acceptance path or a claim about access or obligation.
"""

import copy
import json

from tests.contracts.test_context_discovery import WIRE
from yorunge.cli import TERMS_NOT_ACCEPTED_GUIDANCE, discovery_text_result
from yorunge.domain.discovery import ContextDiscovery


def view(*, accepted: bool, is_material: bool) -> ContextDiscovery:
    data = copy.deepcopy(WIRE)
    data["terms"] = {"accepted": accepted, "current_version": 2, "is_material": is_material}
    if accepted:
        data["reasons"] = [reason for reason in data["reasons"] if reason != "terms_not_accepted"]
    return ContextDiscovery.model_validate_json(json.dumps(data))


def test_unaccepted_terms_get_exactly_one_guidance_line_right_after_the_terms_state():
    lines = discovery_text_result(view(accepted=False, is_material=True)).splitlines()
    assert lines.count(TERMS_NOT_ACCEPTED_GUIDANCE) == 1
    state = next(index for index, line in enumerate(lines) if line.startswith("Sunucunun şart"))
    assert lines[state + 1] == TERMS_NOT_ACCEPTED_GUIDANCE


def test_is_material_does_not_change_the_text_for_unaccepted_terms():
    material = discovery_text_result(view(accepted=False, is_material=True))
    optional = discovery_text_result(view(accepted=False, is_material=False))
    assert material == optional


def test_accepted_terms_have_no_guidance_line_and_keep_their_state():
    text = discovery_text_result(view(accepted=True, is_material=False))
    assert TERMS_NOT_ACCEPTED_GUIDANCE not in text
    assert "şart durumu: kabul edilmiş" in text


def test_the_guidance_names_no_command_url_acceptance_path_or_obligation():
    text = TERMS_NOT_ACCEPTED_GUIDANCE.casefold()
    for forbidden in (
        "--yes",
        "terms accept",
        "http",
        "doc_path",
        "terms/",
        "gerekir",
        "zorunlu",
        "erişemez",
        "kabul ettik",
        "kabul edildi",
    ):
        assert forbidden not in text
    assert "yörünge şart kabul etmez" in text


def test_the_unaccepted_text_shows_no_host_or_url():
    text = discovery_text_result(view(accepted=False, is_material=True))
    assert "example.test" not in text
    assert "https://" not in text and "http://" not in text
