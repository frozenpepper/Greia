#!/usr/bin/env python3
"""In-place source deploy of a frozen ``HEAD`` to an installed developer device.

This is the reusable form of the procedure in ``docs/agents/GREIA_AGENT_OPERATIONS.md``
section 8 ("Developer Acer: in-place source deploy (no installer)"). It needs the
operator's own SSH key/agent and a ``known_hosts`` entry (``BatchMode=yes``: no
password is ever prompted for or handled) and ``sudo -n`` provisioned on the
device. It never touches ``sshd``, sudoers or ``authorized_keys``, and no host,
address or credential is stored in the repository: the target comes from
``--target user@host`` or the ``GREIA_DEV_TARGET`` environment variable.

Usage::

    python3 tools/dev_source_deploy.py stage  [--output FILE]
    python3 tools/dev_source_deploy.py push   --target OPERATOR@DEVICE
    python3 tools/dev_source_deploy.py swap   --target OPERATOR@DEVICE
    python3 tools/dev_source_deploy.py deploy --target OPERATOR@DEVICE   # push + swap
    python3 tools/dev_source_deploy.py status --target OPERATOR@DEVICE
    python3 tools/dev_source_deploy.py cleanup --target OPERATOR@DEVICE

``stage`` builds the bundle from ``git archive HEAD`` (never the worktree;
uncommitted changes are not deployed), keeps exactly the content the image
composer installs (``build/lib/compose.sh``: ``compose_install_target_content``
and ``compose_install_runtime_assets``), regenerates the built-in Activity index
with ``tools/build_activity_index.py``, writes ``.deployed-sha`` and packs a
``.tar.gz`` without AppleDouble/xattr/owner noise. ``push`` streams that bundle
over ssh into ``/var/lib/greia/deploy/new`` (the device's ``/var/tmp`` is a small
tmpfs) and runs the Python parse gate with the device interpreter; the live tree
is untouched. ``swap`` stops the services, keeps exactly one backup in
``/var/lib/greia/deploy/prev``, installs the new tree and index root-owned and
read-only, installs changed units, rebuilds the bytecode prefix with
``tools/precompile_greia_bytecode.py`` on the device, restarts the services and
prints health. Delete the backup with ``cleanup`` only after verification.

Remote commands are fixed argument arrays or fixed scripts whose values are
quoted with :mod:`shlex`; nothing from the command line except the validated
target reaches a remote shell.
"""

from __future__ import annotations

import argparse
import gzip
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Protocol, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_ENV = "GREIA_DEV_TARGET"
SERVICES = ("greia-launcher", "greia-parent")
JUNK_NAMES = frozenset({".DS_Store", "__pycache__"})
RUNTIME_ASSET_DIRS = frozenset({"audio", "boot", "fonts", "icons", "scenes"})
# Repository paths git archive is asked for; the filter below decides what stays.
ARCHIVE_PATHSPECS = (
    "src",
    "runtime",
    "activities",
    "assets",
    "tools/precompile_greia_bytecode.py",
    "tools/build_activity_index.py",
    *(f"build/overlay/etc/systemd/system/{unit}.service" for unit in SERVICES),
)
_TARGET_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9._:\[\]-]*$")

PARSE_GATE_CODE = """\
import os, sys
if sys.version_info < (3, 11):
    sys.exit("device Python is older than 3.11: %s" % (sys.version,))
count = 0
for root, dirs, files in os.walk(sys.argv[1]):
    dirs.sort()
    for name in sorted(files):
        if not name.endswith(".py"):
            continue
        path = os.path.join(root, name)
        with open(path, "rb") as handle:
            data = handle.read()
        try:
            compile(data, path, "exec", dont_inherit=True)
        except (SyntaxError, ValueError) as exc:
            sys.exit("PARSE GATE FAILED: %s: %s" % (path, exc))
        count += 1
print("parse gate ok: %d files, python %d.%d" % (count, *sys.version_info[:2]))
"""


