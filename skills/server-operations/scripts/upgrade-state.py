#!/usr/bin/env python3
"""NAS upgrade protection. Caller holds global shared and application deploy locks."""
import argparse
import base64
from contextlib import closing
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import sys


APPLICATIONS = {"ledger", "feetable", "fabricworld", "recipebox", "yuyan",
                "aicalendar", "aura", "serverportal"}
SNAPSHOTS = Path("/var/lib/server-upgrades")


def run(*args):
    subprocess.run(args, check=True)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    with path.open("x") as output:
        json.dump(value, output, indent=2)
        output.write("\n")


def inventory(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(directory) / name
            relative = str(path.relative_to(root))
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                result[relative] = {"link": os.readlink(path)}
            elif stat.S_ISREG(mode):
                result[relative] = {"sha256": digest(path)}
            elif not stat.S_ISDIR(mode):
                raise ValueError("Non-file application state: " + relative)
    return result


def open_database(path):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def database_check(before, after=None):
    with closing(open_database(after or before)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Database integrity check failed: " + before.name)
        if connection.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Database foreign-key check failed: " + before.name)
        if after is None:
            return
        connection.execute("ATTACH DATABASE ? AS previous",
                           (before.resolve().as_uri() + "?mode=ro",))
        connection.execute("BEGIN")
        tables = connection.execute("SELECT name FROM previous.sqlite_schema "
                                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        for (table,) in tables:
            columns = [row[1] for row in connection.execute(
                "PRAGMA previous.table_info(" + quote(table) + ")")]
            current = [row[1] for row in connection.execute(
                "PRAGMA main.table_info(" + quote(table) + ")")]
            if not columns or not set(columns).issubset(current):
                raise ValueError("Previous table/columns missing: " + before.name + "/" + table)
            # Compare row multiplicities, including BLOB archives; counts alone miss overwritten rows.
            selected = ", ".join(quote(column) + " COLLATE BINARY" for column in columns)
            count = "__upgrade_count"
            while count in columns:
                count += "_"
            grouped = selected + ", COUNT(*) AS " + quote(count)
            joined = " AND ".join("old." + quote(column) + " IS now." + quote(column)
                                  + " COLLATE BINARY" for column in columns)
            query = ("WITH old AS (SELECT " + grouped + " FROM previous." + quote(table)
                     + " GROUP BY " + selected + "), now AS (SELECT " + grouped
                     + " FROM main." + quote(table) + " GROUP BY " + selected
                     + ") SELECT 1 FROM old LEFT JOIN now ON " + joined
                     + " WHERE now." + quote(count) + " IS NULL OR now." + quote(count)
                     + " < old." + quote(count) + " LIMIT 1")
            if connection.execute(query).fetchone():
                raise ValueError("Previous rows changed or missing: " + before.name + "/" + table)


def units(app):
    return [app + ".service"] + (["serverportal-agent.service"] if app == "serverportal" else [])


def program(root, app):
    return root / "bin" / ("portal" if app == "serverportal" else app)


def portal_devices(before, after):
    original = json.loads(before.read_text())
    current = json.loads(after.read_text())
    indexed = {device["id"]: device for device in current}
    if len(indexed) != len(current):
        raise ValueError("Portal contains duplicate device identities.")
    for device in original:
        found = indexed.get(device["id"])
        if found is None or {key: value for key, value in device.items() if key != "seen"} != {
                key: value for key, value in found.items() if key != "seen"}:
            raise ValueError("Portal device grant changed or missing.")
        previous_seen = datetime.datetime.fromisoformat(device["seen"].replace("Z", "+00:00"))
        current_seen = datetime.datetime.fromisoformat(found["seen"].replace("Z", "+00:00"))
        if current_seen < previous_seen:
            raise ValueError("Portal device last-seen time moved backwards.")


def stopped(app):
    for unit in units(app):
        state = subprocess.run(["systemctl", "show", unit, "-p", "ActiveState", "--value"],
                               check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
        if state != "inactive":
            raise ValueError("Gracefully stop " + unit + " before copying or validating cold state.")


def database_selection(root, requested):
    if not isinstance(requested, list) or len(requested) > 16:
        raise ValueError("Expected at most 16 database backup declarations.")
    result = {}
    data = root / "data"
    for item in requested:
        if not isinstance(item, dict) or set(item) != {"path", "reason"}:
            raise ValueError("Each database declaration needs only path and reason.")
        relative, reason = item["path"], item["reason"]
        if (not isinstance(relative, str) or not re.fullmatch(r"[A-Za-z0-9_./-]{1,200}", relative)
                or any(part in ("", ".", "..") for part in relative.split("/"))
                or not isinstance(reason, str) or not reason.strip() or len(reason) > 500):
            raise ValueError("Invalid database path or missing deletion/overwrite reason.")
        path = data / relative
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("Database backup paths must not contain symbolic links.")
        if not path.is_file():
            raise ValueError("Database backup source does not exist: " + relative)
        with path.open("rb") as source:
            if source.read(16) != b"SQLite format 3\x00":
                raise ValueError("Temporary upgrade backups accept only SQLite databases: " + relative)
        result[relative] = {"path": relative, "reason": reason.strip()}
    return list(result.values())


def plan(app, root, release, requested):
    rehearse = False
    if app == "yuyan":
        output = subprocess.run(["runuser", "-u", app, "--", "timeout", "60",
            str(release / "yuyan"), "migrate", "--dry-run", "--data", str(root / "data")],
            check=True, text=True, stdout=subprocess.PIPE).stdout
        migration = json.loads(output)
        steps = migration["steps"]
        if not isinstance(steps, list) or not all(isinstance(step, str) for step in steps):
            raise ValueError("Invalid Yuyan migration preview.")
        # Current pending layout steps rebuild or drop existing tables.
        if steps:
            requested = [*requested, {"path": "yuyan.db", "reason": "; ".join(steps)}]
        rehearse = bool(steps)
    selected = database_selection(root, requested)
    if app == "fabricworld" and selected:
        rehearse = True
    return selected, rehearse


def begin(app, root, release, snapshot, requested):
    stopped(app)
    state_path = release / "upgrade-state.json"
    if state_path.exists() or snapshot.exists():
        raise ValueError("Upgrade state already exists; inspect the previous attempt.")
    selected, rehearse = plan(app, root, release, requested)
    candidate = root / "data"
    if selected:
        snapshot.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        snapshot.mkdir(mode=0o700)
        entries = {}
        for item in selected:
            relative = item["path"]
            destination = snapshot / "data" / relative
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # SQLite backup includes committed WAL content without copying other files.
            with closing(open_database(root / "data" / relative)) as source:
                with closing(sqlite3.connect(destination)) as target:
                    source.backup(target)
                    target.execute("PRAGMA journal_mode=DELETE").fetchone()
            destination.chmod(0o600)
            database_check(destination)
            entries[relative] = {"sha256": digest(destination)}
        save(snapshot / "snapshot.json", {"app": app, "release": release.name,
             "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "scope": "databases", "data": entries, "databases": list(entries),
             "selection": selected})
        run("sync", "-f", str(snapshot))
        if rehearse:
            candidate = release / "upgrade-check-data"
            candidate.mkdir(mode=0o700)
            for relative in entries:
                destination = candidate / relative
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                shutil.copyfile(snapshot / "data" / relative, destination)
                destination.chmod(0o600)
            if app == "yuyan":
                # Migration/check need to find originals; reference them without copying payloads.
                (candidate / "assets").symlink_to(root / "data" / "assets", target_is_directory=True)
            run("chown", "-R", "--no-dereference", app + ":" + app, str(candidate))
    save(state_path, {"app": app, "release": release.name, "databases": selected,
         "candidate_data": str(candidate), "program_sha256": digest(release / ("portal" if app == "serverportal" else app))})
    if selected:
        print("Temporary backup: " + ", ".join(item["path"] for item in selected), file=sys.stderr)
    else:
        print("No database deletion/overwrite risk declared; temporary backup skipped.", file=sys.stderr)
    print(str(candidate))


def verify(app, root, release, snapshot):
    stopped(app)
    metadata = json.loads((snapshot / "snapshot.json").read_text())
    if metadata["app"] != app or metadata["release"] != release.name:
        raise ValueError("Upgrade snapshot identity mismatch.")
    dbs = set(metadata["databases"])
    if metadata.get("scope") == "databases":
        for relative in dbs:
            if digest(snapshot / "data" / relative) != metadata["data"][relative]["sha256"]:
                raise ValueError("Immutable database snapshot has changed: " + relative)
            database_check(snapshot / "data" / relative, root / "data" / relative)
        save(snapshot / "verified.json", {"program_sha256": digest(program(root, app)),
             "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "verification": "Selected databases preserve previous rows and columns, including BLOBs."})
        print("Selected database validation passed; retain protection until runtime acceptance.")
        return
    shared_memory = {relative + "-shm" for relative in dbs}
    if {key: value for key, value in inventory(snapshot / "data").items() if key not in shared_memory} != {
            key: value for key, value in metadata["data"].items() if key not in shared_memory}:
        raise ValueError("Immutable upgrade snapshot has changed.")
    current = inventory(root / "data")
    journals = {relative + suffix for relative in dbs for suffix in ("-wal", "-shm", "-journal")}
    for relative, entry in metadata["data"].items():
        if relative in dbs or relative in journals:
            continue
        if app == "serverportal" and relative == "devices.json":
            portal_devices(snapshot / "data" / relative, root / "data" / relative)
            continue
        if current.get(relative) != entry:
            raise ValueError("Previous file changed or missing: " + relative)
    for relative in dbs:
        database_check(snapshot / "data" / relative, root / "data" / relative)
    save(snapshot / "verified.json", {"program_sha256": digest(program(root, app)),
         "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "verification": "All previous SQLite rows/columns and non-database files preserved; "
                         "Portal grants unchanged except monotonic last-seen timestamps."})
    print("Cold data validation passed; snapshot remains until final runtime acceptance.")


def accept(app, root, release, snapshot, manual_validation):
    state_path = release / "upgrade-state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else None
    if state and (state["app"] != app or state["release"] != release.name):
        raise ValueError("Upgrade state identity mismatch.")
    if state and state["program_sha256"] != digest(program(root, app)):
        raise ValueError("Running program differs from the planned candidate.")
    if state and not state["databases"]:
        if manual_validation:
            raise ValueError("Manual database acceptance requires an existing backup.")
        verification = {"program_sha256": state["program_sha256"],
                        "verification": "Runtime acceptance; no database backup required."}
    elif manual_validation:
        verification = {"evidence": manual_validation, "program_sha256": digest(program(root, app))}
    else:
        verification = json.loads((snapshot / "verified.json").read_text())
        if verification["program_sha256"] != digest(program(root, app)):
            raise ValueError("Program changed after cold data validation.")
    for unit in units(app):
        run("systemctl", "is-active", "--quiet", unit)
    verification["accepted_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    verification["databases"] = state["databases"] if state else "legacy-full-state"
    save(release / "upgrade-acceptance.json", verification)
    if not snapshot.exists():
        print("Accepted upgrade; no temporary database backup was created.")
        return
    try:
        shutil.rmtree(snapshot)
    except OSError as error:
        print("Upgrade accepted, but its temporary snapshot cleanup needs inspection: " + str(error),
              file=sys.stderr)
        return
    work = release / "upgrade-check-data"
    if work.is_dir() and not work.is_symlink():
        try:
            shutil.rmtree(work)
        except OSError as error:
            print("Upgrade accepted; remove its disposable check copy separately: " + str(error),
                  file=sys.stderr)
    print("Accepted upgrade; removed only its temporary local snapshot and check copy.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("begin", "verify", "accept"))
    parser.add_argument("--app", required=True, choices=sorted(APPLICATIONS))
    parser.add_argument("--release", required=True, help="Existing <full-commit>.<mktemp-suffix> directory name")
    parser.add_argument("--plan-token", default="", help="Bounded base64url database declarations from local release")
    parser.add_argument("--database", action="append", default=[], help="Affected SQLite path relative to application data; begin only")
    parser.add_argument("--reason", help="Concrete database deletion/overwrite operation; begin only")
    parser.add_argument("--manual-validation", help="Agent evidence for an intentionally changed state; accept only")
    args = parser.parse_args()
    if os.geteuid() != 0 or Path("/etc/server-maintenance-host").read_text().strip() != "nas":
        raise ValueError("This helper requires root on the explicitly configured NAS host.")
    if not re.fullmatch(r"[0-9a-f]{40}\.[A-Za-z0-9]{6,}", args.release):
        raise ValueError("Invalid release directory name.")
    requested = []
    if args.plan_token:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,4096}", args.plan_token):
            raise ValueError("Invalid or oversized database plan token.")
        requested = json.loads(base64.b64decode(args.plan_token + "=" * (-len(args.plan_token) % 4),
                                              altchars=b"-_", validate=True))
        if not isinstance(requested, list):
            raise ValueError("Database plan must be a list.")
    if args.database:
        if not args.reason:
            raise ValueError("Database protection requires a concrete deletion/overwrite reason.")
        requested.extend({"path": path, "reason": args.reason} for path in args.database)
    if args.action != "begin" and (requested or args.reason):
        raise ValueError("Database selection applies only when beginning an upgrade.")
    if args.manual_validation and args.action != "accept":
        raise ValueError("Manual evidence applies only after independent data and runtime validation.")
    root = Path("/opt") / args.app
    release = root / "releases" / args.release
    snapshot = SNAPSHOTS / args.app / args.release
    if release.is_symlink() or not release.is_dir() or release.stat().st_uid != 0:
        raise ValueError("Expected root-owned application release directory.")
    if snapshot.is_symlink() or (snapshot.exists() and snapshot.stat().st_uid != 0):
        raise ValueError("Expected root-private upgrade snapshot directory.")
    os.umask(0o077)
    if args.action == "begin":
        begin(args.app, root, release, snapshot, requested)
    elif args.action == "verify":
        verify(args.app, root, release, snapshot)
    else:
        accept(args.app, root, release, snapshot, args.manual_validation)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, sqlite3.Error, subprocess.CalledProcessError) as error:
        print("Upgrade protection stopped; retain snapshot for inspection: " + str(error), file=sys.stderr)
        sys.exit(1)
