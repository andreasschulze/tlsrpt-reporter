import unittest
import os
import sys

from pytlsrpt.tlsrpt import ConfigReceiver, ConfigReporter, options_from_cmd_cfg_env, options_receiver, options_reporter,TLSRPTReceiver, TLSRPTReporter, pospars_fetcher

class MyTestCase(unittest.TestCase):
    """
    Test usability of example config file
    """

    def setUp(self):
        self.example_filename = os.path.join(os.path.dirname(__file__), "..", "pytlsrpt" , "example.cfg")
        sys.argv.append("--config_file")
        sys.argv.append(self.example_filename)

    def test_receiver_config(self):
        (configvars, params) = options_from_cmd_cfg_env(options_receiver, TLSRPTReceiver.DEFAULT_CONFIG_FILE,
                                                        TLSRPTReceiver.CONFIG_SECTION,
                                                        TLSRPTReceiver.ENVIRONMENT_PREFIX,
                                                        {})
        config = ConfigReceiver(**configvars)
        self.assertEqual(config.log_level, "debug")
        self.assertEqual(config.receiver_logfilename, "/tmp/tlsrpt-receiver.log")

    def test_fetcher_config(self):
        (configvars, params) = options_from_cmd_cfg_env(options_receiver, TLSRPTReceiver.DEFAULT_CONFIG_FILE,
                                                        TLSRPTReceiver.CONFIG_SECTION,
                                                        TLSRPTReceiver.ENVIRONMENT_PREFIX,
                                                        pospars_fetcher)
        config = ConfigReceiver(**configvars)
        self.assertEqual(config.log_level, "debug")

    def test_reporter_config(self):
        (configvars, params) = options_from_cmd_cfg_env(options_reporter, TLSRPTReporter.DEFAULT_CONFIG_FILE,
                                                        TLSRPTReporter.CONFIG_SECTION,
                                                        TLSRPTReporter.ENVIRONMENT_PREFIX,
                                                        {})
        config = ConfigReporter(**configvars)
        self.assertEqual(config.log_level, "debug")
        self.assertEqual(config.reporter_logfilename, "/tmp/tlsrpt-reporter.log")


if __name__ == '__main__':
    unittest.main()
