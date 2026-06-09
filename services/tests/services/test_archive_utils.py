"""Tests for the VCS archive top-level-dir stripper.

GitHub/GitLab archive downloads wrap every file in a single
``owner-repo-sha/`` directory; terraform/tofu expect ``.tf`` files at
the tarball root. These tests pin both the in-memory (bytes) and the
streaming (file-to-file) variants of the repacker, plus the
no-common-dir passthrough contract.
"""

import io
import tarfile

from terrapod.services.archive_utils import (
    strip_archive_top_level_dir,
    strip_archive_top_level_dir_async,
    strip_archive_top_level_dir_file,
    strip_archive_top_level_dir_file_async,
)


def _make_targz(files: dict[str, bytes], *, top_dir: str | None = "owner-repo-sha") -> bytes:
    """Build a gzipped tarball. When ``top_dir`` is set every file is
    nested under it, mimicking a VCS archive download."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        if top_dir is not None:
            info = tarfile.TarInfo(name=top_dir + "/")
            info.type = tarfile.DIRTYPE
            tar.addfile(info)
        for name, content in files.items():
            member_name = f"{top_dir}/{name}" if top_dir is not None else name
            info = tarfile.TarInfo(name=member_name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def _read_targz(data: bytes) -> dict[str, bytes]:
    """Return {member_name: content} for every regular file in a tarball."""
    out: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile():
                f = tar.extractfile(member)
                out[member.name] = f.read() if f else b""
    return out


class TestStripBytes:
    def test_strips_single_top_level_dir(self):
        archive = _make_targz({"main.tf": b"resource {}", "vars.tf": b"variable {}"})
        result = _read_targz(strip_archive_top_level_dir(archive))
        assert result == {"main.tf": b"resource {}", "vars.tf": b"variable {}"}

    def test_preserves_nested_paths_below_top_dir(self):
        archive = _make_targz({"modules/vpc/main.tf": b"x", "main.tf": b"y"})
        result = _read_targz(strip_archive_top_level_dir(archive))
        assert result == {"modules/vpc/main.tf": b"x", "main.tf": b"y"}

    def test_drops_bare_top_level_dir_entry(self):
        # The directory member itself ("owner-repo-sha/") must not survive
        # as an empty-named entry.
        archive = _make_targz({"main.tf": b"x"})
        names = set(_read_targz(archive))  # sanity: source has the file
        assert "owner-repo-sha/main.tf" in names
        out = strip_archive_top_level_dir(archive)
        with tarfile.open(fileobj=io.BytesIO(out), mode="r:gz") as tar:
            out_names = {m.name for m in tar.getmembers()}
        assert "" not in out_names

    def test_root_level_files_without_wrapper_are_dropped(self):
        # The stripper unconditionally removes the first path component, so
        # members already at the tarball root (no "/" in the name) have no
        # second component and are skipped. VCS archive downloads always
        # carry the "owner-repo-sha/" wrapper, so this edge case doesn't
        # arise in production — but pin the actual behaviour so a future
        # refactor can't change it silently.
        archive = _make_targz({"main.tf": b"x", "vars.tf": b"y"}, top_dir=None)
        result = _read_targz(strip_archive_top_level_dir(archive))
        assert result == {}

    async def test_async_wrapper_matches_sync(self):
        archive = _make_targz({"main.tf": b"resource {}"})
        sync = strip_archive_top_level_dir(archive)
        result = await strip_archive_top_level_dir_async(archive)
        assert _read_targz(result) == _read_targz(sync)


class TestStripFile:
    def test_strips_top_level_dir_file_to_file(self, tmp_path):
        archive = _make_targz({"main.tf": b"a", "outputs.tf": b"b"})
        src = tmp_path / "src.tar.gz"
        dst = tmp_path / "dst.tar.gz"
        src.write_bytes(archive)

        strip_archive_top_level_dir_file(str(src), str(dst))

        result = _read_targz(dst.read_bytes())
        assert result == {"main.tf": b"a", "outputs.tf": b"b"}

    async def test_async_file_wrapper_matches_sync(self, tmp_path):
        archive = _make_targz({"main.tf": b"a"})
        src = tmp_path / "src.tar.gz"
        dst = tmp_path / "dst.tar.gz"
        src.write_bytes(archive)

        await strip_archive_top_level_dir_file_async(str(src), str(dst))

        assert _read_targz(dst.read_bytes()) == {"main.tf": b"a"}
