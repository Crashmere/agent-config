<a id="共享-https-与-ip-证书"></a>
# Shared HTTPS and IP Certificates

Five applications share Nginx's public HTTPS port 443 and continue to use /ledger/, /feetable/, /fabricworld/, /recipebox/, and /yuyan/. Let's Encrypt issues the certificate for the server's public IPv4 address; no domain is required. HTTP port 80 serves only ACME challenge files and 308 redirects to the fixed public IP, preserving paths, query parameters, and request methods. API clients must use HTTPS directly; the initial plaintext request is not encrypted.

HTTPS provides transport encryption, and ServerPortal's shared device authentication now protects the five public business applications. Different paths remain same-origin; device cookies use Secure/HttpOnly/SameSite=Strict/Path=/ and share access after authorization, while writes retain origin validation. IP addresses cannot rely on browser HSTS; HSTS is currently not sent, and preload is not enabled.

<a id="配置与维护源"></a>
## Configuration and maintenance sources

| File/service | Responsibility and maintenance source |
| --- | --- |
| /etc/nginx/sites-available/apps | assets/nginx-apps.conf rendered with the public IPv4; shared 80/443 and local check entry points |
| /opt/<app>/config/nginx-location.conf | Each project's deploy directory; preserves Host and overwrites X-Forwarded-Proto with $scheme |
| /etc/letsencrypt/live/apps-ip/ | Certbot-managed certificate chain and private key; excluded from Git/documentation synchronization |
| /var/lib/letsencrypt/.well-known/acme-challenge/ | HTTP-01 challenge-file directory, read-only for Nginx |
| /etc/letsencrypt/renewal-hooks/deploy/reload-nginx | assets/certbot-reload-nginx; runs nginx -t, then reload after successful renewal |
| snap.certbot.renew.timer | Automatic renewal schedule from the official Certbot snap |

TLS terminates at Nginx; Go services continue to listen only on 127.0.0.1:18080–18085. Ledger's service-to-service calls to FabricWorld remain local HTTP. Separate listen directives on 127.0.0.1:80 and [::1]:80 allow existing release scripts to check proxied pages. Selection uses the actual destination address and permits only loopback sources; bypassing public redirects must not depend solely on a spoofable Host header.

Origin validation in Ledger, FeeTable, FabricWorld, and RecipeBox recognizes direct TLS first. For HTTP connections, it accepts only a single X-Forwarded-Proto header with the value https from a loopback peer. Nginx must overwrite this header, and applications must not listen externally. Missing, duplicate, list-valued, or nonlocal proxy headers must not cause a connection to be treated as HTTPS. Yuyan and the portal already forward this header; any origin or protocol decision based on proxy headers must follow the same boundary.

<a id="初次配置与重建"></a>
## Initial configuration and rebuilding

First follow SKILL.md to check authorization, all applications, server instructions, and configuration drift. Keep root-private copies of the original shared server and five locations. The following describes the sequence only; obtain the public IP from trusted SSH configuration and do not commit the actual address.

1. Use software-installation to install the official Certbot snap: snap install certbot --classic. IP webroot support requires Certbot 5.4+; Ubuntu's current 4.0 package is unsuitable. Do not mix apt, pip, and snap installations of Certbot. The snap updates itself.
2. Create /var/lib/letsencrypt/.well-known/acme-challenge (root-owned, directory mode 0755), then first install assets/nginx-apps-bootstrap.conf. It adds only the challenge path and preserves existing HTTP applications. Reload only after nginx -t succeeds, then check the existing applications and external access to the challenge file.
3. Rehearse with staging first; --dry-run does not install a test certificate, and staging certificates must not be served to browsers:

   ```sh
   /snap/bin/certbot certonly --dry-run --non-interactive --agree-tos \
     --register-unsafely-without-email --preferred-profile shortlived \
     --webroot -w /var/lib/letsencrypt --ip-address "$public_ipv4" --cert-name apps-ip
   ```

