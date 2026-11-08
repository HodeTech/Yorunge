"""The unconfirmed-effects flag through real CLI processes (P02-3i R1-B).

A plan with files whose last confirm may or may not have landed is prepared and approved with the
flag and only with it, and a repeated flag is a bad request.
"""

import json

from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_continuation_cli import Journey, world
from tests.integration.test_upload_continuation_cli import certificates as certificates
from tests.integration.test_upload_continuation_cli import loopback_only as loopback_only
from tests.integration.test_upload_continuation_cli import prepared_input as prepared_input
from tests.integration.test_upload_continuation_cli import public_inputs as public_inputs

FLAGS = ["--accept-unverified-authority", "--accept-unpriced-cost"]


def test_a_plan_with_unconfirmed_files_is_approved_with_the_flag_and_only_with_it(
    public_inputs, certificates
):
    data, manifest, config, provider = world(public_inputs, remembered=False)
    with TlsServer(certificates, provider.routes()) as server:
        journey = Journey(server, data, manifest, config, "json")
        source = journey.plan_and_stop(provider)
        provider.represign = True
        # the provider stops losing the answer of the confirm now (the lost one is not re-lost)
        provider.route_table[f"/api/v1/datasets/{DATASET}/upload/confirm"] = (
            UploadProvider.confirm.__get__(provider)
        )
        base = ["resume", "--operation-id", source, "--accept-unverified-read", "--prepare"]
        refused = journey.run(*base)
        assert journey.failed(refused, "approval_required", 4)["operation_id"] == source
        prepared, _ = journey.done(journey.run(*base, "--accept-unconfirmed-effects"))
        assert prepared["observation"]["class_counts"]["pending_uncertain"] == 1
        approve = [
            "approve",
            "--plan-id",
            prepared["plan_id"],
            "--confirm",
            prepared["plan_digest"],
        ]
        assert journey.failed(journey.run(*approve, *FLAGS), "approval_required", 4)
        approved, _ = journey.done(journey.run(*approve, *FLAGS, "--accept-unconfirmed-effects"))
        assert approved["approval_status"] == "approved" and approved["uncertain_files"] == 1
        started, _ = journey.done(journey.run("start", "--plan-id", prepared["plan_id"]))
        assert started["operation_status"] == "succeeded"
        assert started["continuation_files"] == 2 and started["uncertain_files"] == 1


def test_a_repeated_unconfirmed_flag_is_an_invalid_request(public_inputs, certificates):
    data, manifest, config, provider = world(public_inputs)
    with TlsServer(certificates, provider.routes()) as server:
        journey = Journey(server, data, manifest, config, "json")
        source = journey.plan_and_stop(provider)
        for verb in (
            ["resume", "--operation-id", source, "--prepare"],
            ["approve", "--plan-id", source, "--confirm", "0" * 64],
        ):
            twice = journey.run(
                *verb, "--accept-unconfirmed-effects", "--accept-unconfirmed-effects"
            )
            assert twice.returncode == 2 and twice.stdout == b""
            assert json.loads(twice.stderr)["code"] == "invalid_request"
