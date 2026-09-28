#!/usr/bin/env python3
"""Validate an application's portal declaration locally and on the server (stdlib only)."""
import argparse
import hashlib
import json
import posixpath
import re
import sys

LIMIT = 1024 * 1024
ID = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON field: " + key)
        result[key] = value
    return result


def fields(obj, required, optional=()):
    require(isinstance(obj, dict), "expected an object")
    require(set(required) <= obj.keys(), "missing required fields")
    require(obj.keys() <= set(required) | set(optional), "unknown fields")


def text(value, maximum=1024, empty=False):
    require(isinstance(value, str) and (empty or bool(value)) and len(value.encode()) <= maximum,
            "invalid text value")
    require(not any(ord(c) < 32 or ord(c) == 127 for c in value), "control characters are forbidden")


def inside(path, root):
    text(path)
    require(path.startswith(root + "/") and posixpath.normpath(path) == path and "\\" not in path,
            "path must remain inside " + root)


def validate(data, app):
    require(ID.fullmatch(app) is not None, "invalid expected application ID")
    require(0 < len(data) <= LIMIT, "declaration must be 1 byte to 1 MiB")
    a = json.loads(data, object_pairs_hook=unique_object)
    fields(a, ("id", "name", "description", "icon", "url", "repo", "root", "port", "user",
               "units", "database", "backupKind", "resources", "apis"))
    root = "/opt/" + app
    require(a["id"] == app and a["root"] == root and a["user"] == app,
            "declaration cannot change application identity, root or runtime user")
    text(a["name"], 120)
    text(a["description"], 2048, empty=True)
    text(a["icon"], empty=True)
    require(not a["icon"] or (a["icon"].startswith("/") and not a["icon"].startswith("//")),
            "icon must be a same-origin path")
    require(a["url"] == "/" + app + "/", "application URL must match its registered prefix")
    text(a["repo"])
    require(re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", a["repo"]) is not None,
            "repo must be a GitHub HTTPS repository URL")
    require(type(a["port"]) is int and 1024 <= a["port"] <= 65535, "invalid application port")
    inside(a["database"], root + "/data")
    require(a["database"].endswith((".sqlite", ".db")), "expected a SQLite database path")
    require(a["backupKind"] in ("sqlite", "media"), "unsupported native backup contract")
    require(isinstance(a["units"], list) and 0 < len(a["units"]) <= 32, "invalid units")
    require(len(set(a["units"])) == len(a["units"]), "duplicate units")
    for unit in a["units"]:
        text(unit, 120)
        require(re.fullmatch(re.escape(app) + r"(?:-[a-z0-9-]+)?\.(?:service|timer)", unit) is not None,
                "unit must belong to this application")
    require(app + ".service" in a["units"], "main application unit is missing")
    require(isinstance(a["resources"], list) and 0 < len(a["resources"]) <= 128, "invalid resources")
    ids, paths = set(), set()
    for r in a["resources"]:
        fields(r, ("id", "name", "path", "purpose", "kind", "browse", "cleanup"))
        text(r["id"], 64)
        require(ID.fullmatch(r["id"]) is not None and r["id"] not in ids, "invalid or duplicate resource ID")
        ids.add(r["id"])
        text(r["name"], 120)
        text(r["purpose"], 2048)
        inside(r["path"], root)
        require(r["path"] not in paths, "duplicate resource path")
        paths.add(r["path"])
        require(r["kind"] in ("data", "media", "backups", "releases", "config", "binaries", "documents", "secret"),
                "unknown resource kind")
        require(type(r["browse"]) is bool and type(r["cleanup"]) is bool, "permissions must be booleans")
        top = r["path"][len(root) + 1:].split("/")[0]
        require(not r["browse"] or (top in ("data", "backups", "releases", "docs") and
                r["kind"] not in ("secret", "config", "binaries")), "sensitive material cannot be browsed")
        require(r["kind"] != "documents" or top == "docs", "documents must stay under the application docs directory")
        require(not r["cleanup"] or (r["id"] in ("backups", "releases") and
                r["path"] == root + "/" + r["id"] and r["kind"] == r["id"]),
                "cleanup is restricted to the application's backups/releases roots")
    require(isinstance(a["apis"], list) and len(a["apis"]) <= 1024, "invalid API list")
    endpoints = set()
    for endpoint in a["apis"]:
        fields(endpoint, ("method", "path", "description"))
        text(endpoint["path"])
        text(endpoint["description"], 2048)
        require(endpoint["method"] in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"), "invalid HTTP method")
        require(endpoint["path"].startswith("/") and not endpoint["path"].startswith("//"), "invalid API path")
        key = (endpoint["method"], endpoint["path"], endpoint["description"])
        require(key not in endpoints, "duplicate API entry")
        endpoints.add(key)
    return a


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--file", help="omit to read stdin")
    args = parser.parse_args()
    if args.file:
        with open(args.file, "rb") as source:
            data = source.read(LIMIT + 1)
    else:
        data = sys.stdin.buffer.read(LIMIT + 1)
    try:
        validate(data, args.app)
    except (ValueError, TypeError, KeyError) as error:
        parser.exit(1, "Invalid portal declaration: " + str(error) + "\n")
    print("Validated", args.app, hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