4. After a successful rehearsal, remove --dry-run to issue the production apps-ip certificate. If no contact email was provided, use the registration-without-email method above; the ACME account can later be updated with an email provided by the user.
5. Test and deploy the origin-validation fixes for the four applications; install the committed locations one at a time. Local releases replace only programs and do not install Nginx configuration. Check local health and proxied pages for every application.
6. Replace __PUBLIC_IPV4__ in assets/nginx-apps.conf with the trusted public IPv4. First add 443 using a temporary configuration that retains HTTP applications; verify public TLS reachability, certificate trust, and all applications before switching to the complete template and enabling 308. The cloud security group must allow TCP 443; UFW being inactive does not prove that cloud rules have been verified.
7. Install assets/certbot-reload-nginx as the deploy hook above (root-owned, 0755). Verify the snap renewal timer is active/enabled; run certbot renew --cert-name apps-ip --dry-run --run-deploy-hooks --no-random-sleep-on-renew and confirm successful validation and reload. Then actually run snap.certbot.renew.service once and check Result=success; skipping issuance outside the renewal window is normal. Add --no-random-sleep-on-renew for manual rehearsals to avoid waiting for a random delay; automatic jobs retain their existing random delay.
8. Complete all acceptance checks in the next section, update conventions/current-state/project docs, then synchronize documentation copies after pushing.

When installing configuration, run nginx -t first and immediately restore that step's original configuration on failure. If syntax is valid but public acceptance checks fail, retain the original HTTP entry point and resolve certificate, network, or application issues before redirecting. Reloading Nginx does not require stopping Go services.

<a id="验收与日常检查"></a>
## Acceptance and routine checks

Latest acceptance: 2026-09-27. All five applications passed external HTTP/2 health checks with a trusted production certificate. Chromium checks at desktop 1360×900 and mobile 375×667 both used TLS 1.3 and a secure context, with no mixed content, script errors, or failed resource requests. Public redirects, query parameters, Host spoofing, local checks, and post-cutover renewal/reload rehearsals passed.

- Check externally without -k: unauthorized navigation redirects to authentication, while API/media/health requests return 401. On an authorized device, access the five health endpoints, home pages, deep links, and scripts/styles. Use a real browser to check secure context, HTTP/2, request failures, and mixed content, including desktop and 375×667.
- Public HTTP home pages, bare paths, deep links, and APIs all return 308 to the fixed HTTPS address, preserving all query parameters. Public requests with Host: localhost/127.0.0.1 must also be unable to access the local HTTP entry point. ACME files remain accessible over HTTP; missing files return 404.
- Same-origin HTTPS requests pass middleware in the four applications. When origin validation changes, use isolated examples to check spoofed nonlocal proxy headers, wrong Origin, wrong protocol, and similar cases. In production, use OPTIONS requests that do not write data to verify origin rejection and acceptance; do not submit test records. Existing service-to-service calls remain on loopback.
- From the server, verify the five direct /healthz endpoints and proxied health/page resources through 127.0.0.1:80; check nginx -t, all units, and configuration hashes.
- inspect.sh checks certificate issuer, validity, a 48-hour expiry threshold, and the renewal timer. IP certificates are valid for about 160 hours; fix automatic renewal failures promptly rather than waiting for expiry. There is currently no external certificate-expiry alert.

```sh
ssh ali '/snap/bin/certbot certificates'
ssh ali 'systemctl list-timers snap.certbot.renew.timer --all --no-pager'
ssh ali 'journalctl -u snap.certbot.renew.service -n 60 --no-pager'
ssh ali '/snap/bin/certbot renew --cert-name apps-ip --dry-run --run-deploy-hooks --no-random-sleep-on-renew'
ssh ali 'bash /opt/server-context/scripts/inspect.sh'
```

Preserve the ACME path on port 80; subsequent authentication rules must not intercept it. Do not edit Certbot's archive/live links or manually copy private keys; Certbot manages public/private key permissions.

<a id="故障与回退"></a>
## Failures and rollback

If certificate renewal fails, first check public HTTP-01 reachability, system time, outbound ACME connectivity, timer/hook logs, and nginx -t. If reload fails, fix the configuration and run the deploy hook. Run renew only when the certificate actually needs updating; do not repeatedly force issuance and risk rate limits.

Roll shared configuration back to the original server saved during this task, reload after nginx -t succeeds, and check the five applications. Origin validation is compatible with the previous HTTP setup, so no program rollback is required. Reverting to plaintext is only a failure-recovery measure; report the actual state and do not delete certificates, data, or backups. When the public IP changes, revalidate and issue a certificate covering the new IP, and update shared configuration and client addresses together.

Official references: [Short-lived and IP certificates with Certbot](https://letsencrypt.org/2026/03/11/shorter-certs-certbot), [160-hour certificates](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability/).
