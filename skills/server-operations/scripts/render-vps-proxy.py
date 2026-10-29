#!/usr/bin/env python3
"""Create private vps proxy credentials and import files using an official sing-box binary."""

import argparse
import json
import os
from pathlib import Path
import secrets
from string import Template
import subprocess
from urllib.parse import quote, urlencode
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sing-box", required=True, type=Path)
    parser.add_argument("--server", required=True, help="Private public address from ssh -G vps")
    parser.add_argument("--server-name", default="www.nvidia.com")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    # Refuse regeneration in place: rotating shared credentials affects every device.
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace {args.output}")
    key_output = subprocess.check_output([str(args.sing_box), "generate", "reality-keypair"], text=True)
    keys = dict(line.split(":", 1) for line in key_output.splitlines() if ":" in line)
    keys = {key.strip(): value.strip() for key, value in keys.items()}
    private_key = keys["PrivateKey"]
    public_key = keys.get("PublicKey")
    if not public_key:
        raise ValueError("sing-box did not return the REALITY public key")
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    identity = str(uuid.uuid4())
    short_id = secrets.token_hex(8)
    template = Path(__file__).resolve().parent.parent / "assets/vps/sing-box-config.json.template"
    server = json.loads(Template(template.read_text()).substitute(
        UUID=identity, SERVER_NAME=args.server_name,
        PRIVATE_KEY=private_key, SHORT_ID=short_id,
    ))
    (args.output / "server.json").write_text(json.dumps(server, indent=2) + "\n")
    params = urlencode({
        "encryption": "none", "security": "reality", "sni": args.server_name,
        "fp": "chrome", "pbk": public_key, "sid": short_id,
        "type": "tcp", "flow": "xtls-rprx-vision", "spx": "/",
    })
    address = f"[{args.server}]" if ":" in args.server else args.server
    uri = f"vless://{identity}@{address}:443?{params}#{quote('Personal VPS')}"
    (args.output / "node.txt").write_text(uri + "\n")
    client = {
        "log": {"level": "warn"},
        "inbounds": [{"listen": "127.0.0.1", "listen_port": 18081, "type": "socks"}],
        "outbounds": [{
            "type": "vless", "server": args.server, "server_port": 443,
            "uuid": identity, "flow": "xtls-rprx-vision",
            "tls": {
                "enabled": True, "server_name": args.server_name,
                "utls": {"enabled": True, "fingerprint": "chrome"},
                "reality": {"enabled": True, "public_key": public_key, "short_id": short_id},
            },
        }],
    }
    (args.output / "verify-client.json").write_text(json.dumps(client, indent=2) + "\n")
    print(f"Private configuration created in {args.output}; credentials not printed.")


if __name__ == "__main__":
    main()
