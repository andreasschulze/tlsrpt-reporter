#
#    Copyright (C) 2024 sys4 AG
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

import argparse
import configparser
import collections
import logging
import os

logger = logging.getLogger(__name__)


ConfigReceiver = collections.namedtuple("ConfigReceiver",
                                        ['receiver_dbname',
                                         'receiver_socketname',
                                         'receiver_sockettimeout',
                                         'max_uncommited_datagrams',
                                         'receiver_logfilename',
                                         'fetcher_logfilename',
                                         'dump_path_for_invalid_datagram'])

ConfigReporter = collections.namedtuple("ConfigReporter",
                                        ['reporter_logfilename',
                                         'reporter_dbname',
                                         'reporter_fetchers',
                                         'organization_name',
                                         'contact_info',
                                         'max_receiver_timeout',
                                         'max_receiver_timediff',
                                         'max_retries_domainlist',
                                         'min_wait_domainlist',
                                         'max_wait_domainlist',
                                         'max_retries_domaindetails',
                                         'min_wait_domaindetails',
                                         'max_wait_domaindetails'])

options_receiver = {
    "receiver_dbname": {"type": str, "default": "", "help": ""},
    "receiver_socketname": {"type": str, "default": "", "help": ""},
    "receiver_sockettimeout": {"type": int, "default": "", "help": ""},
    "max_uncommited_datagrams": {"type": int, "default": "", "help": ""},
    "receiver_logfilename": {"type": str, "default": "", "help": ""},
    "fetcher_logfilename": {"type": str, "default": "", "help": ""},
    "dump_path_for_invalid_datagram": {"type": str, "default": "", "help": ""},
}

options_reporter = {
    "reporter_logfilename": {"type": str, "default": "", "help": ""},
    "reporter_dbname": {"type": str, "default": "", "help": ""},
    "reporter_fetchers": {"type": str, "default": "", "help": ""},
    "organization_name": {"type": str, "default": "", "help": ""},
    "contact_info": {"type": str, "default": "", "help": ""},
    "max_receiver_timeout": {"type": int, "default": "10", "help": "Maximum expected receiver timeout"},
    "max_receiver_timediff": {"type": int, "default": "", "help": "Maximum expected receiver time difference"},
    "max_retries_domainlist": {"type": int, "default": "", "help": ""},
    "min_wait_domainlist": {"type": int, "default": "", "help": ""},
    "max_wait_domainlist": {"type": int, "default": "", "help": ""},
    "max_retries_domaindetails": {"type": int, "default": "", "help": ""},
    "min_wait_domaindetails": {"type": int, "default": "", "help": ""},
    "max_wait_domaindetails": {"type": int, "default": "", "help": ""}
}


def _options_from_cmd(options):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    for k in options:
        parser.add_argument("--" + k, type=options[k]["type"], help=options[k]["help"])
    tmp = parser.parse_args()
    return vars(tmp)  # extract dict from Namespace object


def options_from_cmd_cfg_env(options: dict, default_config_file: str, config_section: str, envprefix: str):
    """
    Get options dict from command line, configuration file, environment variables and defaults.
    :param options: dict of option definitions
    :param default_config_file: name of the default config file to read when no --config_file option is given
    :param config_section: name of the section to read from a config file
    :param envprefix: prefix for environment variable names
    :return: dict of all options and their values from command line, config file, environment or the defaults
    """
    # ocmd: options from command line
    # Add a parameter to specify a config file on the command line
    additional_options = {"config_file": {"type": str, "default": None, "help": "Configuration file"}}
    ocmd = _options_from_cmd({**options, **additional_options})
    # remove the added parameter from the results
    user_config_file = ocmd.pop("config_file", None)

    # ocfg: options from config file
    config_file = default_config_file
    if user_config_file is not None:
        if not os.path.isfile(user_config_file):
            raise FileNotFoundError("Config file not found: " + user_config_file)
        config_file = user_config_file

    cp = configparser.ConfigParser()
    cp.read(config_file)

    ocfg = {}
    if config_section not in cp.sections():  # raise clearer exception instead of just running into KeyError
        raise SyntaxError("Section " + config_section + " not found in config file " + config_file)
    for (k, v) in cp.items(config_section):
        if v is None or v == "":
            raise SyntaxError("Key " + k + " without value in config file " + config_file)
        elif k not in options:
            raise SyntaxError("Unknown key " + k + " in config file " + config_file)
        else:
            logging.debug("Config file has ", k, ":", v)
            ocfg[k] = options[k]["type"](v)

    # oenv: options from environment
    oenv = {}
    for k in options:
        ek = envprefix + k.upper()  # environment-key: option "--key" becomes "PREFIX_KEY" as environment variable
        if ek in os.environ:
            oenv[k] = options[k]["type"](os.environ[ek])

    # odef: options from defaults
    # While cmd and cfg and env need to be type converted from strings, the default values don´t need type conversion.
    # Therefore default ints need to be specified as ints, not as strings
    odef = dict(map(lambda kv: (kv[0], options[kv[0]]["default"]), options.items()))

    # combine results
    result = {}
    for k in options:
        tmp = None
        if tmp is None and k in ocmd:
            tmp = ocmd[k]
        if tmp is None and k in ocfg:
            tmp = ocfg[k]
        if tmp is None and k in oenv:
            tmp = oenv[k]
        if tmp is None and k in odef:
            tmp = odef[k]
        result[k] = tmp
    return result
