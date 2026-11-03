"""A recycled numeric ID never transfers ownership to another actual Thread."""

import asyncio
import importlib
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from yorunge.adapters.dataset_files import open_dataset
from yorunge.application.datasets import DatasetBudget
from yorunge.application.http_transport import HttpRequest
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.dataset_upload import UploadRoot
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile
from yorunge.domain.upload_costs import UploadRequestLimits

MODULES = {
    "session": "yorunge.adapters.http_session",
    "transport": "yorunge.adapters.http_transport",
    "stream": "yorunge.application.stream_results",
    "budget": "yorunge.application.upload_budget",
    "input": "yorunge.adapters.upload_input_files",
    "source": "yorunge.adapters.storage_source",
    "preparation": "yorunge.adapters.upload_preparation",
}


def resource(kind, module, root, manifest):
    if kind == "session":
        return module.HttpSession()
    if kind == "transport":
        return module.HttpxTransport()
    if kind == "budget":
        body = json.loads(
            (Path(__file__).parents[1] / "fixtures/dataset-upload-plan-v2.json").read_text()
        )
        limits = UploadRequestLimits.model_validate_json(json.dumps(body["request_limits"]))
        return module.UploadBudget(limits, end=time.monotonic() + 60, read_only=True)
    if kind == "input":
        return module.capture_upload_input(
            root, manifest, SecretValue("test-owner-secret"), end=time.monotonic() + 60
        )
    if kind == "source":
        info = root.stat()
        bound_root = UploadRoot(anchor=str(root), device=info.st_dev, inode=info.st_ino)
        return module.DescriptorByteSource(
            bound_root, manifest.files[0], deadline=time.monotonic() + 60
        )
    if kind == "preparation":
        profile = Profile()
        context = Context(
            profile="test",
            account_id=None,
            project_id=str(uuid4()),
            platform_url=profile.platform_url,
            llm_url=profile.llm_url,
        )
        return module.UploadPreparationRuntime(context, profile, None)

    class Trap:
        def open(self, *args, **kwargs):
            raise YorungeError("transport_failed")

    request = HttpRequest(
        normalize_target("https://api.ssyz.org.tr/api/v1"),
        "GET",
        "auth/me",
        service_id="evren-platform",
        read_only=True,
    )
    return module.OwnedStream(
        Trap(),
        request,
        Context,
        deadline=time.monotonic() + 60,
        stream_id=str(uuid4()),
        operation_id=None,
        secrets=(),
    )


def access(kind, value):
    if kind == "budget":
        value.snapshot()
    elif kind == "input":
        value.recheck()
    elif kind == "preparation":
        with value._invocation():
            pass
    elif kind == "session":
        with value:
            pass
    else:

        async def consume():
            async with value:
                if kind == "source":
                    async for _ in value:
                        pass

        asyncio.run(consume())


@pytest.mark.parametrize("kind", MODULES)
def test_recycled_numeric_thread_id_cannot_transfer_a_resource(kind, tmp_path, monkeypatch):
    module = importlib.import_module(MODULES[kind])
    # Patch only the target module's numeric-ID observation. Thread lifecycle,
    # current_thread(), asyncio and actual filesystem/network ownership stay real.
    monkeypatch.setattr(
        module,
        "threading",
        SimpleNamespace(get_ident=lambda: 17, current_thread=threading.current_thread),
    )
    root = tmp_path.resolve() / "source"
    root.mkdir()
    (root / "sample.bin").write_bytes(b"content")
    with open_dataset(root, DatasetBudget()) as tree:
        manifest = tree.scan()
    captured, failures = [], []

    def issue():
        try:
            captured.append(resource(kind, module, root, manifest))
        except BaseException as error:
            failures.append(error)

    issuer = threading.Thread(target=issue)
    issuer.start()
    issuer.join(5)
    assert not issuer.is_alive()
    assert not failures
    assert len(captured) == 1

    def claim():
        try:
            access(kind, captured[0])
        except BaseException as error:
            failures.append(error)

    claimant = threading.Thread(target=claim)
    claimant.start()
    claimant.join(5)
    assert not claimant.is_alive()
    assert claimant is not issuer
    assert len(failures) == 1
    assert isinstance(failures[0], YorungeError)
    assert failures[0].code == "invalid_request"
