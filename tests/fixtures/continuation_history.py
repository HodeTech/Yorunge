"""A real root upload and the continuations chained to it, as the rows a store would hold.

The root is the v2 history of ``dataset-transfer-graph-v2.json`` whose create receipt is the strict
``dataset-create-receipt-v2.json``. Each continuation is derived here from the v3 fixtures with
plain ``hashlib``/``json``: no digest, formula or validator of the product is used to build it, so
a test can tell a right binding from a wrong one. Dictionaries stay plain until ``install``, so a
test can break exactly one thing first.

The histories are right in everything the read side checks and wrong in time: a continuation is
prepared before its root was created, shares the root's ``created_at`` and sends while the root
still does. The chronology rule is the write gate's (P02-3r); when it lands these must be re-timed.
"""

import copy
import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from tests.fixtures.upload_history import install_fixture
from yorunge.adapters.state import open_store

FIXTURES = Path(__file__).parent


def fixture(name):
    return json.loads((FIXTURES / name).read_bytes())


def canon(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def sha(value):
    return hashlib.sha256(canon(value)).hexdigest()


def uuid(number):
    return f"00000000-0000-4000-8000-{number:012x}"


CREATE_RECEIPT = (FIXTURES / "dataset-create-receipt-v2.json").read_bytes()
CREATED = json.loads(CREATE_RECEIPT)["created_dataset"]
DATASET_ID = CREATED["id"]
BASELINE_DIGEST = sha({"kind": "upload_baseline", "dataset": CREATED})
MANIFEST = fixture("dataset-manifest-v1.json")
FILES = MANIFEST["files"]
GRAPH = fixture("dataset-transfer-graph-v2.json")
BASE_PLAN = fixture("dataset-continuation-plan-v3.json")
CHECK_ONLY_PLAN = fixture("dataset-continuation-plan-v3-verification-only.json")
BASE_APPROVAL = fixture("dataset-continuation-approval-v3.json")
BASE_RECORD = fixture("dataset-continuation-record-v3-admitted.json")
BASE_PROOF = fixture("dataset-continuation-verification-v3.json")
INTENT_SHAPE = GRAPH["intents"][3]

CREATED_AT = "2026-11-02T11:00:02.000000Z"


def stamp(seconds):
    whole, fraction = divmod(round(seconds * 1000), 1000)
    return f"2026-11-02T11:{whole // 60:02d}:{whole % 60:02d}.{fraction:03d}000Z"


def install_root(store, *, terminal=False, partial=True, strict=True, scope=None):
    """The root upload, ``unknown`` unless ``terminal``, as a continuation would find it.

    ``partial`` (the default) stops it where an interrupted upload stops: the first file is
    confirmed, the second has a confirm intent nothing answered, the third was never reached. A
    complete root (``partial=False``) is one to reconcile, not to continue. ``strict`` gives its
    create intent the strict create receipt; without it the root made no dataset it can prove.
    ``scope`` re-addresses the root's scope (see ``install_fixture``).
    """
    data = install_fixture(store, terminal=terminal, scope=scope)
    connection = store.connection
    if strict:
        connection.execute(
            "UPDATE upload_stage_receipts SET payload=? WHERE intent_id=?",
            (CREATE_RECEIPT.decode(), data["receipts"][0]["intent_id"]),
        )
    if partial and not terminal:
        dropped = [intent["intent_id"] for intent in data["intents"][8:]]
        answered = [data["receipts"][7]["intent_id"], *dropped]
        for intent_id in answered:
            connection.execute("DELETE FROM upload_stage_receipts WHERE intent_id=?", (intent_id,))
        for intent_id in dropped:
            connection.execute("DELETE FROM upload_stage_intents WHERE intent_id=?", (intent_id,))
    return data


def reservation(selected, files=3):
    """The journal reservation of a continuation sending ``selected`` files of ``files``."""
    return 16 * 1024 + 3 * selected * 4096 + 20 * 1024 + files * 512


@dataclass
class Continuation:
    plan: dict
    approval: dict
    record: dict | None
    intents: list = field(default_factory=list)
    receipts: list = field(default_factory=list)
    controls: list = field(default_factory=list)
    proof: dict | None = None

    @property
    def selected(self):
        return len(self.plan["continuation"]["file_indices"])


def build(
    root,
    number,
    *,
    source=None,
    indices=(1, 2),
    uncertain=None,
    status="running",
    intents=None,
    acknowledged=None,
    binding=None,
    plan_changes=None,
    reset=False,
):
    """A continuation of ``root`` (the data ``install_root`` returned) from ``source``.

    ``status`` is admitted, running, unknown, succeeded, failed or cancelled. ``intents`` stages
    have been written (all of them for a succeeded one, the first two for a failed one) and the
    first ``acknowledged`` have an accepted receipt; the last receipt of a failed one is a
    rejection. An empty ``indices`` is the check-only continuation. ``binding`` overrides fields
    of the plan's continuation binding and ``plan_changes`` those of the plan itself, before it is
    sealed (a wrong baseline or other parameters, say). ``reset`` (succeeded only) puts an
    identity reset between the sending and the proof: the proof is read under a new epoch and
    clock generation.
    """
    root_scope = root["plan"]["scope"]
    root_operation = root["record"]["operation_id"]
    stages = [(kind, index) for index in indices for kind in ("presign", "put", "confirm")]
    if intents is None:
        intents = len(stages) if status in ("succeeded", "unknown") else 0
        intents = 1 if status == "running" and intents == 0 else intents
        intents = 2 if status == "failed" else intents
    if acknowledged is None:
        acknowledged = intents
    if status == "succeeded":
        intents = acknowledged = len(stages)

    plan = copy.deepcopy(CHECK_ONLY_PLAN if not indices else BASE_PLAN)
    # Against the default root: the second file has an unanswered confirm, the third none at all.
    uncertain = tuple(i for i in (1,) if i in indices) if uncertain is None else uncertain
    plan.update(
        plan_id=uuid(0x100 + number),
        scope=copy.deepcopy(root_scope),
        request_limits={
            **plan["request_limits"],
            "max_presign": len(indices),
            "max_put": len(indices),
            "max_confirm": len(indices),
            "max_upload_bytes": sum(FILES[i]["size"] for i in indices),
        },
    )
    plan["continuation"].update(
        source_operation_id=source or root_operation,
        baseline_operation_id=root_operation,
        dataset_id=DATASET_ID,
        baseline_digest=BASELINE_DIGEST,
        intent_digest=root["record"]["intent_digest"],
        file_indices=list(indices),
        uncertain_indices=list(uncertain),
        remote_present_count=len(FILES) - len(indices),
    )
    plan["continuation"].update(binding or {})
    plan.update(plan_changes or {})
    plan["digest"] = sha({k: v for k, v in plan.items() if k != "digest"})

    binding = {
        k: v for k, v in plan.items() if k not in ("plan_id", "digest", "prepared_at", "expires_at")
    }
    for name in ("grant", "cost_bound"):
        if binding[name] is not None:
            binding[name] = {
                k: v for k, v in binding[name].items() if k not in ("checked_at", "expires_at")
            }
    binding["continuation"] = {
        k: v for k, v in binding["continuation"].items() if k != "observed_at"
    }
    approval = {
        **BASE_APPROVAL,
        "approval_id": uuid(0x200 + number),
        "plan_id": plan["plan_id"],
        "plan_digest": plan["digest"],
        "binding_digest": sha(binding),
        "store_id": root_scope["store_id"],
        "identity_epoch": root_scope["identity_epoch"],
        "acknowledge_unconfirmed_effects": bool(uncertain),
    }

    owner = {
        "owner_id": BASE_RECORD["write_owner_id"],
        "fence": 1,
        "identity_epoch": root_scope["identity_epoch"],
        "clock_generation": 1,
        "mode": "write",
        "renewed_at": CREATED_AT,
        "expires_at": "2026-11-02T11:02:32.000000Z",
    }
    operation = uuid(0x300 + number)
    written, receipts = [], []
    for position, (kind, index) in enumerate(stages[:intents], 1):
        intended = 2 + position
        key = f"objects/{index}"
        request = {
            "plan_digest": plan["digest"],
            "kind": kind,
            "file_index": index,
            "file": FILES[index],
            "dataset_id": DATASET_ID,
            "object_key": key if kind in ("put", "confirm") else None,
        }
        intent_id = uuid(0x1000 + number * 0x40 + position)
        written.append(
            {
                **INTENT_SHAPE,
                "intent_id": intent_id,
                "operation_id": operation,
                "sequence": position,
                "kind": kind,
                "file_index": index,
                "owner": owner,
                "intended_at": stamp(intended),
                "expires_at": stamp(intended + 30),
                "request_digest": sha(request),
            }
        )
        if position <= acknowledged:
            receipts.append(
                {
                    "schema_version": 1,
                    "intent_id": intent_id,
                    "dataset_id": DATASET_ID,
                    "result": "accepted",
                    "recorded_at": stamp(intended + 0.5),
                    "object_key": key,
                    "sent_bytes": FILES[index]["size"] if kind == "put" else None,
                    "sent_sha256": FILES[index]["sha256"] if kind == "put" else None,
                }
            )
    last = 2 + (intents or 0)
    record = {
        **BASE_RECORD,
        "operation_id": operation,
        "plan_id": plan["plan_id"],
        "plan_digest": plan["digest"],
        "intent_digest": plan["continuation"]["intent_digest"],
        "approval": approval,
        "dataset_id": DATASET_ID,
        "observed_identity_epoch": root_scope["identity_epoch"],
        "verification_only": not indices,
        "created_at": CREATED_AT,
        "updated_at": stamp(last),
        "revision": 1 + intents,
        "workflow_latched": intents > 0,
        "lease": owner,
        "status": "admitted" if status == "admitted" else "running",
        "reason": None,
    }
    controls, proof = [], None
    if status in ("unknown", "succeeded", "cancelled", "failed"):
        record.update(lease=None, revision=record["revision"] + 1, updated_at=stamp(last + 3))
    if status == "unknown":
        record.update(status="unknown", reason="request_uncertain")
        controls = [_control(record, "recovery", None)]
    elif status == "cancelled":
        record.update(status="cancelled", reason="lease_expired")
        controls = [_control(record, "terminal", None)]
    elif status == "failed":
        # The last answered stage was refused for good, with nothing left in flight.
        receipts[-1] = {
            **receipts[-1],
            "result": "rejected",
            "dataset_id": None,
            "object_key": None,
            "sent_bytes": None,
            "sent_sha256": None,
        }
        record.update(status="failed", reason="provider_rejected")
        controls = [_control(record, "terminal", None)]
    elif status == "succeeded":
        proof = _proof(plan, stamp(last + 2))
        record.update(status="succeeded", reason="metadata_verified")
        if reset:
            new_epoch = uuid(0xE2)
            record.update(observed_identity_epoch=new_epoch, observed_clock_generation=2)
            proof["scope"].update(identity_epoch=new_epoch, clock_generation=2)
        controls = [_control(record, "terminal", sha(proof))]
        if reset:
            recovery = _control({**record, "revision": record["revision"] - 1}, "recovery", None)
            recovery.update(reason="identity_reset", observed_at=stamp(last + 1))
            controls.append(recovery)
    return Continuation(plan, approval, record, written, receipts, controls, proof)


def _control(record, kind, proof_digest):
    return {
        "schema_version": 3,
        "operation_id": record["operation_id"],
        "kind": kind,
        "revision": record["revision"],
        "observed_at": record["updated_at"],
        "identity_epoch": record["observed_identity_epoch"],
        "clock_generation": record["observed_clock_generation"],
        "reason": record["reason"],
        "verification_digest": proof_digest,
    }


def _proof(plan, observed_at):
    return {
        **copy.deepcopy(BASE_PROOF),
        "dataset_id": DATASET_ID,
        "scope": copy.deepcopy(plan["scope"]),
        "observed_at": observed_at,
    }


def install(store, c, *, plan=True, approval=True):
    """Insert a continuation's rows (the root's namespace and manifest are already there)."""
    connection = store.connection
    if plan:
        connection.execute(
            "INSERT INTO upload_plans VALUES(?,?,?,?,?,?)",
            (
                c.plan["plan_id"],
                c.plan["continuation"]["intent_digest"],
                c.plan["manifest"]["digest"],
                c.plan["prepared_at"],
                c.plan["expires_at"],
                canon(c.plan).decode(),
            ),
        )
    if approval:
        connection.execute(
            "INSERT INTO upload_approvals VALUES(?,?,?,?)",
            (
                c.plan["plan_id"],
                c.approval["approval_id"],
                c.approval["expires_at"],
                canon(c.approval).decode(),
            ),
        )
    if c.record is None:
        return
    record = c.record
    connection.execute(
        "INSERT INTO upload_operations VALUES(?,?,?,?,?,?,?)",
        (
            record["operation_id"],
            record["plan_id"],
            record["intent_digest"],
            record["revision"],
            record["lease"]["expires_at"] if record["lease"] else None,
            reservation(c.selected),
            canon(record).decode(),
        ),
    )
    for intent in c.intents:
        connection.execute(
            "INSERT INTO upload_stage_intents VALUES(?,?,?,?,?,?)",
            (
                intent["intent_id"],
                intent["operation_id"],
                intent["sequence"],
                intent["kind"],
                intent["file_index"] if intent["file_index"] is not None else -1,
                canon(intent).decode(),
            ),
        )
    for receipt in c.receipts:
        connection.execute(
            "INSERT INTO upload_stage_receipts VALUES(?,?)",
            (receipt["intent_id"], canon(receipt).decode()),
        )
    for control in c.controls:
        connection.execute(
            "INSERT INTO upload_controls VALUES(?,?,?)",
            (record["operation_id"], control["kind"], canon(control).decode()),
        )
    if c.proof is not None:
        connection.execute(
            "INSERT INTO upload_verifications VALUES(?,?)",
            (record["operation_id"], canon(c.proof).decode()),
        )


OTHER = uuid(0x999)
FIRST, SECOND = uuid(0x301), uuid(0x302)  # the operations of continuations numbered 1 and 2

SHAPES = {
    "admitted": {"status": "admitted"},
    "running, one stage sent": {"status": "running", "intents": 1, "acknowledged": 1},
    "running, a stage in flight": {"status": "running", "intents": 4, "acknowledged": 3},
    "unknown": {"status": "unknown", "intents": 5, "acknowledged": 4},
    "succeeded": {"status": "succeeded"},
    "cancelled": {"status": "cancelled"},
    "failed": {"status": "failed"},
    "check-only admitted": {"status": "admitted", "indices": ()},
    "check-only succeeded": {"status": "succeeded", "indices": ()},
    "check-only cancelled": {"status": "cancelled", "indices": ()},
}
UNKNOWN = SHAPES["unknown"]


@contextmanager
def world(tmp_path, *specs, timeout=60.0):
    """A store with the root and the continuations ``specs`` describe.

    A spec is ``build`` keywords, plus ``tweak`` (a function that breaks one thing of the built
    continuation before it is stored) and ``plan_only`` (store its plan and approval, no operation).
    """
    with open_store(tmp_path / "state", timeout=timeout) as store:
        root = install_root(store)
        built = []
        for number, spec in enumerate(specs, 1):
            spec = dict(spec)
            tweak = spec.pop("tweak", None)
            plan_only = spec.pop("plan_only", False)
            item = build(root, number, **spec)
            if tweak is not None:
                tweak(item)
            if plan_only:
                item.record = None
            install(store, item)
            built.append(item)
        yield store, root, built
