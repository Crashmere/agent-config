<a id="https-与-ip-证书"></a>
# HTTPS and IP Certificates

The shared application entrances are NAS LAN HTTPS 443, ALI public HTTPS 443, and VPS public HTTPS 8443. Each gateway routes the existing application paths to the same NAS instances. VPS's existing sing-box REALITY/Vision service retains TCP 443; it is not an HTTPS website or a replacement for a public web certificate. [Current-state](current-state.md) records activation; [NAS migration](nas-migration.md) owns the cross-host contract.

## Server and Certificate Sources

| Source | Installed resource / role |
| --- | --- |
| `assets/nginx-gateway.conf` | Public-IP server rendered with `__PUBLIC_IPV4__` and `__HTTPS_PORT__`: ALI 443, VPS 8443; public HTTP-01/308 on 80 and separate loopback inspector |
| `assets/gateway/nginx-main.conf`, `nginx-bootstrap.conf` | AlmaLinux main/include layout and temporary HTTP-01-only server; bootstrap's other paths return 503 until authenticated activation |
| `assets/nginx-nas.conf` | NAS authenticated LAN 443 rendered with `__LAN_IPV4__`; loopback-only HTTP inspector |
| Each application's `deploy/nginx-location.conf` | Active hosts' `/etc/nginx/app-locations`; preserve path/streaming contract and full forwarded Host/port |
| `assets/nginx-portal-auth.conf` | Device-authentication include for every user-facing HTTPS server; no public inspection exception |
| `/etc/letsencrypt/live/apps-ip` | Gateway-specific Certbot chain/private key; never Git or documentation sync |
| `/var/lib/letsencrypt/.well-known/acme-challenge` | Gateway HTTP-01 files, readable by Nginx without Portal authentication |
| `assets/certbot-reload-nginx` | Certbot deploy hook: syntax validation before Nginx reload |
| `assets/gateway/certbot-renew.service`, `.timer` | VPS `certbot-renew.service/timer`, using isolated `/opt/certbot/.venv` |
| `assets/nas/renew-lan-tls.sh`, `nas-lan-tls.service/timer` | NAS CA-signed leaf issuance/renewal at `/etc/nas-ca` |
| ALI `snap.certbot.renew.timer` | Existing official snap renewal while the ALI public entrance remains active |

Distribution-specific enabled Nginx paths differ: Ubuntu uses its sites configuration, while AlmaLinux uses its installed include layout. Do not copy directory/package/version assumptions between hosts. TLS terminates at the entrance; application ports 18080-18087 remain loopback HTTP. Gateway reverse SSH is encrypted; Ledger-to-FabricWorld traffic remains local.

## Public IPv4 Certificates

ALI and VPS each need a certificate for their own public IPv4; copying ALI's certificate cannot cover VPS's different address. Let's Encrypt short-lived IP certificates last approximately 160 hours, so automated renewal is required. Gateway port 80 serves HTTP-01 and returns 308 to the fixed HTTPS URL for other requests, preserving paths, queries, and methods. VPS redirects include `:8443`; clients should use HTTPS directly rather than send an initial plaintext API request.

Use `software-installation` for installation and `python-environment` when selecting or maintaining VPS's isolated Python environment. IP webroot support requires Certbot 5.4+. ALI keeps its official Certbot snap; VPS uses the verified Certbot package in `/opt/certbot/.venv` with AlmaLinux Python 3.12 rather than a global pip install or Ubuntu snap/APT recipe. Signed DNF security updates do not update an isolated Certbot package automatically.

Bootstrap only the HTTP challenge listener until a production certificate exists; do not make Nginx reference missing TLS files or send a staging certificate to user devices. Rehearse issuance through the staging/dry-run flow, then issue the production gateway certificate. Verify actual provider/firewall port 80 reachability and preserve the proxy's existing port 443 rule.

A VPS issuance command uses `/opt/certbot/.venv/bin/certbot`; the ALI equivalent remains `/snap/bin/certbot`:

