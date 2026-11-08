"""What round one found nobody pinning in the installation_v4 reader of research_evidence."""

import pytest

from tests.contracts.test_installation_evidence_v4 import ADDED, CHECKS, receipt

pytestmark = pytest.mark.usefixtures("evidence_publication_context")


@pytest.mark.parametrize("name", ADDED)
@pytest.mark.parametrize("bad", ["weird", "Passed", "", True, None, 5])
def test_gap_status_vocabulary_is_enforced_even_in_an_honest_failing_record(name, bad):
    value = receipt()
    value["results"][1][name] = bad
    value["passed"] = False  # the record admits its failure: only the status guard can refuse it
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)


@pytest.mark.parametrize("name", CHECKS["INSTALL_CHECKS_V4"][1:])
def test_gap_every_check_decides_the_overall_flag_of_a_v4_record(name):
    value = receipt()
    value["results"][0][name] = "failed"
    value["passed"] = False
    assert CHECKS["summarize"](value)["passed"] is False
    value["passed"] = True
    with pytest.raises(ValueError):
        CHECKS["summarize"](value)


@pytest.mark.parametrize(
    ("version", "kind"), [(3, "installation_v4"), (4, "installation_v3"), (True, "installation_v4")]
)
def test_gap_the_v4_reader_itself_checks_its_schema_and_kind(version, kind):
    value = receipt()
    value.update(schema_version=version, report_kind=kind)
    with pytest.raises(ValueError):
        CHECKS["installation_summary_v4"](value)
