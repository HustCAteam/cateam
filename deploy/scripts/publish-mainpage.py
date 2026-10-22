#!/usr/bin/python3 -I
"""Forced SSH command for atomic, bounded publication of the Hugo homepage."""

import contextlib
import fcntl
import gzip
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import signal
import ssl
import stat
import sys
import tarfile
import tempfile
import time


SITE_ROOT = Path("/srv/hustca")
MAX_UPLOAD = 64 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024
MAX_MEMBERS = 10000
KEEP_RELEASES = 5
TIMEOUT_SECONDS = 300
CHUNK_SIZE = 64 * 1024
REVISION_RE = re.compile(r"[0-9a-f]{40}\Z")
DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
RELEASE_RE = re.compile(r"(0|[1-9][0-9]{0,19})-(0|[1-9][0-9]{0,19})-([0-9a-f]{40})\Z")
COMMAND_RE = re.compile(
    r"publish ([0-9a-f]{40}) ([0-9]{1,20}) ([0-9]{1,20}) ([0-9a-f]{64})\Z"
)
VERIFY_COMMAND_RE = re.compile(
    r"verify ([0-9a-f]{40}) ([0-9]{1,20}) ([0-9]{1,20}) ([0-9a-f]{64}) (\S+)\Z"
)
VERIFY_URL_RE = re.compile(r"https://hustca\.cn(?::(404|443))?/?\Z")
RECEIPT_KEYS = {"revision", "run_id", "run_attempt", "archive_sha256", "index_sha256"}


class PublishError(Exception):
    """A rejected operation that does not advance the published version."""


def sequence(receipt):
    return receipt["run_id"], receipt["run_attempt"]


def release_name(revision, run_id, run_attempt):
    return f"{run_id}-{run_attempt}-{revision}"


def validate_identity(revision, run_id, run_attempt, digest):
    if not isinstance(revision, str) or not REVISION_RE.fullmatch(revision):
        raise PublishError("invalid revision")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise PublishError("invalid content digest")
    for value in (run_id, run_attempt):
        if type(value) is not int or not 0 <= value < 10**20:
            raise PublishError("invalid run identifier")
    if (run_id == 0) != (run_attempt == 0):
        raise PublishError("zero identifiers are reserved for the baseline")


class ExpandedReader:
    """Bound all decompressed bytes, including tar headers and hidden metadata."""

    def __init__(self, source):
        self.source = source
        self.total = 0

    def read(self, size=-1):
        remaining = MAX_EXPANDED - self.total
        size = remaining + 1 if size < 0 else min(size, remaining + 1)
        data = self.source.read(size)
        self.total += len(data)
        if self.total > MAX_EXPANDED:
            raise PublishError("expanded archive exceeds limit")
        return data


class TimedInput:
    """Limit total SSH upload time without interrupting the atomic commit."""

    def __init__(self, source):
        self.source = source
        self.deadline = time.monotonic() + TIMEOUT_SECONDS

    def read(self, size):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise PublishError("publication timed out")
        signal.setitimer(signal.ITIMER_REAL, remaining)
        try:
            return self.source.read(size)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)


