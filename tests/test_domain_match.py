import unittest

from tlsrpt_reporter.mapping import _domain_match


class MyTestCase(unittest.TestCase):
    def test_domain_match_catch_all(self):
        for d in ["example.com", "example.com.", "com", ""]:
            self.assertTrue(_domain_match(d,"."))

    def test_domain_match_empty_pattern(self):
        for d in ["example.com", "example.com.", "com"]:
            self.assertFalse(_domain_match(d, ""))

    def test_domain_exact_match(self):
        for d in ["example.com", "example.com.", "com"]:
            pattern = "com"
            self.assertEqual(_domain_match(d, pattern), d == pattern)

    def test_domain_subdomain_match(self):
        tests = {"example.com": True,
                 "example.com.": True,
                 "example.com..": False,
                 "com": False,  # pure subdomain match
                 "com.": False,
                 "example.net": False,
                 "example.com.net": False,
                 "example.net.com": True,
                 }
        pattern = ".com"
        for d in tests.keys():
            self.assertEqual(_domain_match(d, pattern), tests[d])


if __name__ == '__main__':
    unittest.main()
