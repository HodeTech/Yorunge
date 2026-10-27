"""Validate real synthetic archives before any installer or extraction is invoked."""

import io
import runpy
import stat
import tarfile
import warnings
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/verify-distributions.py"
CHECKS = runpy.run_path(str(SCRIPT))
inspect_archive = CHECKS["inspect_archive"]
distribution_pair = CHECKS["distribution_pair"]
ROOT = "yorunge-0.1.0.dev0"
METADATA = "yorunge-0.1.0.dev0.dist-info"


def wheel(tmp_path, entries):
    path = tmp_path / f"{ROOT}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive, warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Duplicate name:", category=UserWarning)
        for name, mode in entries:
            item = zipfile.ZipInfo(name)
            item.create_system = 3
            item.external_attr = mode << 16
            archive.writestr(item, b"synthetic")
    return path


def sdist(tmp_path, entries):
    path = tmp_path / f"{ROOT}.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        for name, kind in entries:
            item = tarfile.TarInfo(name)
            item.type = kind
            if kind in (tarfile.REGTYPE, tarfile.AREGTYPE):
                item.size = 1
                archive.addfile(item, io.BytesIO(b"x"))
            else:
                item.linkname = (
                    "synthetic-target" if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ""
                )
                archive.addfile(item)
    return path


def test_valid_archive_files_and_explicit_directories(tmp_path):
    binary = wheel(
        tmp_path,
        [
            ("yorunge/", stat.S_IFDIR | 0o755),
            ("yorunge/__init__.py", stat.S_IFREG | 0o644),
            (f"{METADATA}/METADATA", 0o644),
        ],
    )
    source = sdist(
        tmp_path,
        [
            (ROOT + "/", tarfile.DIRTYPE),
            (ROOT + "/.github/workflows/", tarfile.DIRTYPE),
            (ROOT + "/.github/workflows/checks.yml", tarfile.REGTYPE),
            (ROOT + "/.agents/skills/yorunge-example/agents/", tarfile.DIRTYPE),
            (ROOT + "/.agents/skills/yorunge-example/agents/openai.yaml", tarfile.REGTYPE),
            (ROOT + "/docs/reference/", tarfile.DIRTYPE),
            (ROOT + "/docs/reference/configuration.md", tarfile.REGTYPE),
            (ROOT + "/docs/analysis/README.md", tarfile.REGTYPE),
            (ROOT + "/pyproject.toml", tarfile.REGTYPE),
        ],
    )
    assert "yorunge/__init__.py" in inspect_archive(binary)
    assert "pyproject.toml" in inspect_archive(source)
    assert distribution_pair(tmp_path) == (binary, source)


@pytest.mark.parametrize(
    "name",
    [
        "/yorunge/file.py",
        "../yorunge/file.py",
        "yorunge/../file.py",
        "yorunge/./file.py",
        "yorunge//file.py",
        "yorunge\\file.py",
        "C:/yorunge/file.py",
        "yorunge/unsafe\x1b.py",
        "yorunge/__pycache__/file.pyc",
        "other/file.py",
        "other.dist-info/METADATA",
        "yorunge-0.0.0.dist-info/METADATA",
        "yorunge",
    ],
)
def test_wheel_rejects_unsafe_or_unexpected_names(tmp_path, name):
    path = wheel(tmp_path, [(name, stat.S_IFREG | 0o644)])
    with pytest.raises(ValueError):
        inspect_archive(path)


@pytest.mark.parametrize(
    "kind", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFSOCK]
)
def test_wheel_rejects_links_and_special_files(tmp_path, kind):
    path = wheel(tmp_path, [("yorunge/member", kind | 0o644)])
    with pytest.raises(ValueError, match="links and special"):
        inspect_archive(path)


@pytest.mark.parametrize("kind", [stat.S_IFREG, stat.S_IFDIR])
def test_wheel_rejects_directory_type_name_mismatch(tmp_path, kind):
    name = "yorunge/member/" if kind == stat.S_IFREG else "yorunge/member"
    with pytest.raises(ValueError):
        inspect_archive(wheel(tmp_path, [(name, kind | 0o755)]))