class Publisher:
    """The root is configurable only through this Python API, never over SSH."""

    def __init__(self, root=SITE_ROOT):
        self.root = Path(root)
        self.releases = self.root / "releases"
        self.receipts = self.root / "receipts"
        self.current = self.root / "current"

    @contextlib.contextmanager
    def locked(self):
        for directory, mode in ((self.root, 0o755), (self.releases, 0o755), (self.receipts, 0o700)):
            try:
                directory.mkdir(mode=mode)
            except FileExistsError:
                pass
            else:
                directory.chmod(mode)
            if directory.is_symlink() or not directory.is_dir():
                raise PublishError("unsafe publication directory")
        fd = os.open(self.root / ".publish.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+") as lock:
            if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
                raise PublishError("unsafe publication lock")
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def _receipt(self, name):
        path = self.receipts / f"{name}.json"
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
            raise PublishError("missing or unsafe publication receipt")
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(receipt, dict) or receipt.keys() != RECEIPT_KEYS:
                raise PublishError("invalid publication receipt")
            validate_identity(receipt["revision"], receipt["run_id"], receipt["run_attempt"], receipt["archive_sha256"])
            if not isinstance(receipt["index_sha256"], str) or not DIGEST_RE.fullmatch(receipt["index_sha256"]):
                raise PublishError("invalid index digest")
            if release_name(receipt["revision"], *sequence(receipt)) != name:
                raise PublishError("receipt does not match release")
            return receipt
        except (ValueError, UnicodeError) as error:
            raise PublishError("invalid publication receipt") from error

    def _status(self):
        if not os.path.lexists(self.current):
            return None
        if not self.current.is_symlink():
            raise PublishError("current must be a managed symlink")
        target = os.readlink(self.current)
        prefix = "releases/"
        if not target.startswith(prefix) or not RELEASE_RE.fullmatch(target[len(prefix):]):
            raise PublishError("current points outside managed releases")
        name = target[len(prefix):]
        release = self.releases / name
        if release.is_symlink() or not release.is_dir():
            raise PublishError("current release is missing or unsafe")
        return self._receipt(name)

    def status(self):
        with self.locked():
            return self._status()

    def verify(self, revision, run_id, run_attempt, index_sha256, url):
        validate_identity(revision, run_id, run_attempt, index_sha256)
        target = VERIFY_URL_RE.fullmatch(url) if isinstance(url, str) else None
        if target is None:
            raise PublishError("verification is limited to the homepage HTTPS origin")
        with self.locked():
            receipt = self._status()
            if receipt is None or (
                receipt["revision"] != revision
                or sequence(receipt) != (run_id, run_attempt)
                or receipt["index_sha256"] != index_sha256
            ):
                raise PublishError("requested verification does not match the current release")
            connection = http.client.HTTPSConnection(
                "hustca.cn", int(target.group(1) or 443), timeout=30,
                context=ssl.create_default_context(),
            )
            try:
                connection.request("GET", "/", headers={
                    "Cache-Control": "no-cache", "Accept-Encoding": "identity",
                })
                with connection.getresponse() as response:
                    if response.status != 200:
                        raise PublishError(f"homepage returned HTTP {response.status}")
                    digest = hashlib.sha256()
                    total = 0
                    for chunk in iter(lambda: response.read(CHUNK_SIZE), b""):
                        total += len(chunk)
                        if total > MAX_EXPANDED:
                            raise PublishError("homepage response exceeds limit")
                        digest.update(chunk)
                    if digest.hexdigest() != index_sha256:
                        raise PublishError("live HTTPS homepage does not match the build")
            finally:
                connection.close()
            return dict(receipt, verified_url=url, http_status=200)

    def _upload(self, source, destination, expected_digest):
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = source.read(min(CHUNK_SIZE, MAX_UPLOAD - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD:
                raise PublishError("compressed archive exceeds limit")
            digest.update(chunk)
            destination.write(chunk)
        if digest.hexdigest() != expected_digest:
            raise PublishError("archive digest mismatch")
        destination.seek(0)

    def _extract(self, archive, staging):
        seen = set()
        count = 0
        file_bytes = 0
        with gzip.GzipFile(fileobj=archive, mode="rb") as compressed:
            expanded = ExpandedReader(compressed)
            with tarfile.open(fileobj=expanded, mode="r|") as bundle:
                for member in bundle:
                    count += 1
                    if count > MAX_MEMBERS:
                        raise PublishError("archive member count exceeds limit")
                    if not (member.isfile() or member.isdir()):
                        raise PublishError("archive may contain only regular files and directories")
                    # Sparse files are special even when tarfile classifies them as regular.
                    if member.sparse is not None or any(key.startswith("GNU.sparse") for key in member.pax_headers):
                        raise PublishError("sparse archive members are forbidden")
                    raw = member.name
                    if not raw or raw.startswith("/") or "\\" in raw or "\x00" in raw or ".." in raw.split("/"):
                        raise PublishError("unsafe archive path")
                    relative = PurePosixPath(raw)
                    normalized = relative.as_posix()
                    if normalized in seen:
                        raise PublishError("duplicate archive path")
                    seen.add(normalized)
                    if normalized == ".":
                        if not member.isdir():
                            raise PublishError("archive root must be a directory")
                        continue
                    destination = staging.joinpath(*relative.parts)
                    if member.isdir():
                        destination.mkdir(mode=0o755, parents=True, exist_ok=True)
                        destination.chmod(0o755)
                        continue
                    if member.size < 0:
                        raise PublishError("invalid archive member size")
                    file_bytes += member.size
                    if file_bytes > MAX_EXPANDED:
                        raise PublishError("expanded files exceed limit")
                    destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                    with bundle.extractfile(member) as source, destination.open("xb") as target:
                        shutil.copyfileobj(source, target, CHUNK_SIZE)
                    destination.chmod(0o644)
            # Tar parsing stops at end markers. Still validate gzip's trailer and
            # bound trailing decompressed data, including concatenated gzip streams.
            while expanded.read(CHUNK_SIZE):
                pass
        for name in ("index.html", "404.html"):
            required = staging / name
            if not required.is_file() or required.stat().st_size == 0:
                raise PublishError(f"archive requires nonempty {name}")
        digest = hashlib.sha256()
        with (staging / "index.html").open("rb") as homepage:
            for chunk in iter(lambda: homepage.read(CHUNK_SIZE), b""):
                digest.update(chunk)
        # mkdir(parents=True) uses the process umask for intermediate parents.
        # Set every served directory explicitly, without trusting archive modes.
        for directory, _, _ in os.walk(staging):
            Path(directory).chmod(0o755)
        return digest.hexdigest()

    def _retain(self, current_name):
        managed = []
        for path in self.releases.iterdir():
            if not RELEASE_RE.fullmatch(path.name) or path.is_symlink() or not path.is_dir():
                continue
            try:
                receipt = self._receipt(path.name)
            except (PublishError, OSError):
                continue
            managed.append((sequence(receipt), path))
        managed.sort(key=lambda item: (item[0], item[1].name), reverse=True)
        keep = {current_name}
        for _, path in managed:
            if len(keep) >= KEEP_RELEASES:
                break
            keep.add(path.name)
        for _, path in managed:
            if path.name not in keep:
                shutil.rmtree(path)
        # Receipts are intentionally retained to preserve immutable release IDs.

    def publish(self, revision, run_id, run_attempt, archive_sha256, source):
        validate_identity(revision, run_id, run_attempt, archive_sha256)
        name = release_name(revision, run_id, run_attempt)
        with self.locked():
            current = self._status()
            if current is not None:
                if (run_id, run_attempt) < sequence(current):
                    raise PublishError("stale publication sequence")
                if (run_id, run_attempt) == sequence(current) and revision != current["revision"]:
                    raise PublishError("publication sequence already belongs to another revision")
            elif (run_id, run_attempt) == (0, 0) and any(self.receipts.iterdir()):
                raise PublishError("baseline is only allowed before the first publication")
            release = self.releases / name
            receipt_path = self.receipts / f"{name}.json"
            with tempfile.TemporaryFile(dir=self.root) as archive:
                self._upload(source, archive, archive_sha256)
                if os.path.lexists(receipt_path):
                    previous = self._receipt(name)
                    if previous["archive_sha256"] != archive_sha256:
                        raise PublishError("immutable release has conflicting bytes")
                    if current == previous:
                        return previous
                    raise PublishError("release already exists but is not current; operator recovery required")
                if os.path.lexists(release):
                    raise PublishError("release path already exists")
                staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=self.releases))
                receipt_temp = self.receipts / f".receipt-{secrets.token_hex(16)}"
                link_temp = self.root / f".current-{secrets.token_hex(16)}"
                installed_release = False
                installed_receipt = False
                committed = False
                try:
                    index_sha256 = self._extract(archive, staging)
                    receipt = dict(revision=revision, run_id=run_id, run_attempt=run_attempt,
                                   archive_sha256=archive_sha256, index_sha256=index_sha256)
                    with receipt_temp.open("x", encoding="utf-8") as output:
                        json.dump(receipt, output, sort_keys=True)
                        output.write("\n")
                    receipt_temp.chmod(0o600)
                    os.rename(staging, release)
                    installed_release = True
                    os.replace(receipt_temp, receipt_path)
                    installed_receipt = True
                    link_temp.symlink_to(f"releases/{name}")
                    os.replace(link_temp, self.current)
                    committed = True
                finally:
                    link_temp.unlink(missing_ok=True)
                    receipt_temp.unlink(missing_ok=True)
                    if staging.exists():
                        shutil.rmtree(staging)
                    if not committed:
                        if installed_receipt:
                            receipt_path.unlink(missing_ok=True)
                        if installed_release:
                            shutil.rmtree(release)
                # Commit is the point of no return. A maintenance failure must not
                # report an unsuccessful publication after current has changed.
                try:
                    self._retain(name)
                except OSError as error:
                    print(f"release retention warning: {error}", file=sys.stderr)
                return receipt


def _timeout(signum, frame):
    raise PublishError("publication timed out")


def main():
    os.umask(0o077)
    command = os.environ.get("SSH_ORIGINAL_COMMAND", "")
    try:
        if len(sys.argv) != 1:
            raise PublishError("command-line arguments are forbidden")
        match = COMMAND_RE.fullmatch(command)
        verification = VERIFY_COMMAND_RE.fullmatch(command)
        if command != "status" and match is None and verification is None:
            raise PublishError("unsupported SSH command")
        signal.signal(signal.SIGALRM, _timeout)
        publisher = Publisher()
        if command == "status":
            result = publisher.status()
        elif verification is not None:
            revision, run_id, run_attempt, digest, url = verification.groups()
            signal.setitimer(signal.ITIMER_REAL, TIMEOUT_SECONDS)
            try:
                result = publisher.verify(revision, int(run_id), int(run_attempt), digest, url)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
        else:
            revision, run_id, run_attempt, digest = match.groups()
            result = publisher.publish(revision, int(run_id), int(run_attempt), digest, TimedInput(sys.stdin.buffer))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (PublishError, OSError, EOFError, tarfile.TarError, http.client.HTTPException, ValueError) as error:
        print(f"command failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
