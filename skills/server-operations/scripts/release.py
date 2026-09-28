#!/usr/bin/env python3
"""Local release helper. Python standard library only; never runs a regression suite."""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def run(args, cwd=None, capture=False, **kwargs):
    if capture:
        kwargs.update(text=True, stdout=subprocess.PIPE)
    return subprocess.run(args, cwd=cwd, check=True, **kwargs)


def git(root, *args):
    return run(["git", *args], cwd=root, capture=True).stdout.strip()


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def clean_commit(root):
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Commit tracked changes before releasing. Untracked files are excluded by git archive.")
    return git(root, "rev-parse", "HEAD")


def backed_up(root, commit):
    remote = git(root, "ls-remote", "origin", "refs/heads/main")
    if not remote or remote.split()[0] != commit:
        raise ValueError("Push this commit to origin/main before deployment; GitHub is the source backup.")


def verify(bundle, cfg):
    m = load(bundle / "manifest.json")
    if (m["app"] != cfg["app"] or not re.fullmatch(r"[0-9a-f]{40}", m["commit"])
            or m["commit"] != bundle.name):
        raise ValueError("Release manifest does not match the application or requested commit.")
    for name, expected in m["files"].items():
        if Path(name).name != name or digest(bundle / name) != expected:
            raise ValueError("Release checksum mismatch: " + name)
    if "program" not in m["files"]:
        raise ValueError("Release has no program.")
    if cfg.get("portal") and "portal.json" not in m["files"]:
        raise ValueError("Release has no portal declaration.")
    return m


def build(root, cfg, commit):
    releases = root / ".local/releases"
    releases.mkdir(parents=True, exist_ok=True)
    bundle = releases / commit
    if bundle.exists():
        verify(bundle, cfg)
        print("Reuse verified release: " + str(bundle), flush=True)
        return bundle
    with tempfile.TemporaryDirectory(prefix=".build-", dir=releases) as tmp:
        work = Path(tmp)
        source = work / "source"
        source.mkdir()
        archive = work / "source.tar"
        with archive.open("wb") as f:
            run(["git", "archive", commit], cwd=root, stdout=f)
        run(["tar", "-xf", str(archive), "-C", str(source)])
        if (source / "web/package-lock.json").exists():
            run(["npm", "--prefix", "web", "ci", "--no-audit", "--no-fund"], cwd=source)
        run(cfg["build"], cwd=source)
        output = work / "release"
        output.mkdir()
        shutil.copy2(source / cfg["binary"], output / "program")
        files = {"program": digest(output / "program")}
        if cfg.get("portal"):
            declaration = source / "deploy/portal.json"
            run([sys.executable, str(Path(__file__).with_name("validate-portal.py")),
                 "--app", cfg["app"], "--file", str(declaration)])
            shutil.copy2(declaration, output / "portal.json")
            files["portal.json"] = digest(output / "portal.json")
        versions = {"go": run(["go", "version"], cwd=source, capture=True).stdout.strip()}
        if (source / "web/package.json").exists():
            versions.update({tool: run([tool, "--version"], capture=True).stdout.strip()
                             for tool in ("node", "npm")})
        save(output / "manifest.json", {"app": cfg["app"], "commit": commit,
             "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "files": files, "build": cfg["build"], "toolchain": versions,
             "verification": "Build and declaration validation only; feature checks are performed before release."})
        output.rename(bundle)
    print("Built release: " + str(bundle), flush=True)
    return bundle