@pytest.mark.parametrize(
    "name",
    [
        "../pyproject.toml",
        "/pyproject.toml",
        "wrong-root/README.md",
        ROOT + "/../README.md",
        ROOT + "/./README.md",
        ROOT + "//README.md",
        ROOT + "/src\\file.py",
        ROOT + "/src/unsafe\x85.py",
        ROOT + "/src/__pycache__/file.pyc",
        ROOT + "/docs/analysis/not-public.md",
        ROOT + "/docs/README.md/child",
        ROOT + "/.github/unsafe.yml",
        ROOT + "/.agents/settings.json",
        ROOT + "/src",
        ROOT,
    ],
)
def test_sdist_rejects_raw_unsafe_roots_and_unexpected_paths(tmp_path, name):
    with pytest.raises(ValueError):
        inspect_archive(sdist(tmp_path, [(name, tarfile.REGTYPE)]))


@pytest.mark.parametrize(
    "kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE]
)
def test_sdist_rejects_links_and_special_files(tmp_path, kind):
    with pytest.raises(ValueError, match="links and special"):
        inspect_archive(sdist(tmp_path, [(ROOT + "/src/member", kind)]))


def test_sdist_rejects_multiple_roots(tmp_path):
    entries = [(ROOT + "/README.md", tarfile.REGTYPE), ("another/pyproject.toml", tarfile.REGTYPE)]
    with pytest.raises(ValueError, match="root"):
        inspect_archive(sdist(tmp_path, entries))


def test_sdist_file_allowlist_entry_cannot_be_a_directory(tmp_path):
    entries = [(ROOT + "/.github/pull_request_template.md/", tarfile.DIRTYPE)]
    with pytest.raises(ValueError):
        inspect_archive(sdist(tmp_path, entries))


@pytest.mark.parametrize("format", ["wheel", "sdist"])
@pytest.mark.parametrize("conflict", ["duplicate", "file-parent", "directory-alias"])
def test_archives_reject_duplicate_and_conflicting_entries(tmp_path, format, conflict):
    first = "yorunge/file" if format == "wheel" else ROOT + "/src/file"
    second = (
        first
        if conflict == "duplicate"
        else first + ("/child" if conflict == "file-parent" else "/")
    )
    directory = conflict == "directory-alias"
    if format == "wheel":
        kinds = (stat.S_IFREG | 0o644, (stat.S_IFDIR if directory else stat.S_IFREG) | 0o644)
        path = wheel(tmp_path, [(first, kinds[0]), (second, kinds[1])])
    else:
        path = sdist(
            tmp_path,
            [(first, tarfile.REGTYPE), (second, tarfile.DIRTYPE if directory else tarfile.REGTYPE)],
        )
    with pytest.raises(ValueError):
        inspect_archive(path)


@pytest.mark.parametrize("format", ["wheel", "sdist"])
def test_empty_distributions_rejected(tmp_path, format):
    path = wheel(tmp_path, []) if format == "wheel" else sdist(tmp_path, [])
    with pytest.raises(ValueError, match="empty"):
        inspect_archive(path)


@pytest.mark.parametrize("case", ["none", "two-wheels", "two-sdists", "mismatch"])
def test_distribution_selection_requires_one_matching_pair(tmp_path, case):
    names = {
        "none": [],
        "two-wheels": [f"{ROOT}-py3-none-any.whl", f"{ROOT}-py311-none-any.whl"],
        "two-sdists": [f"{ROOT}.tar.gz", "yorunge-0.0.0.tar.gz"],
        "mismatch": [f"{ROOT}-py3-none-any.whl", "yorunge-0.0.0.tar.gz"],
    }[case]
    for name in names:
        (tmp_path / name).touch()
    with pytest.raises(ValueError):
        distribution_pair(tmp_path)
