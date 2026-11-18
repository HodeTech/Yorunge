"""The two phases of a download target (P02-4f): taken with the lock, settled once.

A held target that is given no identity decides nothing and leaves nothing; an identity is
settled once, and a second settle is a programming error, not a second decision.
"""

import pytest

from yorunge.adapters.download_sink import open_held_sink

KEY = "a" * 64


def test_a_held_target_that_settles_nothing_leaves_no_trace_and_releases_the_lock(tmp_path):
    target = tmp_path / "weights.onnx"
    with open_held_sink(target):
        pass
    assert list(tmp_path.iterdir()) == []
    with open_held_sink(target):  # the lock is released: a second take succeeds
        pass


def test_a_settled_identity_is_decided_once(tmp_path):
    target = tmp_path / "weights.onnx"
    with open_held_sink(target) as sink:
        sink.settle(KEY)
        with pytest.raises(AssertionError):
            sink.settle(KEY)
