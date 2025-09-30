import io
import unittest
import logging
from tlsrpt_reporter.mapping import DestinationMap, MapActionAccept, MapActionDiscard, MapActionAppend, \
    MapActionReplace, InvalidDestinationScheme, MapParseError


class MyTestCase(unittest.TestCase):
    def setUp(self):
        line = 0
        self.dm=DestinationMap()
        line += 1
        self.dm.add_rua_mapping("accept.example.com",MapActionAccept(), line)
        line += 1
        self.dm.add_rua_mapping("replace.example.com",MapActionReplace(["https://replaced.org",]), line)
        line += 1
        self.dm.add_rua_mapping("discard.example.com",MapActionDiscard(), line)
        line += 1
        self.dm.add_rua_mapping("append.example.com",MapActionAppend(["https://appended.org",]), line)
        line += 1
        self.dm.add_rua_mapping("example.com",MapActionReplace(["directory:/completely.replaced",]), line)
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        #self.logger.addHandler(logging.StreamHandler(sys.stdout))

    def test_ruamap(self):
        """
        Test for correct rua map transformations
        """
        ruas = ["mailto:report@example.net", "https://report.example.net"]
        testcases = [{"dom":"accept.example.com", "rua":ruas},
                     {"dom": "replace.example.com", "rua": ["https://replaced.org",]},
                     {"dom": "discard.example.com", "rua": []},
                     {"dom": "append.example.com", "rua": ["mailto:report@example.net", "https://report.example.net", "https://appended.org"]},
                     {"dom": "example.com", "rua": ["directory:/completely.replaced",]},
                     {"dom": "example.org", "rua": ruas},
                     ]
        i = 0
        for tc in testcases:
            i += 1
            with self.subTest(i=i):
                testrua = self.dm.map_destination(tc["dom"], ruas, self.logger)
                self.assertListEqual(tc["rua"], testrua)

    def test_pre_flight_check_valid(self):
        """
        Test valid report destinations that must pass pre_flight_check
        """
        valid_ruas = [["mailto:report@example.net", "https://report.example.net"],
                      ["mailto:report@example.net"],
                      ["https://report.example.net"],
                      [],
                      ];
        for rua in valid_ruas:
            is_valid = self.dm.pre_flight_check(rua)
            self.assertTrue(is_valid)

    def test_pre_flight_check_invalid(self):
        """
        Test invalid report destinations that must be caught in pre_flight_check
        """
        invalid_ruas = [["mailto:report@example.net", "https://report.example.net", "directory:/hacking/attempt"],
                        ["directory:/hacking/attempt"],
                        ["http://just.plain.http/is/invalid"],
                        ["mail:typo@not.valid"],
                        ["not.even.a.scheme"],
                        [""],
                        ];
        for rua in invalid_ruas:
            with self.assertRaises(InvalidDestinationScheme):
                is_valid = self.dm.pre_flight_check(rua)

    def test_parse_error_match_type(self):
        """
        Test for proper exception to b thrown for various parse errors
        """
        tests = {".subdomain.example" : "rua map line 1: Missing action",
                 ".subdomain.example ": "rua map line 1: Missing action",
                 ".subdomain.example WRONGACTION": "rua map line 1: Unknown action WRONGACTION",
                 ".subdomain.example ACCEPT unexpected_parameter":
                     "rua map line 1: Map action ACCEPT does not accept additional parameters",
                 ".subdomain.example DISCARD unexpected_parameter":
                     "rua map line 1: Map action DISCARD does not accept additional parameters",
                 ".subdomain.example APPEND": "rua map line 1: Map action APPEND needs additional parameters",
                 ".subdomain.example REPLACE": "rua map line 1: Map action REPLACE needs additional parameters",
                 ".subdomain.example REGEXP":
                     "rua map line 1: Map action REGEXP needs 2 additional parameters but got 0",
                 ".subdomain.example REGEXP onlyone":
                     "rua map line 1: Map action REGEXP needs 2 additional parameters but got 1",
                 ".subdomain.example REGEXP too many parameters":
                     "rua map line 1: Map action REGEXP needs 2 additional parameters but got 3",
                 "wrongtype:.subdomain.example ACCEPT": "rua map line 1: Unsupported match type 'wrongtype'",
                 }
        for cfgline in tests:
            description = tests[cfgline]
            dm = DestinationMap()
            mockfile = io.StringIO(cfgline)
            with self.assertRaises(MapParseError) as pe:
                dm.read_from_ios(mockfile, None, None)
            self.assertEqual(description, str(pe.exception))


if __name__ == '__main__':
    unittest.main()
