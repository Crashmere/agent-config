#!/usr/bin/env python3
"""Synthetic contract regression checks; uses no server or real application data."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import sys
sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location("contract", Path(__file__).with_name("validate-portal.py"))
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def fixture():
    return dict(id="sample", name="Sample", description="Example", icon="", url="/sample/",
                repo="https://github.com/Example/Sample", root="/opt/sample", port=18099,
                user="sample", units=["sample.service"], database="/opt/sample/data/sample.db",
                backupKind="sqlite", resources=[dict(id="data", name="Data", path="/opt/sample/data",
                purpose="Application data", kind="data", browse=True, cleanup=False)], apis=[])


class ContractTests(unittest.TestCase):
    def check(self, value):
        return contract.validate(json.dumps(value).encode(), "sample")

    def test_valid(self):
        self.assertEqual(self.check(fixture())["id"], "sample")

    def test_identity_and_permission_boundaries(self):
        cases = [("id", "other"), ("root", "/etc"), ("user", "root"),
                 ("database", "/opt/other/data/other.db"), ("units", ["sshd.service"]),
                 ("url", "//other/"), ("port", True), ("unknown", "ignored?")]
        for key, value in cases:
            with self.subTest(key=key):
                a = fixture(); a[key] = value
                with self.assertRaises((ValueError, TypeError)): self.check(a)

    def test_resource_boundaries(self):
        changes = [{"path": "/etc"}, {"path": "/opt/sample/data/../../other"},
                   {"path": "/opt/sample/config"}, {"cleanup": True},
                   {"kind": "documents"}, {"browse": "false"}]
        for change in changes:
            with self.subTest(change=change):
                a = fixture(); a["resources"][0].update(change)
                with self.assertRaises(ValueError): self.check(a)

    def test_duplicate_fields_and_oversized_input(self):
        with self.assertRaises(ValueError): contract.validate(b'{"id":"sample","id":"other"}', "sample")
        with self.assertRaises(ValueError): contract.validate(b" " * (contract.LIMIT + 1), "sample")

    def test_same_endpoint_can_document_distinct_actions(self):
        a = fixture()
        a["apis"] = [dict(method="POST", path="/api/record", description=d) for d in ("save", "favorite")]
        self.check(a)
        a["apis"].append(copy.deepcopy(a["apis"][0]))
        with self.assertRaises(ValueError): self.check(a)


if __name__ == "__main__":
    unittest.main()