class DeployError(RuntimeError):
    """A deploy step failed; the message is safe to show to the operator."""


# ---------------------------------------------------------------------------
# Bundle content filter (mirrors build/lib/compose.sh)
# ---------------------------------------------------------------------------


def _is_junk(parts: Sequence[str]) -> bool:
    return any(
        part in JUNK_NAMES or part.startswith("._") or part.endswith((".pyc", ".pyo"))
        for part in parts
    )


def _runtime_asset(parts: Sequence[str]) -> bool:
    """Mirror of ``compose_install_runtime_assets`` rsync include/exclude rules."""
    if not parts:
        return False
    if "source" in parts[:-1] or any("contact_sheet" in part for part in parts):
        return False
    head = parts[0]
    if head in RUNTIME_ASSET_DIRS:
        return True
    if head == "catalog":
        return len(parts) == 2 and parts[1].endswith(".toml")
    return len(parts) >= 2 and head == "visual" and parts[1] == "runtime"


def bundle_destination(archive_path: str) -> PurePosixPath | None:
    """Map a ``git archive`` path to its place in the staging tree, or None to drop it.

    The staging tree has ``bundle/`` (what is packed and deployed) and ``host/``
    (host-only helpers needed to build the bundle, never packed).
    """
    path = PurePosixPath(archive_path)
    parts = path.parts
    if path.is_absolute() or ".." in parts or not parts or _is_junk(parts):
        return None
    top = parts[0]
    if top in ("src", "runtime", "activities"):
        return PurePosixPath("bundle/opt/greia-os") / path
    if top == "assets":
        if not _runtime_asset(parts[1:]):
            return None
        return PurePosixPath("bundle/opt/greia-os") / path
    if archive_path == "tools/precompile_greia_bytecode.py":
        return PurePosixPath("bundle") / path
    if archive_path == "tools/build_activity_index.py":
        return PurePosixPath("host") / path
    for unit in SERVICES:
        if archive_path == f"build/overlay/etc/systemd/system/{unit}.service":
            return PurePosixPath(f"bundle/units/{unit}.service")
    return None


