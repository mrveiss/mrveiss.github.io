#!/usr/bin/env python3
"""Content checks for the root page.

Every failure mode here is one the Pages build cannot see: Jekyll copies
`index.html` verbatim and never parses it, so a green build proves only that
Jekyll ran. See mrveiss.github.io#2.

Three outcomes, deliberately distinct: PASS, FAIL (the check ran and found a
defect) and UNKNOWN (the check could not run). UNKNOWN is never reported as a
pass -- a guard that cannot look must not claim it looked.
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
TIMEOUT = 15
RETRIES = 2
UA = {"User-Agent": "mrveiss.github.io-link-check"}

PASS, FAIL, UNKNOWN, SKIP = "PASS", "FAIL", "UNKNOWN", "SKIP"
results: list[tuple[str, str, str]] = []


def record(name: str, outcome: str, detail: str = "") -> None:
    results.append((name, outcome, detail))


def check_no_front_matter(text: str) -> None:
    """A leading `---` makes Jekyll wrap the page in the theme layout."""
    first = text.split("\n", 1)[0].strip()
    if first == "---":
        record("no YAML front matter", FAIL,
               "index.html starts with '---', so Jekyll will wrap it in the theme layout")
    else:
        record("no YAML front matter", PASS, f"starts with {first[:30]!r}")


def check_script_balance(text: str) -> None:
    opens = len(re.findall(r"<script[\s>]", text))
    closes = text.count("</script>")
    outcome = PASS if opens == closes else FAIL
    record("script tags balance", outcome, f"{opens} open, {closes} close")


def check_consent_before_gtag(text: str) -> None:
    """Consent Mode defaults set after gtag.js loads are silently ineffective."""
    default = text.find("gtag('consent', 'default'")
    loader = text.find("googletagmanager.com/gtag/js")
    if default == -1 or loader == -1:
        record("consent defaults precede gtag.js", FAIL,
               f"marker missing (default={default}, loader={loader})")
    elif default < loader:
        record("consent defaults precede gtag.js", PASS,
               f"default at byte {default} < loader at {loader}")
    else:
        record("consent defaults precede gtag.js", FAIL,
               f"default at byte {default} comes AFTER loader at {loader}")


def check_storage_keys(text: str) -> None:
    """Both keys are shared with /AutoBot-AI/ on the same origin.

    Renaming either asks a visitor a second time for a decision they made
    once -- consent on `ab-consent`, light/dark on `ab-theme`.
    """
    for key in ("ab-consent", "ab-theme"):
        outcome = PASS if f"'{key}'" in text else FAIL
        record(f"storage key {key} present", outcome,
               "shared with /AutoBot-AI/ on the same origin")


def check_og_image_absolute(text: str) -> str | None:
    m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', text)
    if not m:
        record("og:image present", FAIL, "no og:image meta tag")
        return None
    url = m.group(1)
    if not url.startswith(("http://", "https://")):
        record("og:image is absolute", FAIL,
               f"relative og:image renders nothing on every platform: {url}")
        return None
    record("og:image is absolute", PASS, url)

    # Before the card existed this pointed at /AutoBot-AI/screenshots/01-chat.png --
    # a product screenshot standing in for a social card. It rendered *something*,
    # so it never looked broken, which is why it survived. A screenshot at whatever
    # aspect ratio it happens to be is not a 2:1 card, and twitter:card is
    # summary_large_image, which crops hard.
    if "/assets/social-card.png" in url:
        record("og:image is the social card", PASS, "assets/social-card.png")
    else:
        record("og:image is the social card", FAIL,
               f"points at {url}, not the generated card at /assets/social-card.png — "
               "a screenshot here renders but is not a card")
    return url


def probe(url: str) -> tuple[str, str]:
    """Return (outcome, detail). A network failure is UNKNOWN, never PASS."""
    last = ""
    for attempt in range(RETRIES + 1):
        for method in ("HEAD", "GET"):
            req = urllib.request.Request(url, method=method, headers=UA)
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    return (PASS, f"HTTP {r.status}") if r.status < 400 else (FAIL, f"HTTP {r.status}")
            except urllib.error.HTTPError as e:
                if e.code == 405 and method == "HEAD":
                    continue
                return FAIL, f"HTTP {e.code}"
            except Exception as e:  # noqa: BLE001 - transport failures are UNKNOWN
                last = f"{type(e).__name__}: {e}"
    return UNKNOWN, f"could not check after {RETRIES + 1} attempts ({last})"


def preconnect_origins(text: str) -> set[str]:
    """Origins named only for connection warm-up are not documents.

    `<link rel="preconnect" href="https://fonts.gstatic.com">` names an origin to
    open a socket to. Requesting it as a page legitimately 404s, so probing it
    reports a defect that does not exist -- which is how a link checker teaches
    people to ignore it.
    """
    tags = re.findall(r"<link\b[^>]*>", text, flags=re.I)
    warm = ("preconnect", "dns-prefetch")
    return {
        m.group(1).rstrip("/")
        for tag in tags
        if any(f'rel="{w}"' in tag.lower() or f"rel='{w}'" in tag.lower() for w in warm)
        for m in [re.search(r'href="([^"]+)"', tag)]
        if m
    }


def collect_urls(files: list[Path]) -> list[str]:
    urls: set[str] = set()
    for f in files:
        if f.exists():
            urls.update(re.findall(r'https?://[^\s"\'<>)\]]+', f.read_text(encoding="utf-8")))
    return sorted(u.rstrip(".,;") for u in urls)


SITE_ORIGIN = "https://mrveiss.github.io/"


def local_file_for(url: str) -> Path | None:
    """Map a site URL to a file this repository ships, if it ships one.

    An asset added in the same commit that references it does not exist at the
    origin yet, so fetching it 404s and the introducing PR fails its own gate. The
    file is the thing under review; the deployed copy is downstream of it.

    Only paths this repository actually contains resolve here — `/AutoBot-AI/...`
    is a different repository and still gets fetched.
    """
    if not url.startswith(SITE_ORIGIN):
        return None
    rel = url[len(SITE_ORIGIN):].split("#")[0].split("?")[0]
    if not rel:
        return None
    candidate = ROOT / rel
    return candidate if candidate.is_file() else None


def check_links(urls: list[str], skip: set[str]) -> None:
    for url in urls:
        if url.rstrip("/") in skip:
            record(f"link {url}", SKIP, "preconnect/dns-prefetch origin, not a document")
            continue
        local = local_file_for(url)
        if local is not None:
            record(f"link {url}", PASS,
                   f"ships in this repo: {local.relative_to(ROOT)}, {local.stat().st_size} bytes")
            continue
        outcome, detail = probe(url)
        record(f"link {url}", outcome, detail)


def main() -> int:
    if not PAGE.exists():
        print(f"UNKNOWN: {PAGE} does not exist -- nothing was checked", file=sys.stderr)
        return 2
    text = PAGE.read_text(encoding="utf-8")

    check_no_front_matter(text)
    check_script_balance(text)
    check_consent_before_gtag(text)
    check_storage_keys(text)
    og = check_og_image_absolute(text)

    urls = collect_urls([PAGE, ROOT / "robots.txt", ROOT / "llms.txt"])
    if og and og not in urls:
        urls.append(og)
    check_links(urls, preconnect_origins(text))

    width = max(len(n) for n, _, _ in results)
    for name, outcome, detail in results:
        print(f"{outcome:<7} {name:<{width}}  {detail}")

    failed = [r for r in results if r[1] == FAIL]
    unknown = [r for r in results if r[1] == UNKNOWN]
    skipped = [r for r in results if r[1] == SKIP]
    passed = len(results) - len(failed) - len(unknown) - len(skipped)
    print(f"\n{len(results)} checks: {passed} pass, {len(failed)} fail, "
          f"{len(unknown)} could not be checked, {len(skipped)} not applicable")

    for name, _, detail in failed:
        print(f"::error title=Check failed::{name}: {detail}")
    for name, _, detail in unknown:
        print(f"::error title=Could not check::{name}: {detail} "
              "-- reported as could-not-check, not as a pass")

    if failed:
        return 1
    return 3 if unknown else 0


if __name__ == "__main__":
    sys.exit(main())
