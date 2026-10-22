"""Behavioral tests for the production forced-command publisher (stdlib only)."""

import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish-mainpage.py"
SPEC = importlib.util.spec_from_file_location("publish_mainpage", SCRIPT)
publisher_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher_module)
REVISION = "a" * 40
OTHER_REVISION = "b" * 40


def digest(data):
    return hashlib.sha256(data).hexdigest()


def entry(name, content=b"content", kind=tarfile.REGTYPE, linkname="", mode=0o7777):
    member = tarfile.TarInfo(name)
    member.type = kind
    member.linkname = linkname
    member.mode = mode
    member.uid = 12345
    member.gid = 12345
    member.size = len(content) if kind == tarfile.REGTYPE else 0
    return member, content


def make_archive(extra=(), homepage=b"<html>homepage</html>", include_index=True, include_404=True):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz", format=tarfile.PAX_FORMAT) as bundle:
        members = []
        if include_index:
            members.append(entry("./index.html", homepage))
        if include_404:
            members.append(entry("./404.html", b"not found"))
        members.extend(extra)
        for member, content in members:
            bundle.addfile(member, io.BytesIO(content) if member.isfile() else None)
    return output.getvalue()


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "site"
        self.publisher = publisher_module.Publisher(self.root)
        self.baseline_archive = make_archive()
        self.baseline = self.publish(self.baseline_archive, run_id=10)

    def publish(self, archive=None, run_id=11, run_attempt=1, revision=REVISION, checksum=None, source=None):
        if archive is None:
            archive = make_archive(homepage=f"run {run_id}/{run_attempt}".encode())
        return self.publisher.publish(
            revision, run_id, run_attempt, checksum or digest(archive),
            source if source is not None else io.BytesIO(archive),
        )

    def assert_preserved(self, expected=None):
        expected = expected or self.baseline
        self.assertEqual(self.publisher.status(), expected)
        name = publisher_module.release_name(expected["revision"], expected["run_id"], expected["run_attempt"])
        self.assertEqual(os.readlink(self.root / "current"), f"releases/{name}")
        self.assertEqual(digest((self.root / "current" / "index.html").read_bytes()), expected["index_sha256"])
        self.assertEqual(list(self.root.glob(".current-*")), [])
        self.assertEqual(list((self.root / "releases").glob(".staging-*")), [])
        self.assertEqual(list((self.root / "receipts").glob(".receipt-*")), [])
        self.assertEqual({p.name for p in self.root.iterdir()}, {"current", "releases", "receipts", ".publish.lock"})

    def assert_rejected(self, archive, **kwargs):
        with self.assertRaises((publisher_module.PublishError, OSError, EOFError, tarfile.TarError, ValueError)):
            self.publish(archive, **kwargs)
        self.assert_preserved()
        self.assertEqual(len(list((self.root / "releases").iterdir())), 1)
        self.assertEqual(len(list((self.root / "receipts").iterdir())), 1)

    def test_success_uses_relative_atomic_link_and_external_receipt(self):
        archive = make_archive([
            entry("./", kind=tarfile.DIRTYPE),
            entry("./assets/images/logo.svg", b"image"),
            entry("./assets/", kind=tarfile.DIRTYPE),
        ], homepage=b"new homepage")
        receipt = self.publish(archive)
        self.assert_preserved(receipt)
        self.assertEqual(receipt, {
            "revision": REVISION, "run_id": 11, "run_attempt": 1,
            "archive_sha256": digest(archive), "index_sha256": digest(b"new homepage"),
        })
        release = (self.root / "current").resolve()
        self.assertEqual((release / "assets/images/logo.svg").read_bytes(), b"image")
        self.assertFalse((release / "receipts").exists())
        name = release.name
        self.assertEqual(json.loads((self.root / "receipts" / f"{name}.json").read_text()), receipt)
        self.assertEqual(stat.S_IMODE((self.root / "receipts" / f"{name}.json").stat().st_mode), 0o600)

    def test_preserves_long_unicode_asset_paths(self):
        asset = "media/" + "计协活动照片" * 8 + ".webp"
        self.publish(make_archive([entry(asset, b"image bytes")]))
        self.assertEqual((self.root / "current" / asset).read_bytes(), b"image bytes")

    def test_safe_modes_under_restrictive_umask_and_private_staging(self):
        previous = os.umask(0o077)
        try:
            archive = make_archive([entry("deep/nested/file.txt", b"hello")])
            original = self.publisher._extract

            def inspect_staging(source, staging):
                self.assertEqual(stat.S_IMODE(staging.stat().st_mode), 0o700)
                return original(source, staging)

            with mock.patch.object(self.publisher, "_extract", side_effect=inspect_staging):
                self.publish(archive)
            release = (self.root / "current").resolve()
            for path in [release, *release.rglob("*")]:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755 if path.is_dir() else 0o644)
            fresh_root = Path(self.temporary.name) / "fresh"
            fresh = publisher_module.Publisher(fresh_root)
            fresh.publish(REVISION, 1, 1, digest(archive), io.BytesIO(archive))
            self.assertEqual(stat.S_IMODE(fresh_root.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((fresh_root / "releases").stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((fresh_root / "receipts").stat().st_mode), 0o700)
        finally:
            os.umask(previous)

    def test_rejects_unsafe_members_without_touching_current(self):
        cases = {
            "parent traversal": entry("../escape"),
            "nested traversal": entry("assets/../../escape"),
            "absolute path": entry("/tmp/escape"),
            "backslash": entry("assets\\escape"),
            "symlink": entry("linked", kind=tarfile.SYMTYPE, linkname="../../escape"),
            "hardlink": entry("linked", kind=tarfile.LNKTYPE, linkname="index.html"),
            "fifo": entry("pipe", kind=tarfile.FIFOTYPE),
            "character device": entry("device", kind=tarfile.CHRTYPE),
            "block device": entry("device", kind=tarfile.BLKTYPE),
            "duplicate file": entry("index.html", b"replacement"),
            "normalized duplicate": entry("././index.html", b"replacement"),
            "file as ancestor": entry("index.html/nested", b"nested"),
            "file as directory": entry("index.html", kind=tarfile.DIRTYPE),
            "regular root": entry("./", b"root"),
        }
        for label, member in cases.items():
            with self.subTest(label=label):
                self.assert_rejected(make_archive([member]))
        self.assertFalse((self.root.parent / "escape").exists())

    def test_rejects_duplicate_directories(self):
        self.assert_rejected(make_archive([
            entry("./assets", kind=tarfile.DIRTYPE),
            entry("assets/", kind=tarfile.DIRTYPE),
        ]))

    def test_rejects_sparse_files(self):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz", format=tarfile.PAX_FORMAT) as bundle:
            for name in ("index.html", "404.html"):
                member, content = entry(name)
                bundle.addfile(member, io.BytesIO(content))
            member, content = entry("sparse")
            member.pax_headers = {"GNU.sparse.name": "sparse"}
            bundle.addfile(member, io.BytesIO(content))
        self.assert_rejected(output.getvalue())

    def test_requires_both_nonempty_pages(self):
        for archive in (
            make_archive(include_index=False),
            make_archive(include_404=False),
            make_archive(homepage=b""),
            make_archive([entry("404.html", b"")], include_404=False),
            make_archive([entry("index.html", kind=tarfile.DIRTYPE)], include_index=False),
        ):
            with self.subTest(archive_digest=digest(archive)):
                self.assert_rejected(archive)

    def test_bad_checksum_and_corrupt_archives_preserve_current(self):
        self.assert_rejected(make_archive(), checksum="0" * 64)
        for archive in (b"not gzip", self.baseline_archive[:-8], gzip.compress(b"not tar")):
            with self.subTest(archive=archive[:16]):
                self.assert_rejected(archive)

    def test_bounds_compressed_expanded_and_member_count(self):
        archive = make_archive()
        with mock.patch.object(publisher_module, "MAX_UPLOAD", len(archive) - 1):
            self.assert_rejected(archive)
        with mock.patch.object(publisher_module, "MAX_EXPANDED", 20480):
            self.assert_rejected(make_archive(homepage=b"x" * 32768))
            self.assert_rejected(archive + gzip.compress(b"x" * 32768))
        with mock.patch.object(publisher_module, "MAX_MEMBERS", 2):
            self.assert_rejected(make_archive([entry("extra", b"extra")]))

    def test_failed_extraction_cleans_staging(self):
        with mock.patch.object(publisher_module.shutil, "copyfileobj", side_effect=OSError("disk full")):
            self.assert_rejected(make_archive())

    def test_failed_receipt_or_symlink_install_preserves_current(self):
        replace = os.replace
        for fail_at in ("receipt", "current"):
            def fail_replace(source, destination):
                target = Path(destination)
                if (fail_at == "current" and target == self.root / "current") or (
                    fail_at == "receipt" and target.parent == self.root / "receipts"
                ):
                    raise OSError("injected installation failure")
                return replace(source, destination)

            with self.subTest(fail_at=fail_at), mock.patch.object(publisher_module.os, "replace", side_effect=fail_replace):
                self.assert_rejected(make_archive())

    def test_timeout_cleans_upload_and_preserves_current(self):
        source = mock.Mock()
        source.read.side_effect = publisher_module.PublishError("publication timed out")
        self.assert_rejected(make_archive(), source=source)
        with mock.patch.object(publisher_module.time, "monotonic", side_effect=[0, 301]):
            source = publisher_module.TimedInput(io.BytesIO(self.baseline_archive))
            self.assert_rejected(self.baseline_archive, source=source)

    def test_idempotent_publication_never_reextracts_or_repoints(self):
        before = (self.root / "current").lstat()
        with mock.patch.object(self.publisher, "_extract", side_effect=AssertionError("must not extract again")):
            result = self.publish(self.baseline_archive, run_id=10)
        self.assertEqual(result, self.baseline)
        self.assertEqual((self.root / "current").lstat().st_ino, before.st_ino)
        self.assert_preserved()
        self.assert_rejected(make_archive(homepage=b"different bytes"), run_id=10)

    def test_orders_numeric_run_and_attempt_and_rejects_stale_replays(self):
        self.assert_rejected(make_archive(), run_id=9, run_attempt=999)
        self.assert_rejected(make_archive(), run_id=10, revision=OTHER_REVISION)
        second_attempt = self.publish(run_id=10, run_attempt=2)
        with self.assertRaises(publisher_module.PublishError):
            self.publish(self.baseline_archive, run_id=10)
        self.assert_preserved(second_attempt)
        newer = self.publish(run_id=11, run_attempt=1)
        with self.assertRaises(publisher_module.PublishError):
            self.publish(run_id=10, run_attempt=999)
        self.assert_preserved(newer)

    def test_baseline_bootstrap_is_initial_only(self):
        fresh = publisher_module.Publisher(Path(self.temporary.name) / "bootstrap")
        self.assertIsNone(fresh.status())
        initial = fresh.publish(REVISION, 0, 0, digest(self.baseline_archive), io.BytesIO(self.baseline_archive))
        self.assertEqual(fresh.status(), initial)
        self.assertEqual(fresh.publish(REVISION, 0, 0, digest(self.baseline_archive), io.BytesIO(self.baseline_archive)), initial)
        self.assert_rejected(make_archive(), run_id=0, run_attempt=0)
        for run_id, run_attempt in ((0, 1), (1, 0), (-1, 1), (10**20, 1), (True, 1)):
            with self.subTest(run_id=run_id, run_attempt=run_attempt):
                self.assert_rejected(make_archive(), run_id=run_id, run_attempt=run_attempt)

    def test_retains_five_releases_and_all_receipts_without_removing_unrelated_paths(self):
        releases = self.root / "releases"
        unrelated = releases / "operator-backup"
        unrelated.mkdir()
        (unrelated / "important").write_text("preserve")
        unreceipted = releases / f"1-1-{'c' * 40}"
        unreceipted.mkdir()
        unsafe_link = releases / f"2-1-{'d' * 40}"
        unsafe_link.symlink_to(unrelated)
        for run_id in range(11, 18):
            newest = self.publish(run_id=run_id)
        expected = {f"{run_id}-1-{REVISION}" for run_id in range(13, 18)}
        self.assertEqual({path.name for path in releases.iterdir()} - {unrelated.name, unreceipted.name, unsafe_link.name}, expected)
        self.assertEqual(len(list((self.root / "receipts").glob("*.json"))), 8)
        self.assertEqual((unrelated / "important").read_text(), "preserve")
        self.assertTrue(unreceipted.is_dir())
        self.assertTrue(unsafe_link.is_symlink())
        self.assert_preserved(newest)

    def test_retention_failure_does_not_report_committed_publish_as_rejected(self):
        with mock.patch.object(self.publisher, "_retain", side_effect=OSError("maintenance failed")), contextlib.redirect_stderr(io.StringIO()):
            receipt = self.publish()
        self.assert_preserved(receipt)

    def test_refuses_unmanaged_current_and_existing_release(self):
        occupied = self.root / "releases" / f"11-1-{REVISION}"
        occupied.mkdir()
        with self.assertRaises(publisher_module.PublishError):
            self.publish()
        self.assert_preserved()
        (self.root / "current").unlink()
        (self.root / "current").symlink_to("../outside")
        with self.assertRaises(publisher_module.PublishError):
            self.publish()
        self.assertEqual(os.readlink(self.root / "current"), "../outside")

    def invoke(self, command, archive=b"", args=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        old_umask = os.umask(0o077)
        try:
            with mock.patch.dict(os.environ, {"SSH_ORIGINAL_COMMAND": command}), \
                    mock.patch.object(publisher_module.sys, "argv", args or [str(SCRIPT)]), \
                    mock.patch.object(publisher_module.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(archive))), \
                    mock.patch.object(publisher_module, "Publisher", return_value=self.publisher), \
                    mock.patch.object(publisher_module.signal, "signal"), \
                    mock.patch.object(publisher_module.signal, "setitimer"), \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = publisher_module.main()
        finally:
            os.umask(old_umask)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_forced_command_publishes_and_reports_json_status(self):
        archive = make_archive(homepage=b"via SSH")
        code, output, error = self.invoke(f"publish {OTHER_REVISION} 11 1 {digest(archive)}", archive)
        self.assertEqual((code, error), (0, ""))
        receipt = json.loads(output)
        self.assert_preserved(receipt)
        code, output, error = self.invoke("status")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output), receipt)

    @contextlib.contextmanager
    def https_response(self, body=b"<html>homepage</html>", status=200):
        response = mock.MagicMock()
        response.status = status
        response.read.side_effect = io.BytesIO(body).read
        response.__enter__.return_value = response
        connection = mock.Mock()
        connection.getresponse.return_value = response
        with mock.patch.object(publisher_module.http.client, "HTTPSConnection", return_value=connection):
            yield connection

    def verify_baseline(self, url="https://hustca.cn:404/", **changes):
        arguments = dict(revision=REVISION, run_id=10, run_attempt=1,
                         index_sha256=self.baseline["index_sha256"], url=url)
        arguments.update(changes)
        return self.publisher.verify(**arguments)

    def test_verification_checks_live_response_and_expected_release(self):
        with self.https_response():
            command = f"verify {REVISION} 10 1 {self.baseline['index_sha256']} https://hustca.cn:404/"
            code, output, error = self.invoke(command)
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output), dict(self.baseline, verified_url="https://hustca.cn:404/", http_status=200))
        for body, status in ((b"old or substituted homepage", 200), (b"", 302), (b"unavailable", 503)):
            with self.subTest(status=status), self.https_response(body, status):
                with self.assertRaises(publisher_module.PublishError):
                    self.verify_baseline()
                self.assert_preserved()

    def test_verification_refuses_other_origins_and_stale_identity_before_network(self):
        urls = ("http://hustca.cn/", "https://example.org/", "https://127.0.0.1/",
                "https://hustca.cn:22/", "https://hustca.cn/other", "https://hustca.cn/?q=x",
                "https://hustca.cn/#fragment", "https://hustca.cn@127.0.0.1/")
        with mock.patch.object(publisher_module.http.client, "HTTPSConnection",
                               side_effect=AssertionError("forbidden network access")):
            for url in urls:
                with self.subTest(url=url), self.assertRaises(publisher_module.PublishError):
                    self.verify_baseline(url)
            for change in (dict(revision=OTHER_REVISION), dict(run_id=9), dict(run_attempt=2),
                           dict(index_sha256="0" * 64)):
                with self.subTest(change=change), self.assertRaises(publisher_module.PublishError):
                    self.verify_baseline(**change)
        self.assert_preserved()

    def test_verification_does_not_ignore_tls_errors_or_unbounded_responses(self):
        with self.https_response() as connection:
            connection.request.side_effect = publisher_module.ssl.SSLCertVerificationError("untrusted certificate")
            with self.assertRaises(publisher_module.ssl.SSLCertVerificationError):
                self.verify_baseline()
        with self.https_response(), mock.patch.object(publisher_module, "MAX_EXPANDED", 4):
            with self.assertRaises(publisher_module.PublishError):
                self.verify_baseline()
        self.assert_preserved()

    def test_forced_command_rejects_shell_and_extra_arguments(self):
        valid = f"publish {REVISION} 11 1 {digest(self.baseline_archive)}"
        for command in ("", "sh", "status; id", "status extra", valid + " extra", valid + "\nstatus",
                        valid.replace(" 11 ", " -1 "), valid.replace(" 11 ", " 100000000000000000000 "),
                        valid.replace(REVISION, REVISION.upper())):
            with self.subTest(command=command):
                code, output, error = self.invoke(command, self.baseline_archive)
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assert_preserved()
        code, _, _ = self.invoke("status", args=[str(SCRIPT), "--root=/tmp/attacker"])
        self.assertEqual(code, 1)
        self.assert_preserved()


if __name__ == "__main__":
    unittest.main()
