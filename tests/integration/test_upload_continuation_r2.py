"""What round two of P02-3i found a journey for: the way out of an answer that cannot be believed.

The card hands over one case from P02-3w: a continuation whose confirm answer lies about the count
ends `operation_uncertain` for the reason `invalid_response`, and the generic words of that error
send a person to `reconcile` — which cannot close the graph of such a continuation. The commands'
own words must lead out: `show` names `resume`, and `resume --prepare` finishes the dataset.
"""

import json

from tests.fixtures.http_server import TlsServer
from tests.integration.test_upload_continuation_cli import Journey, no_secret_anywhere, world
from tests.integration.test_upload_preparation import certificates as certificates
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_public_api import public_inputs as public_inputs

FLAGS = ("--accept-unverified-authority", "--accept-unpriced-cost")


def test_a_continuation_whose_confirm_count_lies_is_led_out_by_show_not_by_reconcile(
    public_inputs, certificates
):
    data, manifest, config, provider = world(public_inputs)
    with TlsServer(certificates, provider.routes()) as server:
        machine = Journey(server, data, manifest, config, "json")
        source = machine.plan_and_stop(provider)
        provider.represign = True
        prepared, _ = machine.done(
            machine.run("resume", "--operation-id", source, "--accept-unverified-read", "--prepare")
        )
        machine.done(
            machine.run(
                "approve",
                "--plan-id",
                prepared["plan_id"],
                "--confirm",
                prepared["plan_digest"],
                *FLAGS,
            )
        )

        # the provider's confirm answer counts wrongly: the continuation cannot be believed
        provider.wrong_confirm_count = True
        lied = machine.run("start", "--plan-id", prepared["plan_id"])
        envelope = machine.failed(lied, "operation_uncertain", 5)
        continuation = envelope["operation_id"]
        assert continuation not in (None, source)
        assert envelope["details"]["reason_code"] == "invalid_response"

        # the words of that error are the generic ones; they send a person to `reconcile` ...
        person = Journey(server, data, manifest, config, "text")
        text = person.run("start", "--plan-id", prepared["plan_id"]).stderr.decode()
        assert (
            "uzlaştırın" in text
            and f"İncele: yorunge datasets upload show --operation-id {continuation}" in text
        )

        # ... which cannot close this graph: it ends with the same words, a dead end
        reconcile = person.run(
            "reconcile", "--operation-id", continuation, "--accept-unverified-read"
        )
        assert reconcile.returncode == 5 and reconcile.stdout == b""
        assert "uzlaştırın" in reconcile.stderr.decode()

        # `show` is what leads out: the journal says a new report is the way
        shown = person.run("show", "--operation-id", continuation, context=False)
        assert shown.returncode == 0
        shown_text = shown.stdout.decode()
        assert (
            f"Devam için: yorunge datasets upload resume --operation-id {continuation} "
            "--accept-unverified-read"
        ) in shown_text

        # and the commands finish it, once the provider counts honestly again
        provider.wrong_confirm_count = False
        second, _ = machine.done(
            machine.run(
                "resume", "--operation-id", continuation, "--accept-unverified-read", "--prepare"
            )
        )
        machine.done(
            machine.run(
                "approve",
                "--plan-id",
                second["plan_id"],
                "--confirm",
                second["plan_digest"],
                *FLAGS,
            )
        )
        finished, _ = machine.done(machine.run("start", "--plan-id", second["plan_id"]))
        assert finished["operation_status"] == "succeeded"
        assert finished["continuation_of"] == continuation
        assert sorted(provider.confirmed) == sorted(file.path for file in data[2].files)
        assert json.loads(json.dumps(finished))["verification_level"] == "metadata"
        no_secret_anywhere(machine)
        no_secret_anywhere(person)
