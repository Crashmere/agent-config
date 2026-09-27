#!/usr/bin/env python3
"""Exercise an app's actual restricted SSH wrapper and metadata dispatcher with mocks."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--app", required=True)
parser.add_argument("--directory", required=True)
args = parser.parse_args()
directory = Path(args.directory).resolve()
commit, digest = "a" * 40, "b" * 64

with tempfile.TemporaryDirectory(prefix="portal-protocol-") as temporary:
    root = Path(temporary)
    log = root / "call"
    mock = root / "sudo"
    mock.write_text('#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\n'
                    'Path(os.environ["PORTAL_TEST_CALL"]).write_text(json.dumps(sys.argv[1:]))\n')
    mock.chmod(0o755)
    env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"], PORTAL_TEST_CALL=str(log))
    import json
    for action in ("deploy", "portal-check", "portal"):
        env["SSH_ORIGINAL_COMMAND"] = f"{action} {commit} {digest}"
        subprocess.run(["bash", str(directory / "deploy-ssh.sh")], env=env, check=True)
        want = ["-n", f"/opt/{args.app}/bin/deploy-release.sh"]
        if action != "deploy": want.append(action)
        assert json.loads(log.read_text()) == want + [commit, digest]
        log.unlink()
    for command in ("id", f"portal {commit} {digest}; id", f"portal {commit} {digest} extra",
                    f"portal {commit}\n{digest}", f"portal {commit} ../../other", "portal", "sudo bash"):
        env["SSH_ORIGINAL_COMMAND"] = command
        result = subprocess.run(["bash", str(directory / "deploy-ssh.sh")], env=env, capture_output=True)
        assert result.returncode != 0 and not log.exists(), command

    # Test a temporary copy; production contains no path/privilege override flags.
    portal = root / "portal"
    portal.write_text('#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\n'
                      'Path(os.environ["PORTAL_TEST_CALL"]).write_text(json.dumps([sys.argv[1:],sys.stdin.read()]))\n')
    portal.chmod(0o755)
    timeout = root / "timeout"
    timeout.write_text('#!/usr/bin/env bash\nshift\nexec "$@"\n')
    timeout.chmod(0o755)
    script = (directory / "deploy-release.sh").read_text()
    script = script.replace('export PATH=/usr/sbin:/usr/bin:/sbin:/bin', 'export PATH="' + str(root) + ':$PATH"')
    script = script.replace('$EUID -eq 0', '0 -eq 0').replace('/opt/serverportal/bin/portal', str(portal))
    target = root / "release.sh"
    target.write_text(script)
    for action, cli in (("portal", "register"), ("portal-check", "check-registration")):
        subprocess.run(["bash", str(target), action, commit, digest], env=env, input="{}", text=True, check=True)
        argv, body = json.loads(log.read_text())
        assert argv == [cli, "--app", args.app, "--commit", commit, "--sha256", digest]
        assert body == "{}"
        log.unlink()

print("Restricted deployment protocol passed for", args.app)
