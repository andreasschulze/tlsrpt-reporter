#
#    Copyright (C) 2024-2025 sys4 AG
#    Author Boris Lohner bl@sys4.de
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#

import unittest
from tlsrpt_reporter.utility import normalize_domain_name

class MyTestCase(unittest.TestCase):
    """
    Test utility function normalize_domain_name
    """
    def test_nochange(self):
        for d in ["", ".", "example.com"]:
            self.assertEqual(d,  normalize_domain_name(d))

    def test_uppercase(self):
        for d in ["name.tld", "Name.tld", "NAME.tld", "name.Tld", "name.TLD", "Name.Tld", "NAME.TLD"]:
            self.assertEqual("name.tld", normalize_domain_name(d))

    def test_trailing_dot(self):
        self.assertEqual(normalize_domain_name("name.tld"), "name.tld")
        self.assertEqual(normalize_domain_name("name.tld."), "name.tld")  # this is the only change to happen
        self.assertEqual(normalize_domain_name("name.tld.."), "name.tld..")
        self.assertEqual(normalize_domain_name("name.tld..."), "name.tld...")

    def test_all(self):
        for d in ["name.tld.", "Name.tld.", "NAME.tld.", "name.Tld.", "name.TLD.", "Name.Tld.", "NAME.TLD."]:
            self.assertEqual("name.tld", normalize_domain_name(d))


if __name__ == '__main__':
    unittest.main()
