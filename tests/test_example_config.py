import unittest

from pytlsrpt.tlsrpt import ConfigReceiver, ConfigReporter, options_from_cmd_cfg_env, options_receiver, options_reporter,TLSRPTReceiver, TLSRPTReporter, pospars_fetcher

class MyTestCase(unittest.TestCase):
    """
    Test usability of example config file
    """
    example_filename = "../pytlsrpt/example.cfg"

    def test_receiver_config(self):
        (configvars, params) = options_from_cmd_cfg_env(options_receiver, self.example_filename,
                                                        TLSRPTReceiver.CONFIG_SECTION,
                                                        TLSRPTReceiver.ENVIRONMENT_PREFIX,
                                                        {})
        config = ConfigReceiver(**configvars)
        self.assertEqual(config.log_level, "debug")

    def test_fetcher_config(self):
        (configvars, params) = options_from_cmd_cfg_env(options_receiver, self.example_filename,
                                                        TLSRPTReceiver.CONFIG_SECTION,
                                                        TLSRPTReceiver.ENVIRONMENT_PREFIX,
                                                        pospars_fetcher)
        config = ConfigReceiver(**configvars)
        self.assertEqual(config.log_level, "debug")

    def test_reporter_config(self):
        (configvars, params) = options_from_cmd_cfg_env(options_reporter, self.example_filename,
                                                        TLSRPTReporter.CONFIG_SECTION,
                                                        TLSRPTReporter.ENVIRONMENT_PREFIX,
                                                        {})
        config = ConfigReporter(**configvars)
        self.assertEqual(config.log_level, "debug")


if __name__ == '__main__':
    unittest.main()