def ssh(cfg, command, stream=None):
    args = ["ssh", "-T", "-C", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=4"]
    if cfg.get("restricted", True):
        key = Path(os.environ.get("RELEASE_KEY", "~/.ssh/ali_deploy_ed25519")).expanduser()
        if not key.is_file():
            raise ValueError("Local deployment key not found: " + str(key))
        args += ["-i", str(key), "-o", "IdentitiesOnly=yes", "-l", cfg["app"] + "-deploy"]
    args += [os.environ.get("RELEASE_HOST", "ali"), command]
    run(args, stdin=stream)


def public_check(cfg):
    host = os.environ.get("RELEASE_HOST", "ali")
    settings = run(["ssh", "-T", "-G", host], capture=True).stdout
    hostname = next(line.split(None, 1)[1] for line in settings.splitlines()
                    if line.startswith("hostname "))
    if ":" in hostname:
        hostname = "[" + hostname + "]"
    path = "/portal/api/session" if cfg["app"] == "serverportal" else "/" + cfg["app"] + "/healthz"
    status = run(["curl", "--silent", "--show-error", "--proto", "=https", "--max-time", "15",
                  "-o", os.devnull, "-w", "%{http_code}", "https://" + hostname + path], capture=True).stdout
    if status != "401":
        raise ValueError("Public authentication check expected 401, got " + status)


def publish(root, cfg, bundle, rollback=False):
    m = verify(bundle, cfg)
    commit = m["commit"]
    if not rollback:
        if clean_commit(root) != commit:
            raise ValueError("Release does not match HEAD.")
        backed_up(root, commit)
    # Preflight remains read-only, and is checked before stopping the application.
    if cfg.get("portal"):
        with (bundle / "portal.json").open("rb") as f:
            ssh(cfg, f"portal-check {commit} {m['files']['portal.json']}", f)
    command = f"deploy {commit} {m['files']['program']}"
    if not cfg.get("restricted", True):
        command = f"/opt/{cfg['app']}/bin/deploy-release.sh {commit} {m['files']['program']}"
    if cfg.get("gzip"):
        with tempfile.TemporaryFile() as compressed:
            with gzip.GzipFile(fileobj=compressed, mode="wb", mtime=0) as target:
                with (bundle / "program").open("rb") as source:
                    shutil.copyfileobj(source, target)
            compressed.seek(0)
            ssh(cfg, command, compressed)
    else:
        with (bundle / "program").open("rb") as source:
            ssh(cfg, command, source)
    # Record the program switch even when the independent declaration update fails.
    receipt = {"commit": commit, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "rollback": rollback, "program": "success", "portal": "not-applicable"}
    save(bundle / "last-deployment.json", receipt)
    if cfg.get("portal"):
        receipt["portal"] = "pending"
        save(bundle / "last-deployment.json", receipt)
        with (bundle / "portal.json").open("rb") as f:
            ssh(cfg, f"portal {commit} {m['files']['portal.json']}", f)
        receipt["portal"] = "success"
        save(bundle / "last-deployment.json", receipt)
    public_check(cfg)
    receipt["public_auth"] = "success"
    save(bundle / "last-deployment.json", receipt)
    print("Deployment complete: " + commit, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("action", choices=["build", "deploy", "portal", "rollback", "list"])
    parser.add_argument("commit", nargs="?", help="Explicit previous commit for rollback")
    args = parser.parse_args()
    root = args.project.resolve()
    cfg = load(root / "deploy/release.json")
    # goenv is lazily initialized in interactive shells on the maintenance Mac.
    shims = Path.home() / ".goenv/shims"
    if shims.is_dir():
        os.environ["PATH"] = str(shims) + os.pathsep + os.environ["PATH"]
    if args.action == "list":
        for m in sorted((root / ".local/releases").glob("*/manifest.json")):
            print(m.parent.name, load(m).get("created_at", ""))
        return
    if args.action == "rollback":
        if not args.commit or not re.fullmatch(r"[0-9a-f]{40}", args.commit):
            raise ValueError("rollback requires an explicit full commit from the local release list.")
        print("Rolling back the program; existing data is retained. Confirm schema compatibility before using this command.", flush=True)
        publish(root, cfg, root / ".local/releases" / args.commit, rollback=True)
        return
    commit = clean_commit(root)
    if args.action == "portal":
        if not cfg.get("portal"):
            raise ValueError("This application has no business-app portal declaration.")
        backed_up(root, commit)
        with tempfile.TemporaryFile() as stream:
            data = run(["git", "show", commit + ":deploy/portal.json"], cwd=root, capture=True).stdout.encode()
            stream.write(data)
            checksum = hashlib.sha256(data).hexdigest()
            for operation in ["portal-check", "portal"]:
                stream.seek(0)
                ssh(cfg, f"{operation} {commit} {checksum}", stream)
        return
    bundle = build(root, cfg, commit)
    if args.action == "deploy":
        publish(root, cfg, bundle)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as e:
        print("Release stopped: " + str(e), file=sys.stderr)
        sys.exit(1)
