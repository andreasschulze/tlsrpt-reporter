import unittest
import pytlsrpt.tlsrpt
import os


class MyTestCase(unittest.TestCase):
    def get_fields_from_config_named_tuple(self, config):
        """
        Collect command line options from named tuple
        :param config: The named tuple class containing the command line options
        :return: A sorted list of the command line options, including options added by the argparse module
        """
        fields = list(config._fields)
        # add options from argparse module
        fields.append("help")
        fields.append("config_file")
        fields.sort()
        return fields

    def get_options_from_manpage(self, manpage):
        """
        Collect the command line options that are documented in a manpage
        :param manpage: the name of the man page
        :return: A sorted list of the documented command line options
        """
        documented = []
        for manpage_source in [manpage+".adoc", "manpage-common-options.adoc"]:
            mpf = os.path.join(os.path.dirname(__file__), "..", "doc", "manpages", manpage_source)
            with open(mpf) as mp:
                lines = mp.readlines()
                for line in lines:
                    if line.startswith("*--"):
                        parts = line.partition("*--")
                        parts = parts[2].partition("*")
                        option = parts[0]
                        documented.append(option)
        documented.sort()
        return documented

    def check_manpage_against_options(self, manpage, config):
        """
        Check if the command line options defined in a named tuple match the options documented in a manpage
        :param manpage: Name of the manpage
        :param config: Named tuple class containing the command line parameters
        """
        self.maxDiff = None
        fields = self.get_fields_from_config_named_tuple(config)
        documented = self.get_options_from_manpage(manpage)
        self.assertListEqual(fields, documented)

    def test_receiver_manpage(self):
        """
        Check if manpages match actual command line options for tlsrpt-receiver
        """
        self.check_manpage_against_options("tlsrpt-receiver", pytlsrpt.tlsrpt.ConfigReceiver)

    def test_fetcher_manpage(self):
        """
        Check if manpage matches actual command line options for tlsrpt-fetcher
        """
        self.check_manpage_against_options("tlsrpt-fetcher", pytlsrpt.tlsrpt.ConfigFetcher)

    def test_reporter_manpage(self):
        """
        Check if manpage matches actual command line options for tlsrpt-reporter
        """
        self.check_manpage_against_options("tlsrpt-reporter", pytlsrpt.tlsrpt.ConfigReporter)


if __name__ == '__main__':
    unittest.main()
