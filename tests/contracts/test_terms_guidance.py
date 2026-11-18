"""P02-R10: the one guidance line for unaccepted LLM terms, in the text view only.

The line observes what the server reports and what Yörünge does not do. It must not depend on
``is_material``, must not appear when the terms are accepted, and must not carry a command, a URL,
an acceptance path or a claim about access or obligation. The whole text is pinned for both states,
so that a change to any other line shows up here too.
"""

import copy
import json

import pytest

from tests.contracts.test_context_discovery import WIRE
from yorunge.cli import TERMS_NOT_ACCEPTED_GUIDANCE, discovery_text_result
from yorunge.domain.discovery import ContextDiscovery

HEAD = ["Hizmet: evren-llm", "Profil: work"]
SCOPE = "Profilin hesap/proje tercihinin LLM hizmet kapsamı bilinmiyor."
UNVERIFIED = "Kimlik doğrulaması: doğrulanmadı. Uzak hesap/proje kimliği sunulmuyor."
NO_EXECUTION = "Bu gözlem yürütme izni vermez; uzak atomik snapshot değildir."


def view(*, accepted: bool, is_material: bool) -> ContextDiscovery:
    data = copy.deepcopy(WIRE)
    data["terms"] = {"accepted": accepted, "current_version": 2, "is_material": is_material}
    if accepted:
        data["reasons"] = [reason for reason in data["reasons"] if reason != "terms_not_accepted"]
    return ContextDiscovery.model_validate_json(json.dumps(data))


def test_unaccepted_terms_text_is_pinned_line_by_line():
    assert discovery_text_result(view(accepted=False, is_material=True)) == "\n".join(
        [
            *HEAD,
            "Sunucunun şart durumu: kabul edilmemiş (sürüm 2)",
            TERMS_NOT_ACCEPTED_GUIDANCE,
            UNVERIFIED,
            NO_EXECUTION,
            SCOPE,
        ]
    )


def test_accepted_terms_text_is_pinned_line_by_line_and_has_no_guidance():
    assert discovery_text_result(view(accepted=True, is_material=False)) == "\n".join(
        [
            *HEAD,
            "Sunucunun şart durumu: kabul edilmiş (sürüm 2)",
            UNVERIFIED,
            NO_EXECUTION,
            SCOPE,
        ]
    )


def test_is_material_does_not_change_the_text_for_unaccepted_terms():
    material = discovery_text_result(view(accepted=False, is_material=True))
    optional = discovery_text_result(view(accepted=False, is_material=False))
    assert material == optional


@pytest.mark.parametrize("accepted", [True, False])
def test_the_verification_and_execution_lines_are_kept_in_both_states(accepted):
    text = discovery_text_result(view(accepted=accepted, is_material=True))
    assert UNVERIFIED in text.splitlines()
    assert NO_EXECUTION in text.splitlines()


def test_the_guidance_names_no_command_url_acceptance_path_or_obligation():
    text = TERMS_NOT_ACCEPTED_GUIDANCE.casefold()
    for forbidden in (
        "--yes",
        "terms accept",
        "http",
        "doc_path",
        "terms/",
        "gerekir",
        "gerekli",
        "gerekiyor",
        "lazım",
        "mecbur",
        "zorunlu",
        "erişemez",
        "kabul edin",
        "kabul ettik",
        "kabul edildi",
        "onaylayın",
        "kendi hesabınız",
    ):
        assert forbidden not in text
    assert "yörünge şartları sizin adınıza kabul etmez." in text


def test_the_unaccepted_text_shows_no_host_or_url():
    text = discovery_text_result(view(accepted=False, is_material=True))
    assert "example.test" not in text
    assert "https://" not in text and "http://" not in text