```sh
certbot certonly --dry-run --non-interactive --agree-tos \
  --register-unsafely-without-email --preferred-profile shortlived \
  --webroot -w /var/lib/letsencrypt --ip-address "$public_ipv4" --cert-name apps-ip
```

Install the deploy hook, validate Nginx, and test renewal with `--dry-run --run-deploy-hooks --no-random-sleep-on-renew`. VPS checks renewal at 03:00 and 15:00 with up to one hour of randomized delay; ALI retains the snap schedule. Manual dry-runs do not install a production certificate or replace proof of a working timer.

## NAS Local CA

The NAS private CA is `/etc/nas-ca/ca.crt` and `ca.key`; its leaf certificate/key are `server.crt` and `server.key`. The selected IPv4 is recorded in `/etc/nas-ca/lan-ip` and appears in the leaf SAN. Devices receive only `ca.crt` and use normal OS trust, including iOS full trust where required. Keep private keys server-side with restricted permissions and in manual recovery materials.

The source renews a 90-day RSA leaf when it has no more than 30 days remaining or does not match the configured IPv4. `nas-lan-tls.timer` checks daily with a randomized delay up to 30 minutes. Issuance verifies the CA chain; an active Nginx is syntax-tested before reload, with the previous leaf pair restored on syntax failure. Restoring the same CA preserves device trust; replacing/loss of the signing key requires a separate trust migration.

The user currently retains DHCP and has deferred address reservation. A changed LAN address requires updating the trusted connection, `lan-ip`, Nginx/Origin settings, and shortcuts together, then renewing the matching leaf. The timer does not infer a new address from DHCP or update client bookmarks. Public certificates cannot cover private NAS IPs, and gateway certificates cannot replace this local-CA trust.

## Authentication and Proxy Trust

Portal protects every user-facing HTTPS entrance. Browser Origins include IP and explicit port; configure NAS, ALI, and VPS `:8443` precisely. Cookies remain Secure/HttpOnly/SameSite and host-bound, not isolated by port. Browser trust does not authenticate a device, and a trusted home network does not create an unauthenticated LAN entrance.

Nginx must overwrite `X-Forwarded-Proto` with one correct value and use `$http_host` so VPS's explicit port survives. Applications accepting forwarded protocol trust only the intended loopback hop; duplicate/list-valued/nonlocal spoofed headers must not create HTTPS trust. Portal also checks that a supplied Origin equals the HTTPS request Host/port. Exact brand assets, login resources, ACME, and AICalendar's separate Bearer ingest keep their registered exceptions.

Loopback HTTP on each active host is selected by actual destination address, not a client-controlled Host. Agent inspection uses trusted SSH to that listener; public requests with `Host: localhost` must not enter it. IP-literal entrances do not use HSTS/preload, so do not describe an HTTP redirect as protection of the initial plaintext request.

## Acceptance and Failures

Verify Nginx syntax and actual listener ownership first, then certificate chain/IP/expiry, public HTTP-01, fixed redirects, unauthenticated API/page rejection, and the affected path/header/streaming contracts. Public checks do not use `-k`; LAN checks use the CA root or an OS-trusted device. Browser/Aura trust and each IP's initial Portal login require actual-device acceptance, not a CLI claim. Keep checks focused on the entrances and behavior that changed.

Renewal failures require checking HTTP-01 reachability, time, ACME outbound access, timer/hook logs, and Nginx syntax. Fix the actual cause before forcing issuance; repeated forced renewal risks CA rate limits. Gateway/tunnel failure returns unavailable or denies protected traffic, never enables old ALI databases or bypasses authentication. Preserve valid certificates/private keys and data while restoring the last reviewed shared configuration; changing a public IP requires a new matching certificate and client settings.

Official references: [Certbot IP certificates](https://letsencrypt.org/2026/03/11/shorter-certs-certbot), [160-hour certificates](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability/).
