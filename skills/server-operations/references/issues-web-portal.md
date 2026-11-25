# Common Issues: Portal, Shared Authentication, Nginx, and Web/Mobile UI

Shared solutions for page refresh continuity, Portal APIs/collector, shared auth size limits and cookie renewal, Nginx compression/regex, iPhone home-screen icons/blur, and stale frontend chunks. See the [symptom index](common-issues.md) for all topics.


## A data refresh flashes or resets the page

A page can appear to reload without a document request: replacing loaded content with a skeleton or clearing a gallery before fetching shortens the page, clamps scroll position and remounts images, editors or players. Observed paths include Ledger's filters and pagination, FeeTable's location saves and export filters, FabricWorld's material saves and detail retries, Aura's gallery filters, Curio's collection refreshes and ServerPortal's section navigation. AICalendar's former homepage anchor instead requested a new document. Apply [Page continuity](conventions.md#page-continuity) to every service on `nas`, whether reached through `nas`, `ali` or `vps`: keep valid content mounted while updating, use the client router for same-service navigation, and show bounded progress or transitions. Inspect loading conditionals and state-reset calls as well as `location.reload`, ordinary anchors and native form submission. Verify the affected delayed request with synthetic data; no server runtime, proxy, database or backup change is needed for this frontend correction.


<a id="门户-api-列表与服务不一致"></a>

## Portal API List Does Not Match the Service

This applies to each service's `docs/API.md` and `deploy/portal.json.apis`. A successful portal receipt proves only that the declaration was loaded. The shared validator checks formatting, ownership, and resource boundaries; it does not compare declarations with business routes to verify that APIs really exist or that the list is complete. Documentation that puts multiple APIs in one table cell, extracts only the first table, or treats actions on the same path as separate APIs can leave errors and omissions even when the files synchronize successfully.

Use the current service's route registration and handlers as the authority for methods, internal paths, parameter locations, return values, and authentication notes. Inspect every route file, including endpoints registered in loops. List restricted media variants such as main and thumb separately. In the project API table, put only one method and path on each row; the path field must not contain a query string, enumeration comma, second method, or body action. Put parameters and actions in the description. Compare the portal declaration and API table item by item, add omissions, and remove nonexistent or duplicate entries. Do not extract paths from narrative prose merely by splitting on spaces.

