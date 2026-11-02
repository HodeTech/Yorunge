"""Copied/constructed request inputs cannot emit their rejected values or warnings."""

import warnings

import pytest

from tests.contracts.test_platform_upload_codec import PARAMETERS, PLAN, SCOPE, SECRET
from yorunge.application.platform_upload_codec import create_content
from yorunge.application.upload_inputs import revalidate_input
from yorunge.domain.dataset_upload import UploadOwner
from yorunge.domain.errors import YorungeError


class NeverRepr:
    def __repr__(self):
        pytest.fail("invalid input repr must never be evaluated")


@pytest.mark.parametrize("field", list(type(PARAMETERS).model_fields))
@pytest.mark.parametrize("value", [123456789, NeverRepr()])
def test_invalid_parameter_fields_never_warn_or_keep_error_chain(field, value, capsys):
    copied = PARAMETERS.model_copy(update={field: value})
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("error")
        with pytest.raises(YorungeError) as failure:
            create_content(SCOPE, copied, SECRET)
    assert failure.value.code == "invalid_request"
    assert failure.value.__context__ is None and failure.value.__cause__ is None
    assert observed == [] and capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "change",
    [
        {"credential_revision": True},
        {"profile": 123456789},
        {"owner": UploadOwner.model_construct(kind="user", id=123456789)},
        {"owner": UploadOwner.model_construct(kind=NeverRepr(), id=NeverRepr())},
    ],
)
def test_invalid_nested_scope_is_checked_before_json_normalizes_it(change, capsys):
    copied = SCOPE.model_copy(update=change)
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("error")
        with pytest.raises(YorungeError) as failure:
            create_content(copied, PARAMETERS, SECRET)
    assert failure.value.code == "invalid_request" and failure.value.__context__ is None
    assert observed == [] and capsys.readouterr() == ("", "")


def test_nested_plan_input_has_same_warning_free_boundary():
    bad = PLAN.model_copy(
        update={"parameters": PARAMETERS.model_copy(update={"name": NeverRepr()})}
    )
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("error")
        with pytest.raises(YorungeError) as failure:
            revalidate_input(type(PLAN), bad)
    assert failure.value.code == "invalid_request" and observed == []
    assert failure.value.__context__ is None
