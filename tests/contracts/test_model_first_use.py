"""Cold schema, validation and concurrent first use retain strict canonical wire."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = """
import json,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

sys.path.insert(0, str(Path(sys.argv[1]) / 'src'))
from pydantic import ValidationError
from yorunge.domain.capabilities import canonical
from yorunge.application.response_json import check_response_secrets
from yorunge.domain.credentials import SecretValue
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2

wire = (Path(sys.argv[1]) / 'tests/fixtures/dataset-upload-plan-v2.json').read_bytes()
expected = canonical(json.loads(wire))
mode = sys.argv[2]
if mode == 'schema':
    schema = DatasetUploadPlanV2.model_json_schema()
    assert schema['additionalProperties'] is False
    assert 'schema_version' in schema['required']
if mode == 'threads':
    barrier = Barrier(8)
    def validate(_):
        barrier.wait(timeout=5)
        return DatasetUploadPlanV2.model_validate_json(wire).encoded()
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(validate, range(8))) == [expected] * 8
else:
    assert DatasetUploadPlanV2.model_validate_json(wire).encoded() == expected
value = DatasetUploadPlanV2.model_validate_json(wire)
check_response_secrets(value, (SecretValue('unrelated-long-secret-canary'),))
for field,bad in [('schema_version',True),('inputs_verified',1),('policy_version','2')]:
    invalid = json.loads(wire)
    invalid[field] = bad
    try:
        DatasetUploadPlanV2.model_validate(invalid)
    except ValidationError:
        pass
    else:
        raise AssertionError('strict first-use validation was bypassed')
try:
    value.policy_version = 2
except ValidationError:
    pass
else:
    raise AssertionError('frozen model was mutated')
invalid = json.loads(wire)
invalid['schema_version'] = 'private-invalid-input-canary'
try:
    DatasetUploadPlanV2.model_validate(invalid)
except ValidationError as error:
    assert 'private-invalid-input-canary' not in str(error)
else:
    raise AssertionError('invalid version accepted')
print('cold strict canonical validation passed')
"""


@pytest.mark.parametrize("mode", ["validate", "schema", "threads"])
def test_fresh_process_first_use_preserves_schema_wire_and_rejection(mode):
    result = subprocess.run(
        [sys.executable, "-I", "-c", PROGRAM, str(ROOT), mode],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert result.stdout == b"cold strict canonical validation passed\n"
    assert not result.stderr