# ---------------------------------------------------------------------------
# Staging
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise DeployError(f"git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _tar_filter(commit_time: int) -> Callable[[tarfile.TarInfo], tarfile.TarInfo | None]:
    def apply(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        if _is_junk(PurePosixPath(info.name).parts):
            return None
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = commit_time
        info.pax_headers = {}
        if info.isdir():
            info.mode = 0o755
        else:
            info.mode = 0o755 if info.mode & 0o100 else 0o644
        return info
    return apply


class BundleStager:
    """Builds the deploy tarball for the current ``HEAD`` of a repository."""

    def __init__(self, repo: Path = PROJECT_ROOT, python: str = sys.executable) -> None:
        self._repo = repo
        self._python = python

    def head_sha(self) -> str:
        return _git(self._repo, "rev-parse", "HEAD")

    def dirty(self) -> bool:
        return bool(_git(self._repo, "status", "--porcelain", "--untracked-files=no"))

    def stage(self, output: Path, work_dir: Path) -> str:
        """Write the bundle tarball to ``output`` using ``work_dir`` for scratch.

        Returns the deployed SHA. The caller owns ``work_dir`` cleanup.
        """
        sha = self.head_sha()
        commit_time = int(_git(self._repo, "show", "-s", "--format=%ct", "HEAD"))
        tree = work_dir / "tree"
        self._extract_filtered(tree)
        live = tree / "bundle" / "opt" / "greia-os"
        for required in ("src", "runtime", "activities"):
            if not (live / required).is_dir():
                raise DeployError(f"git archive HEAD has no {required}/ tree")
        self._build_index(tree)
        (live / ".deployed-sha").write_text(sha + "\n", encoding="ascii")
        self._pack(tree / "bundle", output, commit_time)
        return sha

    def _extract_filtered(self, tree: Path) -> None:
        proc = subprocess.Popen(
            ["git", "-C", str(self._repo), "archive", "--format=tar", "HEAD", "--", *ARCHIVE_PATHSPECS],
            stdout=subprocess.PIPE,
        )
        assert proc.stdout is not None
        try:
            with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
                for member in archive:
                    destination = bundle_destination(member.name) if member.isfile() else None
                    if member.issym() or member.islnk():
                        if bundle_destination(member.name) is not None:
                            raise DeployError(f"refusing link in deploy content: {member.name}")
                        continue
                    if destination is None:
                        continue
                    target = tree / destination
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source is None:
                        continue
                    with source, open(target, "wb") as handle:
                        shutil.copyfileobj(source, handle, 1 << 20)
                    target.chmod(0o755 if member.mode & 0o100 else 0o644)
        finally:
            proc.stdout.close()
            if proc.wait() != 0:
                raise DeployError("git archive HEAD failed")

    def _build_index(self, tree: Path) -> None:
        live = tree / "bundle" / "opt" / "greia-os"
        index = tree / "bundle" / "usr" / "share" / "greia" / "activity-index-v1.json"
        index.parent.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, PYTHONPATH=str(live / "src"), PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(
            [
                self._python, "-B", str(tree / "host" / "tools" / "build_activity_index.py"),
                "--activities", str(live / "activities"),
                "--runtime", str(live / "runtime" / "child-runtime.toml"),
                "--output", str(index),
            ],
            check=False, capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            raise DeployError("built-in Activity index generation failed:\n" + result.stderr.strip())

    @staticmethod
    def _pack(bundle: Path, output: Path, commit_time: int) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.with_name(output.name + ".part")
        apply = _tar_filter(commit_time)
        try:
            with open(staging, "wb") as raw, gzip.GzipFile(
                fileobj=raw, mode="wb", compresslevel=6, mtime=commit_time, filename=""
            ) as gz, tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as tar:
                for path in sorted(bundle.rglob("*")):
                    if path.is_symlink():
                        raise DeployError(f"refusing symlink in bundle: {path}")
                    tar.add(path, arcname=path.relative_to(bundle).as_posix(),
                            recursive=False, filter=apply)
            os.replace(staging, output)
        finally:
            staging.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Remote execution
# ---------------------------------------------------------------------------


class Runner(Protocol):
    """Runs a local command; a seam so tests can record commands offline."""

    def run(self, argv: Sequence[str], stdin_path: Path | None = None) -> int: ...


class SubprocessRunner:
    def run(self, argv: Sequence[str], stdin_path: Path | None = None) -> int:
        if stdin_path is None:
            return subprocess.run(list(argv), check=False).returncode
        with open(stdin_path, "rb") as stdin:
            return subprocess.run(list(argv), check=False, stdin=stdin).returncode


@dataclass(frozen=True)
class DevicePaths:
    """Fixed device locations (conventions of the installed developer image)."""

    deploy: str = "/var/lib/greia/deploy"
    live: str = "/opt/greia-os"
    index: str = "/usr/share/greia/activity-index-v1.json"
    units: str = "/etc/systemd/system"

    @property
    def new(self) -> str:
        return f"{self.deploy}/new"

    @property
    def prev(self) -> str:
        return f"{self.deploy}/prev"


def validate_target(target: str) -> str:
    """Accept only ``user@host`` shaped values that cannot be read as ssh options."""
    if not _TARGET_RE.match(target):
        raise DeployError(
            f"--target must look like user@host (or set {TARGET_ENV}); got {target!r}"
        )
    return target


def _assignments(**values: str) -> str:
    return "".join(f"{name}={shlex.quote(value)}\n" for name, value in values.items())


class RemoteScripts:
    """Fixed remote scripts; the only interpolated values are quoted constants."""

    def __init__(self, paths: DevicePaths = DevicePaths()) -> None:
        self._paths = paths

    def prepare(self) -> str:
        return "set -eu\n" + _assignments(D=self._paths.deploy, NEW=self._paths.new) + (
            'install -d -m 0755 "$D"\n'
            'rm -rf "$NEW"\n'
            'install -d -m 0755 "$NEW"\n'
        )

    def swap(self) -> str:
        paths = self._paths
        assignments = _assignments(
            D=paths.deploy, NEW=paths.new, PREV=paths.prev, LIVE=paths.live,
            INDEX=paths.index, UNITS=paths.units,
            SERVICES=" ".join(SERVICES),
        )
        return "set -eu\n" + assignments + r'''
[ -d "$NEW/opt/greia-os/src" ] || { echo "no staged bundle in $NEW; run push first" >&2; exit 2; }
[ -f "$NEW/usr/share/greia/activity-index-v1.json" ] || { echo "staged bundle has no index" >&2; exit 2; }
systemctl stop $SERVICES
rm -rf "$PREV"
install -d -m 0755 "$PREV"
if [ -d "$LIVE" ]; then mv "$LIVE" "$PREV/greia-os"; fi
if [ -f "$INDEX" ]; then cp -p "$INDEX" "$PREV/activity-index-v1.json"; fi
mv "$NEW/opt/greia-os" "$LIVE"
install -D -m 0644 -o root -g root "$NEW/usr/share/greia/activity-index-v1.json" "$INDEX"
chown -R root:root "$LIVE"
chmod -R a-w "$LIVE"
changed=0
for unit in $SERVICES; do
  src="$NEW/units/$unit.service"
  dst="$UNITS/$unit.service"
  if [ -f "$src" ] && ! cmp -s "$src" "$dst"; then
    install -m 0644 -o root -g root "$src" "$dst"
    echo "unit updated: $unit"
    changed=1
  fi
done
if [ "$changed" = 1 ]; then systemctl daemon-reload; fi
/usr/bin/python3 -I -B "$NEW/tools/precompile_greia_bytecode.py" --greia-root "$LIVE" \
  || echo "WARNING: bytecode prefix rebuild failed; launch timings are not meaningful" >&2
systemctl start $SERVICES
sleep 5
'''

    def health(self) -> str:
        return "set -u\n" + _assignments(
            LIVE=self._paths.live, SERVICES=" ".join(SERVICES)
        ) + r'''
for unit in $SERVICES; do
  active=$(systemctl is-active "$unit" || true)
  restarts=$(systemctl show "$unit" -p NRestarts --value || true)
  echo "$unit active=$active restarts=$restarts"
done
echo "deployed sha: $(cat "$LIVE/.deployed-sha" 2>/dev/null || echo unknown)"
'''

    def cleanup(self) -> str:
        return "set -eu\n" + _assignments(
            D=self._paths.deploy, NEW=self._paths.new, PREV=self._paths.prev
        ) + 'rm -rf "$PREV" "$NEW"\nrm -f "$D"/*.tar.gz\necho "removed prev/new/tarballs under $D"\n'


class RemoteDevice:
    """Builds and runs ssh commands against one validated ``user@host`` target."""

    SSH_OPTIONS = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=15")

    def __init__(self, target: str, runner: Runner | None = None,
                 paths: DevicePaths = DevicePaths()) -> None:
        self.target = validate_target(target)
        self._runner = runner or SubprocessRunner()
        self.paths = paths
        self.scripts = RemoteScripts(paths)

    def ssh_argv(self, remote_command: str) -> list[str]:
        return ["ssh", *self.SSH_OPTIONS, "--", self.target, remote_command]

    @staticmethod
    def sudo(argv: Sequence[str]) -> str:
        return shlex.join(["sudo", "-n", *argv])

    @classmethod
    def sudo_script(cls, script: str) -> str:
        return cls.sudo(["/bin/sh", "-c", script])

    def _run(self, remote_command: str, what: str, stdin_path: Path | None = None) -> None:
        code = self._runner.run(self.ssh_argv(remote_command), stdin_path)
        if code != 0:
            raise DeployError(f"{what} failed on the device (exit {code})")

    def require_sudo(self) -> None:
        code = self._runner.run(self.ssh_argv(self.sudo(["true"])))
        if code != 0:
            raise DeployError(
                "cannot run 'sudo -n' on the device (ssh key login or passwordless sudo is "
                "not provisioned for this operator); stopping. Ask the device owner."
            )

    def push(self, bundle: Path) -> None:
        self.require_sudo()
        self._run(self.sudo_script(self.scripts.prepare()), "preparing staging area")
        self._run(
            self.sudo(["tar", "-xzf", "-", "-C", self.paths.new, "--no-same-owner"]),
            "extracting bundle", stdin_path=bundle,
        )
        self._run(
            self.sudo(["python3", "-I", "-B", "-c", PARSE_GATE_CODE, self.paths.new + "/opt/greia-os"]),
            "Python 3.11 parse gate",
        )

    def swap(self) -> None:
        self.require_sudo()
        try:
            self._run(self.sudo_script(self.scripts.swap()), "swap")
        except DeployError as exc:
            raise DeployError(
                f"{exc}. Services may be stopped; the previous tree, if moved, is in "
                f"{self.paths.prev}. Fix forward from 'journalctl -u greia-launcher'."
            ) from exc
        self.status()

    def status(self) -> None:
        self.require_sudo()
        self._run(self.sudo_script(self.scripts.health()), "health check")

    def cleanup(self) -> None:
        self.require_sudo()
        self._run(self.sudo_script(self.scripts.cleanup()), "cleanup")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _stage_to_temp(stager: BundleStager, then: Callable[[Path, str], None]) -> None:
    work = Path(tempfile.mkdtemp(prefix="greia-dev-deploy."))
    try:
        sha = stager.stage(work / "bundle.tar.gz", work)
        then(work / "bundle.tar.gz", sha)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("stage", help="build the bundle tarball from git archive HEAD")
    stage.add_argument("--output", type=Path, default=None,
                       help="tarball path (default: ~/.cache/greia-dev-deploy/bundle-<sha12>.tar.gz)")
    for name, text in (
        ("push", "stage, upload, extract and parse-gate on the device"),
        ("swap", "swap the pushed bundle in and restart services"),
        ("deploy", "push + swap"),
        ("status", "print service health and deployed sha"),
        ("cleanup", "remove the backup and staging areas on the device"),
    ):
        command = sub.add_parser(name, help=text)
        command.add_argument("--target", default=os.environ.get(TARGET_ENV),
                             help=f"operator@device (default: ${TARGET_ENV})")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    args = _parse_args(argv)
    stager = BundleStager()
    try:
        if args.command == "stage":
            def keep(bundle: Path, sha: str) -> None:
                output = args.output or (
                    Path.home() / ".cache" / "greia-dev-deploy" / f"bundle-{sha[:12]}.tar.gz"
                )
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(bundle), output)
                print(f"staged {sha} -> {output}")
            _stage_to_temp(stager, keep)
            return 0
        if not args.target:
            raise DeployError(f"--target operator@device is required (or set {TARGET_ENV})")
        device = RemoteDevice(args.target)
        if args.command in ("push", "deploy"):
            if stager.dirty():
                print("note: uncommitted changes are NOT deployed (bundle is git archive HEAD)",
                      file=sys.stderr)

            def upload(bundle: Path, sha: str) -> None:
                print(f"pushing {sha}")
                device.push(bundle)
            _stage_to_temp(stager, upload)
        if args.command in ("swap", "deploy"):
            device.swap()
        elif args.command == "status":
            device.status()
        elif args.command == "cleanup":
            device.cleanup()
        return 0
    except DeployError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