After correcting source files, run the shared `validate-portal.py` and separately compare the entry set and semantics with the implementation; format validation does not replace that review. For documentation-only changes, first confirm that the relevant route code matches the deployed version, then run `make portal` according to the [portal release protocol](portal.md#shared-validation-and-release-protocol) and synchronize documentation with `sync-docs.sh <project-name>`. Verify the hash actually loaded by the portal and the documentation source. Do not restart a business service for a documentation correction or validate the list with production write requests.

There is currently no release gate that automatically compares each business route with its declaration. An agent changing an interface must still perform the review above. If a feature has not yet been deployed, release its declaration with the corresponding program version; do not describe a source-only API as already available in production.


<a id="统一认证误拦大请求"></a>
<a id="shared-authentication-rejects-large-requests"></a>

## Shared Authentication Incorrectly Blocks Large Requests

Symptom: a business request returns 500 while the Nginx error log contains `client intended to send too large body`, `subrequest: "/_portal_device_check"`, and `auth request unexpected status: 413`, with no corresponding request in the application's journal. This was confirmed on 2026-10-01 when RecipeBox uploaded an approximately 4.4 MiB photo and reproduced in isolated Nginx: 1 MiB passed, while one additional byte failed.

Cause: a business location's `client_max_body_size` does not propagate to the authentication subrequest location. `/_portal_device_check` previously inherited Nginx's 1 MiB default. Even with `proxy_pass_request_body off` and an empty `Content-Length`, Nginx checks that limit against the original request length before entering the proxy phase. A 413 from the authentication subrequest is not an authentication result accepted by auth_request, so the client ultimately sees 500.

| Application | Existing ingress and program limits | Impact |
| --- | --- | --- |
| RecipeBox, FabricWorld | Nginx 26 MiB; 25 MiB per image | Normal images over 1 MiB could be blocked incorrectly |
| Yuyan | Nginx 26 MiB; 25 MiB per image; 16 MiB JSON | Large images and large document saves could be blocked incorrectly |
| Ledger | Nginx and JSON both 2 MiB | Requests of 1–2 MiB could not reach business validation |
| FeeTable | Nginx 2 MiB; JSON 64 KiB | Normal business input was unaffected; the service still inherited shared authentication |
| ServerPortal | Nginx and JSON both 1 MiB; performs its own authentication | Does not use this subrequest and was unaffected |

Keep the fix only in `location = /_portal_device_check` in shared `assets/nginx-portal-auth.conf`: set `client_max_body_size 0;` while retaining `internal`, `proxy_pass_request_body off`, the empty `Content-Length`, and cookie validation. Each business location and backend continues to enforce its own size limits. Do not disable limits at the entire http/server layer or bypass authentication for business APIs to work around the failure.

Before applying the change, use all existing locations, an isolated loopback Nginx, and synthetic authentication and business upstreams to verify normal and large requests for every site, missing and forged credentials, requests exceeding business ingress limits, authentication failures, cookie renewal, and the inability to reach the internal authentication path externally. Confirm that the bytes and hashes received by the business upstream match and that the authentication upstream receives no request body; isolated checks need not write real business data. Install to `/etc/nginx/snippets/portal-auth.conf` according to the authorization table, retain the old configuration, and gracefully reload only after `nginx -t` succeeds; restore the old configuration on failure. Then verify health for every inventory application, public icon GET/HEAD requests, unauthenticated page redirects, and API rejection. Source, live server configuration, and the `/opt/server-context` copy must agree. See [current-state](current-state.md#portal-and-shared-authentication) for deployment status.


<a id="统一认证的-cookie-续期"></a>

## Cookie Renewal with Shared Authentication

Business applications use Nginx auth_request to validate devices; a Set-Cookie header from the subrequest does not automatically become a response header on the business request. Shared `assets/nginx-portal-auth.conf` captures that header with auth_request_set and forwards it with add_header Set-Cookie ... always, while the portal renews directly. Anonymous, forged, expired, and revoked credentials must not receive a renewal cookie. Do not weaken the Secure, HttpOnly, SameSite=Strict, or Path=/ attributes.

An application location that adds its own add_header directive overrides inheritance of the entire parent add_header set and may prevent renewal while that application is in continuous use. Explicitly retain the shared renewal header at that layer and check the other shared response headers. Run `scripts/test-cookie-renewal.py --locations /etc/nginx/app-locations --auth <pending-shared-auth-file>` to verify, with an isolated loopback Nginx and synthetic upstream, that valid requests renew exactly once and invalid requests do not renew. Check its focused application cases and add an affected application's case when its renewal behavior changes. Do not temporarily weaken production authentication or print real device credentials in test logs.


<a id="统一认证后-iphone-桌面图标缺失"></a>

## Missing iPhone Home-Screen Icons After Shared Authentication

Diagnosis: the HTTPS resource URLs and existing PNGs were valid, but icons for all five business applications also inherited device authentication. Access logs showed that an iPhone received 200 for the Ledger page icon/manifest but 401 for the separate `icon-192.png` request. Do not assume the system carries the current browser cookie when adding an item to the home screen.

| Application | Icon configuration |
| --- | --- |
| Ledger | 180 px touch icon, 192/512 px manifest icons, and public manifest, with exact GET/HEAD exceptions |
| FeeTable | 180 px touch icon, with Vite hashed paths matched against three brand icon names |
| FabricWorld | 180 px touch icon, `favicon.ico`, and project SVG, with exact GET/HEAD exceptions |
| RecipeBox | 180 px touch icon, `favicon.ico`, and project SVG, with exact GET/HEAD exceptions |
| Yuyan | `static/favicon.svg` and supplemental `static/apple-touch-icon.png`, with exact GET/HEAD exceptions |
| ServerPortal | Public `static/favicon.svg` and supplemental `static/apple-touch-icon.png`, served by the web layer |
| AICalendar | `favicon.svg` and `apple-touch-icon.png`, with exact GET/HEAD exceptions; ingest retains its separate Bearer boundary |
| Aura | `favicon.svg` and `apple-touch-icon.png`, with exact GET/HEAD exceptions |
| Curio | `favicon.svg` and `apple-touch-icon.png`, with exact GET/HEAD exceptions |
| Lilt | `favicon.svg`, 180 px touch icon, 192/512 px manifest icons and public manifest, with exact GET/HEAD exceptions |

Resolution: each business project's own `nginx-location.conf` disables auth_request only for its named brand icons and any declared public manifest, restricted to GET/HEAD. FeeTable matches only the three icon names and their build hashes. Do not expose whole `assets` or `static` trees, user-uploaded media, or APIs. Yuyan and the portal generate opaque 180×180 PNGs from existing SVGs and declare apple-touch-icon in every page head; this does not change their login, cookie, or business-data behavior.

When adding or changing icons, verify the actual HTML href, built path, PNG dimensions, Content-Type, anonymous requests, and version query parameters. Before deployment, run `scripts/test-public-icons.py` (see `--help` for arguments) with an isolated loopback Nginx and synthetic upstream to verify the rules. Keep its registered service-icon cases aligned with the affected routes. The portal web layer serves its own static files, so also confirm that unauthenticated `/portal/api/overview` still returns 401. The final result of adding the site to an iPhone home screen still requires user confirmation and cannot be inferred from server checks.

Each active website deploys its icons and HTML head with its program and maintains its anonymous icon rules. Run `nginx -t` before reloading after a rule change. See current-state for deployment status; future projects should include these icons by default according to conventions.

Every new website must include this configuration in its initial delivery. See the complete [website icon conventions](conventions.md#website-icons-and-home-screen-shortcuts). The general `scripts/check-site-icons.py` discovers icons and manifests from real HTML and verifies anonymous GET/HEAD, media types, file signatures, and PNG dimensions; central lists do not need updates when build hashes change.

For mobile acceptance, first authenticate in the browser and return to the corresponding application page before adding it to the home screen; do not create an application shortcut from the shared login page. Existing shortcuts may retain old icons and need to be added again. If a home-screen application asks for device authorization again, follow the normal login flow without weakening cookie security attributes. See Apple's [Configuring Web Applications](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html) for PNG and page-icon rules.


<a id="web-manifest-returns-a-non-json-content-type"></a>

## Web Manifest Returns a Non-JSON Content Type

Lilt's initial icon acceptance on `nas` returned a valid manifest with HTTP 200 but failed `check-site-icons.py` with `manifest did not return JSON Content-Type`. Without an explicit header, Go's `http.ServeContent` determines the type from extension tables or content sniffing; a `.webmanifest` filename alone does not guarantee the manifest MIME type.

Set the response type in the application's static handler before calling `http.ServeContent`:

```go
if name == "manifest.webmanifest" {
    w.Header().Set("Content-Type", "application/manifest+json; charset=utf-8")
}
http.ServeContent(w, r, name, modTime, content)
```

Lilt was the affected application; Ledger already explicitly maps `.webmanifest` to `application/manifest+json` in its static handler. Verify GET and HEAD return 200 with the declared type on the actual `nas` runtime, then run the shared icon checker through the `ali` and `vps` entrances. Keep the manifest's exact public GET/HEAD exception and inherited business authentication unchanged.


<a id="root-采集进程无法切换应用用户"></a>

## Root Collector Cannot Switch to the Application User

The ServerPortal root collector uses `serverportal` as its non-root primary group so that only the web user can access its Unix socket. On ALI, combining this setup with NoNewPrivileges and RestrictAddressFamilies/LockPersonality left the process CapEff/CapPrm without CAP_SETUID; runuser reported `cannot set user id: Operation not permitted`, and native backups could not start. A successful direct run as root in a terminal does not prove that the operation works inside the unit.

For that historical ALI collector, explicitly configure `AmbientCapabilities=CAP_SETUID` while retaining the other sandbox settings. The current NAS Portal no longer runs backups or switches users; its unit has removed this capability. The historical source remains in ServerPortal Git history. The ALI system was checked for primary group, seccomp properties, and capabilities, and native snapshots were verified under an equivalent sandbox. Native backup units already running as fixed application users require no change. Current NAS backups use independent administrator SSH tooling; see [Agent backup and recovery](backup-recovery.md).


<a id="https-页面能打开但保存返回-403"></a>

## HTTPS Page Loads but Saving Returns 403

TLS terminates at Nginx while application upstreams see loopback HTTP. A check using only `r.TLS` rejects a real browser HTTPS Origin; stripping the explicit port through `$host` also breaks VPS HTTPS 8443. Keep one trusted `X-Forwarded-Proto: https` value and full `$http_host`, and configure the precise NAS/ALI/VPS Origin set in affected applications and Portal. Portal additionally requires a supplied Origin to equal the actual HTTPS Host/port. Check the specific rejected request and installed route source before changing a certificate or authentication rule. [HTTPS](https.md#authentication-and-proxy-trust) owns trust boundaries; do not remove Origin checks or relax CORS to hide a forwarded-header error. Validate affected wrong-origin/protocol/header cases with synthetic requests, not production writes.


<a id="iphone-主屏幕页面顶部发虚"></a>

## Top of an iPhone Home-Screen Page Appears Blurry

User report: after being added to the home screen from iPhone Chrome, Ledger, FeeTable, FabricWorld, and RecipeBox had a blurry area near the time and battery indicators, while Yuyan did not. The key code difference was positioning. Yuyan used `position: sticky; top: 0`; three older services used normal-flow headers. Although Ledger's header sat outside its inner content scroller and looked persistent, its CSS still used `position: relative`, which is not equivalent to a fixed or sticky element recognized by WebKit.

A [WebKit engineer's explanation of top-color extension](https://bugs.webkit.org/show_bug.cgi?id=301756#c2) says the browser extends a solid background from fixed or sticky elements at the viewport edge to avoid a gap above them during scrolling; the iPhone browser UI itself has a softer blur underneath. This provides a mechanism for the observed code difference. Desktop browser validation alone cannot prove that the home-screen appearance is fixed on a particular iPhone.

Resolution: all four services use a solid `sticky; top: 0` header. Ledger retains its internal content scrolling and header dimensions; the other three retain document scrolling, route restoration, and modal scroll locking. Applications receiving new sticky headers reserve top space for controls and anchors, and FabricWorld's desktop photo bar now sticks below navigation. All four viewports also match Yuyan and use the default safe-area layout. The user confirmed on a real device that removing only Ledger's `viewport-fit=cover` did not fix the blur, changing FeeTable to sticky fixed its top area, and then changing only Ledger from relative to `sticky; top: 0` fixed it as well. This confirms the role of explicit sticky positioning in this issue; safe-area settings alone are neither the cause nor the solution. Equivalent FabricWorld and RecipeBox changes have been released and passed browser regression checks but have not received separate real-device confirmation. No Nginx, PWA identity, database, or system-status-bar changes are needed.

Validate at two levels. Desktop Chromium/WebKit checks only the header position, scrolling, navigation, forms, and modals at 320/375 px and desktop sizes; it does not reproduce or prove removal of the native iPhone blur layer. Confirm the final result on a real iPhone by reopening the site from the home screen and scrolling in both directions. Prefer fully closing and reopening that home-screen window to load new HTML/CSS before clearing site data. The pages and Ledger manifest use no-cache, and no Service Worker is registered. Code differences alone cannot establish the native rendering cause for a particular iOS version, and they do not justify adding supposedly universal CSS to "disable system blur."

For safe-area behavior, see WebKit's official [Designing Websites for iPhone X](https://webkit.org/blog/7929/designing-websites-for-iphone-x/): `viewport-fit=cover` extends the page to the screen edges and requires developers to account for safe-area insets. These applications currently use the default layout.


<a id="go-程序返回的-javascript-没有被-nginx-压缩"></a>

## Nginx Does Not Compress JavaScript Returned by a Go Program

This applies to applications that enable compression with `gzip_types` in their application location, currently only Yuyan. Ledger, FeeTable, FabricWorld, and RecipeBox do not set `gzip_types` and inherit nginx.conf's default of compressing only HTML, so they are unaffected. Configure every future Go application that enables `gzip_types` in the same way.

Symptom: CSS and JSON responses include `Content-Encoding: gzip`, but `.js` does not. Yuyan behaved this way from installation, but it was discovered only after the single-page application release on 2026-09-26. The application script transferred 297 KB uncompressed (approximately 100 KB compressed), and the editor chunk transferred approximately 930 KB uncompressed (approximately 290 KB compressed), adding more than one second at the server's approximate 0.5 MB/s downstream rate.

Cause: Go's `http.FileServer` returns `.js` as `text/javascript; charset=utf-8` based on the extension, while `gzip_types` listed only `application/javascript`.

Resolution: include both `text/javascript` and `application/javascript` in `gzip_types` inside the application's own location. Update and push the project's `deploy/nginx-location.conf`, install it to `/opt/<app>/config/nginx-location.conf`, run `nginx -t`, and then run `systemctl reload nginx`; the shared server does not need a change.

Acceptance: request a `.js` resource from the application with `curl -sI -H 'Accept-Encoding: gzip'` and confirm `Content-Encoding: gzip`. After reloading, verify direct and proxied health checks and deep links for all five applications. Yuyan was fixed and verified this way on 2026-09-26.


<a id="nginx-location-regex-quantifiers-require-quoting"></a>

## Nginx Location Regex Quantifiers Require Quoting

On `nas`, Lilt's initial route validation failed with PCRE2 `missing closing parenthesis` because two `location ~` patterns contained unquoted `{32}`. Nginx parses configuration braces before compiling the regular expression. Quote the entire pattern while preserving its regex escapes and quantifier semantics:

```nginx
location ~ "^/lilt/api/tracks/t_[0-9a-f]{32}/(?:stream|download)$" {
    proxy_pass http://127.0.0.1:18089;
}
```

This applies to quantified regex locations in application-owned includes on `nas`, `ali` and `vps`. Lilt uses quoted 32-hex-ID patterns for upload/cover and stream/download routes. Correct the project's route source, validate the candidate in isolated Nginx, then run `nginx -t` on each target before a graceful reload. Retain inherited authentication, cookie renewal and the existing request/media settings.

For Lilt, `scripts/test-public-icons.py --apps lilt --locations <candidate-directory> --auth <shared-auth-file>` checks the quoted routes, exact public brand exceptions, protected uploads/media and page/library cookie renewal with synthetic devices. It starts only private temporary listeners and does not weaken production authentication.


<a id="发布后旧标签页的动态模块加载失败"></a>

## Dynamic Module Loading Fails in a Stale Tab After Deployment

After content-hashed frontend chunks are replaced with a Go program, an already open tab may still request lazy-loaded files from the previous version. This was confirmed in Yuyan on 2026-09-28: the Mermaid core, dependency chunk, and code-reading module all returned 404 in Nginx logs, while the new files referenced by the current manifest existed. This is an invalidated version reference, not a diagram-syntax error.

During diagnosis, first obtain the exact filename from the browser or access log and compare it with the current build manifest and loopback response. A 404 means the file does not exist; a 401 or login page points to shared authentication, and a connection error points to networking. Do not infer a Mermaid syntax problem from dynamic-import error text or expose static directories to bypass authentication and restore script loading.

The page shell must be revalidated while hashed resources may be cached long-term. Clearing only a JavaScript loading Promise cannot clear the browser's recorded failed module; provide an explicit full-page reload action. Editing forms must first wait for uploads and saves to complete, including input added while saving. Preserve the page and draft on failure or conflict instead of reloading immediately. When observing chunk-load failures, retain the original Promise rejection so callers do not believe the module loaded successfully. Handling only the route layer is insufficient because diagram and language modules contain nested imports.

Current scope: Yuyan uses a global prompt and reloads after saving; browser checks exercise real 404s for core and nested chunks. Ledger's lazy-loaded routes already have an error component and the “重新加载页面” (Reload page) action. Current FeeTable, FabricWorld, and RecipeBox sources do not use dynamic imports. ServerPortal uses embedded static scripts without this lazy-loading chain. This change does not alter application release scripts, asset directories, or shared Nginx. When introducing lazy loading later, test stale tabs, loading failures, and recovery of unsaved input together.
