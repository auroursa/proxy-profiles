import importlib.util
from pathlib import Path
import re
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_profiles", ROOT / "scripts/check_profiles.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ProfileTests(unittest.TestCase):
    def test_current_profile(self):
        errors, _, _ = checker.validate(ROOT)
        self.assertEqual(errors, [])

    def mutated_errors(self, before, after):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT / "QuantumultX", root / "QuantumultX")
            profile = root / "QuantumultX/quantumultx.conf"
            text = profile.read_text()
            self.assertIn(before, text)
            profile.write_text(text.replace(before, after, 1))
            errors, _, _ = checker.validate(root)
            return errors

    def test_undefined_force_policy(self):
        errors = self.mutated_errors("force-policy=OpenAI", "force-policy=Missing")
        self.assertTrue(any("undefined force-policy Missing" in e for e in errors))

    def test_invalid_node_selection_regex(self):
        errors = self.mutated_errors("server-tag-regex=^.+$", "server-tag-regex=[")
        self.assertTrue(any("policy line" in e for e in errors))

    def test_cycle(self):
        errors = self.mutated_errors("static = Manual, proxy,", "static = Manual, Final,")
        self.assertTrue(any("policy cycle" in e for e in errors))

    def test_geoip_cannot_shadow_services(self):
        errors = self.mutated_errors("inserted-resource=true", "inserted-resource=false")
        self.assertTrue(any("precede local GeoIP" in e for e in errors))

    def test_catchall_is_unique_and_last(self):
        errors = self.mutated_errors("final, Final", "final, Final\nhost, example.com, direct")
        self.assertTrue(any("terminate filter_local" in e for e in errors))
        errors = self.mutated_errors("final, Final", "final, proxy\nfinal, Final")
        self.assertTrue(any("exactly one final" in e for e in errors))

    def test_ca_must_not_be_published(self):
        errors = self.mutated_errors("passphrase =\n", "passphrase = test-secret\n")
        self.assertTrue(any("do not publish MITM" in e for e in errors))

    def test_duplicate_rule_and_ip_family(self):
        errors, _ = checker.filter_rules("host, a.test, direct\nhost, a.test, direct", set())
        self.assertTrue(any("duplicate" in e for e in errors))
        errors, _ = checker.filter_rules("ip6-cidr, 10.0.0.0/8, direct", set())
        self.assertTrue(any("family" in e for e in errors))

    def test_service_scope(self):
        _, github = checker.filter_rules((ROOT / "QuantumultX/filter/github.txt").read_text(), {"GitHub"})
        domains = {value for _, value, _ in github}
        self.assertTrue({"githubusercontent.com", "githubassets.com", "ghcr.io"} <= domains)
        self.assertNotIn("npmjs.org", domains)
        _, ai = checker.filter_rules((ROOT / "QuantumultX/filter/apple-intelligence.txt").read_text(), {"AppleIntelligence"})
        self.assertNotIn("apps.mzstatic.com", {v for _, v, _ in ai})
        _, openai = checker.filter_rules((ROOT / "QuantumultX/filter/openai.txt").read_text(), {"OpenAI"})
        self.assertFalse(any(k == "ip-asn" or v in {"stripe.com", "sentry.io", "auth0.com"} for k, v, _ in openai))
        _, anthropic = checker.filter_rules((ROOT / "QuantumultX/filter/anthropic.txt").read_text(), {"Anthropic"})
        self.assertTrue({"anthropic.com", "claude.ai", "claude.com", "claudeusercontent.com",
                         "claudemcpclient.com", "claudemcpcontent.com"} <= {v for _, v, _ in anthropic})
        self.assertFalse(any(k == "ip-asn" or v in {"b-cdn.net", "usefathom.com"} for k, v, _ in anthropic))


class RedirectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = (ROOT / "QuantumultX/rewrite-rules.conf").read_text()
        rules = [line for _, line in checker.active_lines(text) if " url " in line]
        assert len(rules) == 1
        pattern, action = rules[0].split(" url ", 1)
        status, cls.target = action.split(" ", 1)
        assert status == "302"
        cls.pattern = re.compile(pattern)
        cls.hostnames = text.split("hostname = ", 1)[1].splitlines()[0].split(", ")

    def redirect(self, url):
        match = self.pattern.fullmatch(url)
        if not match:
            return None
        # QX replacement captures use $1; validate the intended expansion.
        return re.sub(r"\$(\d+)", lambda m: match.group(int(m[1])) or "", self.target)

    def test_path_and_query_preserved(self):
        for host in self.hostnames:
            with self.subTest(host=host):
                self.assertEqual(self.redirect(f"https://{host}/search?q=qx%20rules&hl=zh-CN"),
                                 "https://www.google.com/search?q=qx%20rules&hl=zh-CN")
        self.assertEqual(self.redirect("http://g.cn/"), "https://www.google.com/")
        self.assertEqual(self.redirect("https://google.cn?q=test"), "https://www.google.com?q=test")
        self.assertEqual(self.redirect("https://google.cn"), "https://www.google.com")

    def test_similar_hosts_and_unrelated_urls_unchanged(self):
        for url in ["https://google.cn.evil.test/search", "https://wwwXgoogle.cn/",
                    "https://google.cnx/", "https://mail.google.cn/",
                    "https://www.google.com/search", "https://google.cn@evil.test/",
                    "ftp://google.cn/", "https://example.com/?next=https://google.cn/"]:
            with self.subTest(url=url):
                self.assertIsNone(self.redirect(url))


if __name__ == "__main__":
    unittest.main()
