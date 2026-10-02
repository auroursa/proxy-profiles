#!/usr/bin/env python3
"""Read-only checks for this QX profile; no third-party Python dependencies."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import ipaddress
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SELF_PREFIX = "https://raw.githubusercontent.com/froseiun/proxy-profiles/master/"
BUILTINS = {"direct", "proxy", "reject", "reject-tinygif", "reject-drop"}
RULE_TYPES = {
    "host", "host-suffix", "host-keyword", "host-wildcard", "user-agent",
    "ip-cidr", "ip6-cidr", "ip-asn", "geoip", "final",
}
SECTIONS = {
    "general", "dns", "policy", "server_remote", "filter_remote",
    "rewrite_remote", "server_local", "filter_local", "rewrite_local",
    "task_local", "mitm",
}


def active_lines(text):
    return [(n, line.strip()) for n, line in enumerate(text.splitlines(), 1)
            if line.strip() and not line.strip().startswith(("#", ";", "//"))]


def sections(text):
    result, current = {}, None
    for n, line in active_lines(text):
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            if current not in SECTIONS or current in result:
                raise ValueError(f"line {n}: unknown or duplicate section {current}")
            result[current] = []
        elif current is None:
            raise ValueError(f"line {n}: content outside a section")
        else:
            result[current].append((n, line))
    missing = SECTIONS - result.keys()
    if missing:
        raise ValueError(f"missing sections: {sorted(missing)}")
    return result


def resource(line):
    parts = [x.strip() for x in line.split(",")]
    opts = {}
    for part in parts[1:]:
        if "=" not in part:
            raise ValueError(f"invalid resource option: {part}")
        key, value = part.split("=", 1)
        if key in opts:
            raise ValueError(f"duplicate resource option: {key}")
        opts[key] = value
    return parts[0], opts


def filter_rules(text, policies, forced=None, strict_duplicates=True):
    errors, rules, seen = [], [], set()
    for n, line in active_lines(text):
        fields = [x.strip() for x in line.split(",")]
        kind = fields[0].lower()
        expected = 2 if kind == "final" else 3
        if kind not in RULE_TYPES or len(fields) < expected:
            errors.append(f"line {n}: unsupported or malformed filter")
            continue
        policy = forced or fields[expected - 1]
        if policy not in policies | BUILTINS:
            errors.append(f"line {n}: undefined policy {policy}")
        try:
            if kind in {"ip-cidr", "ip6-cidr"}:
                net = ipaddress.ip_network(fields[1], strict=False)
                if net.version != (6 if kind == "ip6-cidr" else 4):
                    raise ValueError("IP address family does not match rule")
            elif kind == "ip-asn" and not fields[1].isdigit():
                raise ValueError("invalid ASN")
        except ValueError as exc:
            errors.append(f"line {n}: {exc}")
        key = (kind, *fields[1:])
        if key in seen and strict_duplicates:
            errors.append(f"line {n}: duplicate filter")
        seen.add(key)
        rules.append((kind, fields[1] if kind != "final" else "", policy))
    if not rules:
        errors.append("no filter rules found")
    return errors, rules


def validate(root):
    """Validate local content, returning errors, remote work items and policies."""
    errors, jobs = [], []
    config = root / "QuantumultX/quantumultx.conf"
    try:
        sec = sections(config.read_text())
    except (ValueError, OSError) as exc:
        return [str(exc)], [], set()
    policies, graph, used = set(), {}, set()
    for n, line in sec["policy"]:
        try:
            kind, body = line.split("=", 1)
            fields = [x.strip() for x in body.split(",")]
            name = fields[0]
            if kind.strip() not in {"static", "available", "round-robin", "dest-hash", "ssid", "url-latency-benchmark"}:
                raise ValueError("unknown policy type")
            if name in policies or name in BUILTINS:
                raise ValueError(f"duplicate/reserved policy {name}")
            policies.add(name)
            graph[name] = [x for x in fields[1:] if "=" not in x]
            for field in fields[1:]:
                if field.startswith(("server-tag-regex=", "resource-tag-regex=")):
                    re.compile(field.split("=", 1)[1])
        except (ValueError, re.error) as exc:
            errors.append(f"policy line {n}: {exc}")
    for name, refs in graph.items():
        for ref in refs:
            if ref not in policies | BUILTINS:
                errors.append(f"{name}: undefined candidate {ref}")
            used.add(ref)
    def cycle(name, stack):
        if name in stack:
            errors.append(f"policy cycle: {' -> '.join(stack + [name])}")
            return
        for ref in graph.get(name, []):
            if ref in policies:
                cycle(ref, stack + [name])
    for name in policies:
        cycle(name, [])
    tags, urls, filter_tags = set(), set(), []
    for section in ("filter_remote", "rewrite_remote"):
        for n, line in sec[section]:
            try:
                url, opts = resource(line)
                tag = opts.get("tag")
                if not tag or tag in tags or url in urls:
                    raise ValueError("missing/duplicate tag or duplicate URL")
                tags.add(tag)
                urls.add(url)
                if opts.get("enabled") not in {"true", "false"}:
                    raise ValueError("explicit enabled=true/false required")
                if section == "filter_remote":
                    filter_tags.append(tag)
                    forced = opts.get("force-policy")
                    if forced not in policies | BUILTINS:
                        raise ValueError(f"undefined force-policy {forced}")
                    used.add(forced)
                    if opts.get("inserted-resource") != "true":
                        raise ValueError("filters must precede local GeoIP fallback")
                if url == "FILTER_LAN":
                    continue
                if urlsplit(url).scheme != "https":
                    raise ValueError("remote resources must use HTTPS")
                if "update-interval" not in opts or opts.get("opt-parser") != "false":
                    raise ValueError("native resources need explicit interval and opt-parser=false")
                int(opts["update-interval"])
                if url.startswith(SELF_PREFIX):
                    path = root / url[len(SELF_PREFIX):]
                    body = path.read_text()
                    if section == "filter_remote":
                        es, rules = filter_rules(body, policies)
                        errors.extend(f"{path.relative_to(root)}: {e}" for e in es)
                        used.update(p for _, _, p in rules)
                    else:
                        if not any(" url " in s for _, s in active_lines(body)):
                            raise ValueError("local rewrite has no rules")
                else:
                    jobs.append((url, section, opts.get("force-policy")))
            except (ValueError, OSError) as exc:
                errors.append(f"{section} line {n}: {exc}")
    expected = ["LAN", "APNs", "AppleIntelligence", "Siri", "OpenAI", "Anthropic", "GitHub", "TechNews",
                "Telegram", "Twitter", "ForeignMedia", "DomesticMedia", "Google", "Microsoft", "Apple", "Global", "China"]
    if filter_tags != expected:
        errors.append("resource order differs from reviewed LAN/service/Global/China order")
    local = "\n".join(line for _, line in sec["filter_local"])
    es, rules = filter_rules(local, policies)
    errors.extend(f"filter_local: {e}" for e in es)
    used.update(p for _, _, p in rules)
    if sum(k == "final" for k, _, _ in rules) != 1 or not rules or rules[-1] != ("final", "", "Final"):
        errors.append("exactly one final, Final must terminate filter_local")
    if not any(k == "geoip" and v == "cn" and p == "China" for k, v, p in rules):
        errors.append("GeoIP CN must use China")
    for name in sorted(policies - used):
        errors.append(f"unused policy {name}")
    for _, line in sec["mitm"]:
        if "=" in line:
            key, value = [x.strip() for x in line.split("=", 1)]
            if key in {"passphrase", "p12"} and value:
                errors.append(f"do not publish MITM {key}")
            if key == "skip_validating_cert" and value != "false":
                errors.append("MITM certificate verification must remain enabled")
    for section in ("server_remote", "server_local"):
        if sec[section]:
            errors.append(f"{section}: keep subscriptions and credentials device-local")
    for _, line in sec["general"]:
        if line.startswith("resource_parser_url"):
            url = line.split("=", 1)[1].strip()
            if not re.search(r"/QuantumultX/[0-9a-f]{40}/Scripts/resource-parser\.js$", url):
                errors.append("pin the resource parser to a reviewed commit")
            jobs.append((url, "script", None))
    return errors, jobs, policies


def fetch(url):
    last = None
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "proxy-profiles-check/1.0"})
            with urlopen(req, timeout=25) as response:
                body = response.read().decode("utf-8-sig")
                content_type = response.headers.get("Content-Type", "")
            if not body.strip() or "text/html" in content_type or body.lstrip().lower().startswith(("<!doctype html", "<html")):
                raise ValueError("empty or HTML response")
            return body
        except (OSError, ValueError) as exc:
            last = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise ValueError(f"fetch failed: {last}")


def check_remote(job, policies):
    url, kind, forced = job
    try:
        body = fetch(url)
        if kind == "filter_remote":
            # Upstream duplicates are tolerated; local duplicates fail offline checks.
            errors, rules = filter_rules(body, policies, forced, strict_duplicates=False)
            if any(k == "final" for k, _, _ in rules):
                errors.append("remote filters must not contain final")
            if errors:
                raise ValueError("; ".join(errors[:5]))
            return [], f"OK {url}: {len(rules)} rules -> {forced}"
        if kind == "rewrite_remote":
            lines = [s for _, s in active_lines(body) if " url " in s]
            if not lines:
                raise ValueError("no rewrite rules found")
            for line in lines:
                re.compile(line.split(" url ", 1)[0])
                for script_url in re.findall(r"https://\S+\.js(?:\?\S*)?", line):
                    script = fetch(script_url)
                    if "$done" not in script:
                        raise ValueError("rewrite script missing $done")
            return [], f"OK {url}: {len(lines)} rewrites (including disabled modules)"
        if "function" not in body and "=>" not in body:
            raise ValueError("resource parser does not look like JavaScript")
        return [], f"OK {url}: script reachable"
    except (ValueError, re.error) as exc:
        return [f"{url}: {exc}"], ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="also check upstream rules, parser and optional rewrite scripts")
    args = parser.parse_args()
    errors, jobs, policies = validate(ROOT)
    if args.online and not errors:
        with ThreadPoolExecutor(max_workers=6) as pool:
            for es, message in pool.map(lambda job: check_remote(job, policies), jobs):
                errors.extend(es)
                if message:
                    print(message)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"PASS: local profile, {len(policies)} policies" + (f", {len(jobs)} upstream resources" if args.online else ""))
    print("Repository-owned resource URLs are validated from the working tree; client behavior is not emulated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
