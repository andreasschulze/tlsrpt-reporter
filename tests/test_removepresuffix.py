import unittest
from tlsrpt_reporter import utility

class MyTestCase(unittest.TestCase):
    def do_with_prefix(self, x):
        tests = {"Nothing":"Nothing",
                 "No" + x +" thing": "No" + x +" thing",
                 x + "Nothing": "Nothing",
                 x + " Nothing": " Nothing",
                 x + x + "Nothing": x + "Nothing",
                 x : "",
                 "": "",
                 x + x : x,
                 x + "öüßÄÖÜ" : "öüßÄÖÜ",
                 "Nothing" + x: "Nothing" + x,
                 "Nothing " + x: "Nothing " + x,
                 "Nothing " + x + x: "Nothing " + x + x,
                 "öüßÄÖÜ" + x: "öüßÄÖÜ" + x
        }
        for k in tests:
            self.assertEqual(utility.remove_prefix(k,x), tests[k])

    def test_prefix(self):
        for pfx in ["a", "abcdefgh", "Nothings", "ä", "äöü", " ", "", "."]:
            self.do_with_prefix(pfx)


    def do_with_suffix(self, x):
        tests = {"Nothing": "Nothing",
                 "No" + x + " thing": "No" + x + " thing",
                 x + "Nothing": x + "Nothing",
                 x + " Nothing": x + " Nothing",
                 x + x + "Nothing": x + x + "Nothing",
                 x: "",
                 "": "",
                 x + x: x,
                 x + "äöüßÄÖÜ": x + "äöüßÄÖÜ",
                 "Nothing" + x: "Nothing",
                 "Nothing " + x: "Nothing ",
                 "Nothing "+ x + x: "Nothing " + x,
                 "äöüßÄÖÜ" + x: "äöüßÄÖÜ"
                 }
        for k in tests:
            self.assertEqual(utility.remove_suffix(k, x), tests[k])


    def test_suffix(self):
        for pfx in ["a", "abcdefgh", "Nothings", "ä", "äöü", " ", "", "."]:
            self.do_with_suffix(pfx)


if __name__ == '__main__':
    unittest.main()
