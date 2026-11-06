"""Every place that tells the plan families apart is listed, with the slice that must handle it.

A continuation (plan version 3) is not a subclass of the v2 types, so code that says "is it v2,
otherwise v1" or "is it v2, otherwise a continuation does not exist" silently misreads or ignores
it. The list in ``tests/fixtures/version-dispatch-sites.json`` is derived from the source by the
rules below. A new site fails this test until it is assigned; a site a slice has handled is
changed to ``done`` in the same commit that handles it.
"""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "src" / "yorunge"
LIST = json.loads((ROOT / "tests" / "fixtures" / "version-dispatch-sites.json").read_text())

FAMILY_TYPES = (
    "DatasetUploadPlan|DatasetUploadApproval|TransferRecord|TransferControl|TransferVerification"
    "|StageReceipt|DatasetUploadPlanV2|DatasetUploadApprovalV2|TransferRecordV2|TransferControlV2"
    "|TransferVerificationV2|CreateReceiptV2|DatasetContinuationPlanV3|DatasetUploadApprovalV3"
    "|TransferRecordV3|TransferControlV3|TransferVerificationV3"
)
PATTERNS = (
    re.compile(rf"isinstance\((?:[^()]|\([^()]*\))*?\b(?:{FAMILY_TYPES})\b", re.S),
    re.compile(rf"type\([^)]*\)\s+is(?:\s+not)?\s+(?:{FAMILY_TYPES})\b"),
    re.compile(
        r"\b(?:record|proof|plan|control|approval|view\.\w+|current|old|value|updated)"
        r"\.schema_version\s*(?:==|!=|in\b|<|>)"
    ),
)
# The modules that define the families; their own rules are not dispatch between families.
DEFINING_MODULES = {
    "dataset_transfer.py",
    "dataset_transfer_v2.py",
    "dataset_transfer_v3.py",
    "dataset_upload.py",
    "dataset_upload_v2.py",
    "dataset_continuation.py",
    "create_receipt.py",
}


def found_sites():
    sites = []
    for path in sorted(SOURCE.rglob("*.py")):
        if path.name in DEFINING_MODULES:
            continue
        text = path.read_text()
        lines = text.splitlines()
        numbers = {
            text.count("\n", 0, match.start()) + 1
            for pattern in PATTERNS
            for match in pattern.finditer(text)
        }
        counter = Counter()
        for number in sorted(numbers):
            first = lines[number - 1].strip()
            relative = str(path.relative_to(ROOT))
            sites.append((relative, first, counter[relative, first]))
            counter[relative, first] += 1
    return sites


def listed_sites():
    return [(site["file"], site["text"], site["occurrence"]) for site in LIST["sites"]]


def test_the_list_equals_the_code_site_for_site():
    found, listed = found_sites(), listed_sites()
    assert sorted(found) == sorted(listed), (
        "a version-dispatch site changed: assign it in tests/fixtures/version-dispatch-sites.json "
        f"\nnew in code: {sorted(set(found) - set(listed))}"
        f"\nlisted but gone or reworded: {sorted(set(listed) - set(found))}"
    )


def test_every_site_has_a_known_owner_and_says_why():
    owners = set(LIST["owners"])
    for site in LIST["sites"]:
        assert site["owner"] in owners, site
        assert site["note"].strip(), site
    assert len(listed_sites()) == len(set(listed_sites()))


def test_only_the_slices_still_to_come_own_open_sites():
    # P02-3g has handled its own; v1-only and v2-only are deliberate, permanent families.
    open_owners = {site["owner"] for site in LIST["sites"]} - {"done", "v1-only", "v2-only"}
    assert open_owners <= {"P02-3u", "P02-3v", "P02-3r", "P02-3h", "P02-3i"}
    assert "P02-3g" not in open_owners


def test_the_dispatch_helpers_of_the_versions_module_name_every_family():
    # A cheap guard on the done sites: the helpers that decide by family mention all three.
    text = (SOURCE / "domain" / "upload_versions.py").read_text()
    for name in ("DatasetContinuationPlanV3", "DatasetUploadApprovalV3", "TransferVerificationV3"):
        assert name in text


@pytest.mark.parametrize("owner", ["P02-3u", "P02-3v", "P02-3r", "P02-3h"])
def test_each_open_owner_names_a_card_that_exists(owner):
    cards = list((ROOT / "docs" / "roadmap" / "tasks").glob(f"{owner.lower()}-*.md"))
    assert len(cards) == 1, owner
