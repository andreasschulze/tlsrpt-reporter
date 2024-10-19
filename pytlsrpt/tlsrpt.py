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

import collections
import email.message
import gzip
import json
import logging
import random
import smtplib
from abc import ABCMeta, abstractmethod
from pathlib import Path
import socket
import subprocess
import sys
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

from pytlsrpt.utility import *
from pytlsrpt.config import *

# Constants
TLSRPT_FETCHER_VERSION_STRING_V1 = "TLSRPT FETCHER v1devel domain list"
TLSRPT_TIMEFORMAT = "%Y-%m-%d %H:%M:%S"
TLSRPT_MAX_READ_FETCHER = 16*1024*1024
TLSRPT_MAX_READ_RECEIVER = 16*1024*1024

# Exit codes
EXIT_DB_SETUP_FAILURE = 1
EXIT_WRONG_DB_VERSION = 2
EXIT_USAGE = 3


ConfigReceiver = collections.namedtuple("ConfigReceiver",
                                        ['storage',
                                         'receiver_socketname',
                                         'receiver_sockettimeout',
                                         'max_uncommited_datagrams',
                                         'retry_commit_datagram_count',
                                         'receiver_logfilename',
                                         'fetcher_logfilename',
                                         'log_level',
                                         'dump_path_for_invalid_datagram'])


# Available command line options for the receiver command.
options_receiver = {
    "storage": {"type": str, "default": "sqlite:///var/lib/tlsrpt/receiver.sqlite", "help": "Storage backend, multiple backends separated by comma"},
    "receiver_socketname": {"type": str, "default": "", "help": ""},
    "receiver_sockettimeout": {"type": int, "default": 5, "help": ""},
    "max_uncommited_datagrams": {"type": int, "default": 1000, "help": ""},
    "retry_commit_datagram_count": {"type": int, "default": 1000, "help": ""},
    "receiver_logfilename": {"type": str, "default": "/var/log/tlsrpt/receiver.log", "help": ""},
    "fetcher_logfilename": {"type": str, "default": "/var/log/tlsrpt/fetcher.log", "help": ""},
    "log_level": {"type": str, "default": "warn", "help": "Log level"},
    "dump_path_for_invalid_datagram": {"type": str, "default": "", "help": ""},
}


# Positional parameters for fetcher
pospars_fetcher = {
    "day": {"type": str, "help": "Day to fetch data for"},
    "domain": {"type": str, "help": "Domain to fetch data for, if omitted fetch list of domains"},
}


ConfigReporter = collections.namedtuple("ConfigReporter",
                                        ['reporter_logfilename',
                                         'log_level',
                                         'debug_db',
                                         'debug_send_mail_dest',
                                         'debug_send_http_dest',
                                         'debug_send_file_dest',
                                         'develmode',
                                         'reporter_dbname',
                                         'reporter_fetchers',
                                         'organization_name',
                                         'contact_info',
                                         'compression_level',
                                         'http_timeout',
                                         'smtp_server',
                                         'spread_out_delivery',
                                         'interval_main_loop',
                                         'max_receiver_timeout',
                                         'max_receiver_timediff',
                                         'max_retries_delivery',
                                         'min_wait_delivery',
                                         'max_wait_delivery',
                                         'max_retries_domainlist',
                                         'min_wait_domainlist',
                                         'max_wait_domainlist',
                                         'max_retries_domaindetails',
                                         'min_wait_domaindetails',
                                         'max_wait_domaindetails'])


options_reporter = {
    "reporter_logfilename": {"type": str, "default": "/var/log/tlsrpt/reporter.log", "help": ""},
    "log_level": {"type": str, "default": "warn", "help": "Log level"},
    "debug_db": {"type": int, "default": 0, "help": "Enable database debugging"},
    "debug_send_mail_dest": {"type": str, "default": "", "help": "Send all mail reports to this addres instead"},
    "debug_send_http_dest": {"type": str, "default": "", "help": "Post all mail reports to this server instead"},
    "debug_send_file_dest": {"type": str, "default": "", "help": "Save all mail reports to this directory additionally"},
    "develmode": {"type": int, "default": 0, "help": "Enable development mode. DO NOT USE ON PRODUCTIVE SYSTEM!"},
    "reporter_dbname": {"type": str, "default": "/var/lib/tlsrpt/reporter.sqlite", "help": ""},
    "reporter_fetchers": {"type": str, "default": "/usr/bin/tlsrpt-fetcher", "help": ""},
    "organization_name": {"type": str, "default": "", "help": ""},
    "contact_info": {"type": str, "default": "", "help": ""},
    "compression_level": {"type": int, "default": -1, "help": "zlib compression level used to create reports"},
    "http_timeout": {"type": int, "default": 10, "help": "Timeout for HTTPS uploads"},
    "smtp_server": {"type": str, "default": "", "help": "SMTP server to use for sending email reports"},
    "spread_out_delivery": {"type": int, "default": 36000, "help": "Time range in seconds to spread out report delivery"},
    "interval_main_loop": {"type": int, "default": 300, "help": "Maximum sleep interval in main loop"},
    "max_receiver_timeout": {"type": int, "default": 10, "help": "Maximum expected receiver timeout"},
    "max_receiver_timediff": {"type": int, "default": 10, "help": "Maximum expected receiver time difference"},
    "max_retries_delivery": {"type": int, "default": 5, "help": "Maximum attempts to deliver a report"},
    "min_wait_delivery": {"type": int, "default": 300, "help": "Minimum time in seconds between to delivery attempts"},
    "max_wait_delivery": {"type": int, "default": 1800, "help": "Maximum time in seconds between to delivery attempts"},
    "max_retries_domainlist": {"type": int, "default": 5, "help": ""},
    "min_wait_domainlist": {"type": int, "default": 30, "help": ""},
    "max_wait_domainlist": {"type": int, "default": 300, "help": ""},
    "max_retries_domaindetails": {"type": int, "default": 5, "help": ""},
    "min_wait_domaindetails": {"type": int, "default": 30, "help": ""},
    "max_wait_domaindetails": {"type": int, "default": 300, "help": ""}
}


def setup_logging(filename, level):
    logging.basicConfig(format="%(asctime)s %(levelname)s %(module)s %(lineno)s : %(message)s", level=logging.NOTSET)
    logger.addHandler(logging.FileHandler(filename))
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % level)
    logger.setLevel(numeric_level)


class EmailReport(email.message.EmailMessage):
    """
    Extension of EmailMessage with get_header method
    """
    def get_header(self, header):
        """
        Lookup an existing header
        :param header: email header to retrieve
        :return: the content of the email header
        """
        for k, v in self._headers:
            if k == header:
                return v
        raise IndexError("Header not found: " + header)


class TLSRPTReceiver(metaclass=ABCMeta):
    """
    Abstract base class for TLSRPT receiver implementations
    """
    DEFAULT_CONFIG_FILE = "/etc/tlsrpt/receiver.cfg"
    CONFIG_SECTION = "tlsrpt_receiver"
    ENVIRONMENT_PREFIX = "TLSRPT_"

    @abstractmethod
    def add_datagram(self, datagram):
        """
        Process a received datagram
        :param datagram: datagram received e.g. from the tlsrpt library
        """
        pass

    @abstractmethod
    def socket_timeout(self):
        """
        Process a timeout on the receiving socket
        """
        pass

    @staticmethod
    def factory(url: str, config: ConfigReceiver):
        if url.startswith("sqlite:"):
            return TLSRPTReceiverSQLite(url, config)
        elif url.startswith("dummy:"):
            return DummyReceiver(url, config)
        else:
            raise SyntaxError(f"Unsupported receiver URL: '{url}'")


class DummyReceiver(TLSRPTReceiver):
    """
    DummyReceiver only logs received datagrams.
    This is used during development to test support for multiple receivers.
    """

    def __init__(self, url: str, config: ConfigReceiver):
        parsed = urllib.parse.urlparse(urllib.parse.unquote(url))
        if parsed.scheme != "dummy":
            raise Exception(f"DummyReceiver can not be instantiated from '{url}'")
        dolog = (parsed.query == "log")
        self.dolog = dolog

    def add_datagram(self, datagram):
        if self.dolog:
            logger.info(f"Dummy receiver got datagram {datagram}")

    def socket_timeout(self):
        if self.dolog:
            logger.info("Dummy receiver got socket timeout")


class TLSRPTReceiverSQLite(TLSRPTReceiver):
    def __init__(self, url: str, config: ConfigReceiver):
        """
        :type config: ConfigReceiver
        """
        parsed = urllib.parse.urlparse(urllib.parse.unquote(url))
        if parsed.scheme != "sqlite":
            raise Exception(f"SQLiteReceiver can not be instantiated from '{url}'")

        self.cfg = config
        self.uncommitted_datagrams = 0
        self.total_datagrams_read = 0
        self.dbname = parsed.path
        logger.debug("Try to open database '%s'", self.dbname)
        self.con = sqlite3.connect("file:///"+self.dbname, uri=True)
        self.cur = self.con.cursor()
        if self._check_database():
            logger.info("Database %s looks OK", self.dbname)
        else:
            logger.info("Create new database %s", self.dbname)
            self._setup_database()
        # Settings for flushing to disk
        self.commitEveryN = self.cfg.max_uncommited_datagrams
        self.next_commit = tlsrpt_utc_time_now()

    def _setup_database(self):
        try:
            ddl = ["CREATE TABLE finalresults(day, domain, tlsrptrecord, policy, cntrtotal, cntrfailure, "
                   "PRIMARY KEY(day, domain, tlsrptrecord, policy))",
                   "CREATE TABLE failures(day, domain, tlsrptrecord, policy, reason, cntr, "
                   "PRIMARY KEY(day, domain, tlsrptrecord, policy, reason))",
                   "CREATE TABLE tlsrptreceiverdbversion(version, installdate)",
                   "INSERT INTO tlsrptreceiverdbversion(version, installdate) "
                   " VALUES(1,strftime('%Y-%m-%d %H-%M-%f','now'))"]

            for ddlstatement in ddl:
                self.cur.execute(ddlstatement)
            self.con.commit()
            logger.info("Database '%s' setup finished", self.dbname)
        except Exception as err:
            logger.error("Database '%s' setup failed: %s", self.dbname, err)
            sys.exit(EXIT_DB_SETUP_FAILURE)

    def _check_database(self):
        try:
            self.cur.execute("SELECT version, installdate FROM tlsrptreceiverdbversion")
            row = self.cur.fetchone()
            if row[0] != 1:
                logger.error("Database has wrong version, expected 1 but got %s", row)
                sys.exit(EXIT_WRONG_DB_VERSION)
            return True
        except Exception as err:
            logger.info("Database check failed: %s", err)
            return False

    def _db_commit(self, reason):
        """
        Perform a commit of the sqlite database to write data to disk so it can be accessed by the fetcher
        :param reason: Descriptive string for the logging message
        :return:
        """
        try:
            # adjust next_commit now BEFORE the actual commit might fail!
            # This way we avoid retrying it after each datagram and wasting too much time blocking in timeouts
            self.next_commit = tlsrpt_utc_time_now() + datetime.timedelta(seconds=self.cfg.receiver_sockettimeout)
            self.con.commit()
            logger.debug("%s with %d datagrams (%d total)", reason, self.uncommitted_datagrams, self.total_datagrams_read)
            self.uncommitted_datagrams = 0
        except sqlite3.OperationalError as e:
            logger.error("Failed "+reason+" with %d datagrams: %s", self.uncommitted_datagrams, e)

    def timed_commit(self):
        self._db_commit("Database commit due to timeout")

    def commit_after_n_datagrams(self):
        if tlsrpt_utc_time_now() > self.next_commit:
            self._db_commit("Database commit due to overdue")
        if self.uncommitted_datagrams >= self.commitEveryN:
            # a database problem can cause a commit-attempt to hang
            # do not retry after each additional datagram but wait for more data to accumulate before retrying
            if (self.uncommitted_datagrams-self.commitEveryN) % self.cfg.retry_commit_datagram_count == 0:
                self._db_commit("Database commit")

    def _add_policy(self, day, domain, tlsrptrecord, policy):
        """
        Process one of the policies found in the received datagram
        :param day: The day this datagram was received
        :param domain: The domain this report entry will be about
        :param tlsrptrecord: The tlsrpt DNS record
        :param policy: the policy dict
        """
        # Remove unneeded keys from policy before writing to database, keeping needed values
        policy_failed = policy.pop("f")  # boolean defining success or failure as final result
        failures = policy.pop("failure-details", [])  # the failures encountered
        failure_count = policy.pop("t", None)  # number of failures
        if failure_count != len(failures):
            logger.error("Failure count mismatch in received datagram: %d reported versus %d failured details: %s",
                         failure_count, len(failures), json.dumps(failures))
        p = json.dumps(policy)
        self.cur.execute(
            "INSERT INTO finalresults (day, domain, tlsrptrecord, policy, cntrtotal, cntrfailure) VALUES(?,?,?,?,1,?) "
            "ON CONFLICT(day, domain, tlsrptrecord, policy) "
            "DO UPDATE SET cntrtotal=cntrtotal+1, cntrfailure=cntrfailure+?",
            (day, domain, tlsrptrecord, p, policy_failed, policy_failed))

        for f in failures:
            self.cur.execute(
                "INSERT INTO failures (day, domain, tlsrptrecord, policy, reason, cntr) VALUES(?,?,?,?,?,1) "
                "ON CONFLICT(day, domain, tlsrptrecord, policy, reason) "
                "DO UPDATE SET cntr=cntr+1",
                (day, domain, tlsrptrecord, p, json.dumps(f)))

    def _add_policies_from_datagram(self, day, datagram):
        """
        Process the policies found in the received datagram
        :param day: The day this datagram was received
        :param datagram: The received datagram
        """
        if "policies" not in datagram:
            logger.warning("No policies found in datagram: %s", datagram)
            return
        for policy in datagram["policies"]:
            self._add_policy(day, datagram["d"], datagram["pr"], policy)

    def add_datagram(self, datagram):
        # process the datagram
        self._add_policies_from_datagram(tlsrpt_utc_date_now(), datagram)
        # database maintenance
        self.uncommitted_datagrams += 1
        self.total_datagrams_read += 1
        self.commit_after_n_datagrams()

    def socket_timeout(self):
        """
        Commit database to disk periodically
        """
        self.timed_commit()


class TLSRPTFetcherSQLite(TLSRPTReceiverSQLite):
    """
    Fetcher class for SQLite receiver
    """
    def fetch_domain_list(self, day):
        """
        List domains contained in this receiver database for a specific day
        :param day: The day for which to create a report
        """
        logger.info(f"TLSRPT fetcher domain list starting for day {day}")
        # protocol header line 1: the protocol version
        print(TLSRPT_FETCHER_VERSION_STRING_V1)
        # line 2: timeout in seconds so fetching can be rescheduled after a timeout commit, or warn about too big delay
        print(self.cfg.receiver_sockettimeout)
        # line 3: current time so fetching can be rescheduled to account for clock offset, or warn about too big delay
        print(tlsrpt_utc_time_now().strftime(TLSRPT_TIMEFORMAT))
        # protocol header finished
        # send domains
        dlcursor = self.con.cursor()
        dlcursor.execute("SELECT DISTINCT domain FROM finalresults WHERE day=?", (day,))
        alldata = dlcursor.fetchall()
        dlcursor.close()
        linenumber = 0
        for row in alldata:
            try:
                linenumber += 1
                print(row[0])
            except BrokenPipeError as err:
                logger.warning(f"Error when writing line {linenumber} : ", err)
                return
        # terminate domain list with a single dot
        print(".")

    def fetch_domain_details(self, day, domain):
        """
        Print out report details for a domain on a specific day
        :param day: The day for which to print the report details
        :param domain: The domain for which to print the report details
        """
        logger.info(f"TLSRPT fetcher domain details starting for day {day} and domain {domain}")
        policies = {}
        dlcursor = self.con.cursor()
        dlcursor.execute("SELECT domain, policy, tlsrptrecord, cntrtotal, cntrfailure "
                         "FROM finalresults WHERE day=? AND domain=?",
                         (day, domain))
        for (domain, policy, tlsrptrecord, cntrtotal, cntrfailure) in dlcursor:
            if tlsrptrecord not in policies:  # need to create new dict entry
                policies[tlsrptrecord] = {}
            if policy not in policies[tlsrptrecord]:  # need to create new dict entry
                policies[tlsrptrecord][policy] = {"cntrtotal": 0, "cntrfailure": 0, "failures": {}}
            policies[tlsrptrecord][policy]["cntrtotal"] += cntrtotal
            policies[tlsrptrecord][policy]["cntrfailure"] += cntrfailure

        dlcursor.execute("SELECT tlsrptrecord, policy, reason, cntr FROM failures WHERE day=? AND domain=?",
                         (day, domain))
        for (tlsrptrecord, policy, reason, cntr) in dlcursor:
            if reason not in policies[tlsrptrecord][policy]["failures"]:  # need to create new dict entry
                policies[tlsrptrecord][policy]["failures"][reason] = 0
            policies[tlsrptrecord][policy]["failures"][reason] += cntr
        details = {"d": domain, "policies": policies}
        print(json.dumps(details, indent=4))


class TLSRPTReporter:
    """
    The TLSRPT reporter class
    """

    DEFAULT_CONFIG_FILE = "/etc/tlsrpt/reporter.cfg"
    CONFIG_SECTION = "tlsrpt_reporter"
    ENVIRONMENT_PREFIX = "TLSRPT_"

    def __init__(self, config: ConfigReporter):
        """
        :type config: ConfigReporter
        """
        self.cfg = config
        self.dbname = self.cfg.reporter_dbname
        self.con = sqlite3.connect(self.dbname)
        self.cur = self.con.cursor()
        self.curtoupdate = self.con.cursor()
        self.wakeuptime = tlsrpt_utc_time_now()
        if self._check_database():
            logger.info("Database %s looks OK", self.dbname)
        else:
            logger.info("Create new database %s", self.dbname)
            self._setup_database()
        if self.cfg.debug_db:
            self.con.set_trace_callback(print)

    def _setup_database(self) -> None:
        """
        Create the database table structure. If the database setup cannot be
        completed, program execution is terminated with non-zero return value.
        """
        try:
            ddl = ["CREATE TABLE fetchjobs(day, fetcherindex, fetcher, retries, status, nexttry, "
                   "PRIMARY KEY(day, fetcherindex))",
                   "CREATE TABLE reportdata(day, domain, data, fetcher, fetcherindex, retries, status, nexttry, "
                   "PRIMARY KEY(day, domain, fetcher))",
                   "CREATE TABLE reports(r_id INTEGER PRIMARY KEY ASC, day, domain, uniqid, tlsrptrecord, report)",
                   "CREATE TABLE destinations(destination, d_r_id INTEGER, retries, status, nexttry, "
                   "PRIMARY KEY(destination, d_r_id), "
                   "FOREIGN KEY(d_r_id) REFERENCES reports(r_id))",
                   "CREATE TABLE tlsrptreporterdbversion(version, installdate)",
                   "INSERT INTO tlsrptreporterdbversion(version, installdate) "
                   " VALUES(1,strftime('%Y-%m-%d %H-%M-%f','now'))"]
            for ddlstatement in ddl:
                logger.debug("Database '%s' DDL %s", self.dbname, ddlstatement)
                self.cur.execute(ddlstatement)
            self.con.commit()
            logger.info("Database '%s' setup finished", self.dbname)
        except Exception as err:
            logger.error("Database '%s' setup failed: %s", self.dbname, err)
            sys.exit(EXIT_DB_SETUP_FAILURE)

    def _check_database(self) -> bool:
        """
        Tries to run a database query, returns True if database has the correct
        version and works as expected. If the database has wrong database
        version, the whole program execution is terminated.
        """
        try:
            self.cur.execute("SELECT version, installdate FROM tlsrptreporterdbversion")
            row = self.cur.fetchone()
            if row[0] != 1:
                logger.error("Database has wrong version, expected 1 but got %s", row)
                sys.exit(EXIT_WRONG_DB_VERSION)
            return True
        except Exception as err:
            logger.error("Database check failed: %s", err)
            return False

    def get_fetchers(self):
        """
        Parse and extract fetchers from config
        :return: An array of fetcher commands
        """
        fetchers = self.cfg.reporter_fetchers.split(",")
        return fetchers

    def _wait(self, smin, smax):
        """
        Calculates a random wait period between smin and smax seconds

        :return: seconds to wait before next retry
        """
        return random.randint(smin, smax)

    def wait_domainlist(self):
        """
        Calculates a random wait period between smin and smax seconds

        :return: seconds to wait before next retry
        """
        return self._wait(self.cfg.min_wait_domainlist, self.cfg.max_wait_domainlist)

    def wait_retry_report_delivery(self):
        """
        Calculates a random wait period between smin and smax seconds

        :return: seconds to wait before next retry
        """
        return self._wait(self.cfg.min_wait_delivery, self.cfg.max_wait_delivery)

    def schedule_report_delivery(self):
        secs = random.randint(0, self.cfg.spread_out_delivery)
        return tlsrpt_utc_time_now() + datetime.timedelta(seconds=secs)

    def check_day(self):
        """
        Check if a new day has started and create jobs for the new day to be processed in the next steps
        """
        logger.debug("Check day")
        cur = self.con.cursor()
        yesterday = tlsrpt_utc_date_yesterday()
        if self.cfg.develmode:  # use today´s data during development
            yesterday = tlsrpt_utc_date_now()
        now = tlsrpt_utc_time_now()
        cur.execute("SELECT * FROM fetchjobs WHERE day=?", (yesterday,))
        row = cur.fetchone()
        if row is not None:  # Jobs already exist
            self.wake_up_in(300)  # wake up every five minutes to check
            return
        # create now fetcher jobs
        fidx = 0
        for fetcher in self.get_fetchers():
            fidx += 1
            cur.execute("INSERT INTO fetchjobs (day, fetcherindex, fetcher, retries, status, nexttry)"
                        "VALUES (?,?,?,0,NULL,?)", (yesterday, fidx, fetcher, now))
        self.con.commit()

    def collect_domains(self):
        """
        Collect domains from the fetchers
        """
        logger.debug("Collect domains")
        curs = self.con.cursor()
        curu = self.con.cursor()
        now = tlsrpt_utc_time_now()
        curs.execute("SELECT day, fetcherindex, fetcher, retries FROM fetchjobs "
                     "WHERE status IS NULL AND nexttry<?", (now,))
        for (day, fetcherindex, fetcher, retries) in curs:
            if self.collect_domains_from(day, fetcher, fetcherindex):
                logger.info("Fetcher %d %s finished in run %d", fetcherindex, fetcher, retries)
                curu.execute("UPDATE fetchjobs SET status='ok' WHERE day=? AND fetcherindex=?", (day, fetcherindex))
            elif retries < self.cfg.max_retries_domainlist:
                logger.warning("Fetcher %d %s failed in run %d", fetcherindex, fetcher, retries)
                curu.execute("UPDATE fetchjobs SET retries=retries+1, nexttry=? WHERE day=? AND fetcherindex=?",
                             (self.wake_up_in(self.wait_domainlist()), day, fetcherindex))
            else:
                logger.warning("Fetcher %d %s timedout after %d retries", fetcherindex, fetcher, retries)
                curu.execute("UPDATE fetchjobs SET status='timedout' WHERE day=? AND fetcherindex=?",
                             (day, fetcherindex))
        self.con.commit()

    def collect_domains_from(self, day, fetcher, fetcherindex):
        """
        Fetch the list of domains from one of the fetchers

        :param day: Day for which to fetch the domain list
        :type fetcher: The fetcher to run
        :type fetcherindex: The fetchers index in the configuration
        :return: True if the job completed successfully, False if a retry is necessary
        """
        logger.debug("Collect domains from %d %s", fetcherindex, fetcher)
        duration = Duration()
        args = fetcher.split()
        args.append(day.__str__())
        fetcherpipe = subprocess.Popen(args, stdout=subprocess.PIPE)
        versionheader = fetcherpipe.stdout.readline().decode('utf-8').rstrip()
        logger.debug(f"From fetcher {fetcherindex} got version header: {versionheader}")
        if versionheader != TLSRPT_FETCHER_VERSION_STRING_V1:
            logger.error(f"Unsupported protocol version from fetcher {fetcherindex} '{fetcher}': {versionheader}")
            return False
        # get socket timeout and therefore the commit lag of this receiver
        receiver_timeout = fetcherpipe.stdout.readline().decode('utf-8').rstrip()
        if int(receiver_timeout) > self.cfg.max_receiver_timeout:
            logger.warning(f"Receiver timeout {receiver_timeout} greater than maximum of "
                           f"{self.cfg.max_receiver_timeout} on fetcher {fetcherindex} {fetcher}")
        # get current time of this receiver
        receiver_time_string = fetcherpipe.stdout.readline().decode('utf-8').rstrip()
        receiver_time = datetime.datetime.strptime(receiver_time_string, TLSRPT_TIMEFORMAT). \
            replace(tzinfo=datetime.timezone.utc)
        reporter_time = tlsrpt_utc_time_now()
        dt = reporter_time - receiver_time
        if abs(dt.total_seconds()) > self.cfg.max_receiver_timediff:
            logger.warning(f"Receiver time {receiver_time} and reporter time {reporter_time} differ more then "
                           f"{self.cfg.max_receiver_timediff} on fetcher {fetcherindex} {fetcher}")

        self.cur.execute("SAVEPOINT domainlist")
        # read the domain list
        result = True
        dc = 0  # domain count
        try:
            while result:
                dom = fetcherpipe.stdout.readline().decode('utf-8').rstrip()
                logger.debug("Got line '%s'", dom)
                if dom == ".":  # end of domain list reached
                    break
                if not dom:  # EOF
                    # this is a warning instead of an error because a remote connection could have been interrupted
                    # and a retry might succeed
                    logger.warning("Unexpected end of domain list")
                    result = False
                    break
                try:
                    self.cur.execute("INSERT INTO reportdata "
                                     "(day, domain, data, fetcherindex, fetcher, retries, status, nexttry) "
                                     "VALUES (?,?,NULL,?,?,0,NULL,?)",
                                     (day, dom, fetcherindex, fetcher, tlsrpt_utc_time_now()))
                    dc += 1
                except sqlite3.IntegrityError as e:
                    logger.warning(e)
        except Exception as e:
            logger.error("Unexpected exception: %s", e.__str__())
            result = False

        if result:
            logger.info(f"DB-commit for fetcher {fetcherindex} {fetcher}")
            self.cur.execute("RELEASE SAVEPOINT domainlist")
            self.con.commit()
        else:
            logger.info(f"DB-rollback for fetcher {fetcherindex} {fetcher}")
            self.cur.execute("ROLLBACK TO SAVEPOINT domainlist")
            self.con.commit()
        duration.add(dc)
        logger.info(f"Fetching {dc} domains took {duration.time()}, {duration.rate()} domains per second")
        return result

    def select_incomplete_days(self, cursor):
        """
        Get days with incomplete fetchjobs from the database
        :param cursor: the DB cursor to use for the query
        :return: the row set of incomplete days
        """
        # select days that are not fully fetched yet for debug loglevel
        cursor.execute("SELECT day FROM fetchjobs WHERE status IS NULL")
        incompletedays = cursor.fetchall()
        return incompletedays

    def fetch_data(self):
        """
        Fetch details for the domains not yet processed
        """
        logger.debug("Fetch data")
        curtofetch = self.con.cursor()
        incompletedays = self.select_incomplete_days(curtofetch)
        if len(incompletedays) != 0:
            logger.debug("The are %d incomplete days: %s", len(incompletedays), incompletedays.__str__())

        # select jobs that are due
        now = tlsrpt_utc_time_now()
        curtofetch.execute(
            "SELECT day, fetcher, fetcherindex, domain FROM reportdata "
            "WHERE data IS NULL AND nexttry<? AND day NOT IN (SELECT day FROM fetchjobs WHERE status IS NULL)",
            (now,))
        for (day, fetcher, fetcherindex, domain) in curtofetch:
            self.fetch_data_from_fetcher_for_domain(day, fetcher, fetcherindex, domain)

    def fetch_data_from_fetcher_for_domain(self, day, fetcher, fetcherindex, dom):
        """
        Fetch details for one domain from one fetcher for a specific day
        :param day: Day for which to fetch the domain details
        :type fetcher: The fetcher to run
        :type fetcherindex: The fetchers index in the configuration
        :param dom: The domain for which to fetch the details
        """
        logger.debug("Fetch data from %d %s for domain %s", fetcherindex, fetcher, dom)
        args = fetcher.split()
        args.append(day.__str__())
        args.append(dom)
        try:
            fetcherpipe = subprocess.Popen(args, stdout=subprocess.PIPE)
        except FileNotFoundError as e:
            logger.error("File not found when trying to run fetcher %s: %s", fetcher, e.__str__())
            return
        alldata = fetcherpipe.stdout.read(TLSRPT_MAX_READ_FETCHER)
        try:
            j = json.loads(alldata)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON: %s", e.__str__())
            return
        gotdom = j.pop("d")
        if gotdom != dom:
            logger.error("Domain mismatch! Asked for %s but got reply for %s", dom, gotdom)
            return
        data = j.pop("policies")
        self.curtoupdate.execute("UPDATE reportdata SET data=?, status='fetched' "
                                 "WHERE day=? AND fetcherindex=? AND domain=?",
                                 (json.dumps(data), day, fetcherindex, dom))
        self.con.commit()

    def aggregate_report_from_data(self, r, data):
        """
        Aggregate data into report
        :param r: the report into which to aggregate the data
        :param data: the data
        """
        # spolicy is the whole policy as a string, do not to be confused with the "policy-string" inside it
        for spolicy in data:
            tmp = data[spolicy]
            cntrtotal = tmp["cntrtotal"]
            cntrfailure = tmp["cntrfailure"]
            failures = tmp["failures"]
            if spolicy not in r:
                r[spolicy] = {"cntrtotal": 0, "cntrfailure": 0, "failures": {}}
            r[spolicy]["cntrtotal"] += cntrtotal
            r[spolicy]["cntrfailure"] += cntrfailure
            for failure in failures:
                if failure not in r[spolicy]["failures"]:
                    r[spolicy]["failures"][failure] = 0
                r[spolicy]["failures"][failure] += failures[failure]

    def render_report(self, day, dom, tlsrptrecord, data, report):
        """
        Render a report into its final form
        :param day: Day for which to create the report
        :param dom: Domain for which to create the report
        :param tlsrptrecord: TLSRPT DNS record describing the recipients of the report
        :param data: The data from which to create the report
        :param report: The report
        """
        policies = []
        for spolicy in data:
            tmp = data[spolicy]
            cntrtotal = tmp["cntrtotal"]
            cntrfailure = tmp["cntrfailure"]
            failures = tmp["failures"]
            policy = json.loads(spolicy)
            policy_type_names = {1: "tlsa", 2: "sts", 9: "no-policy-found"}  # mapping of policy types
            policy["policy-type"] = policy_type_names[policy["policy-type"]]
            npol = {"summary": {"total-failure-session-count": cntrfailure,
                                "total-successful-session-count": cntrtotal - cntrfailure}}
            npol["policy"] = policy
            npol["failure-details"] = []
            for sfailure in failures:
                fdet = {}
                failure = json.loads(sfailure)
                fdmap = {  # mapping of failure detail short keys from receiver to long keys conforming to RFC8460
                    "a": "additional-information",
                    # "c": "failure-code",  # will be mapped via fcmap below
                    "f": "failure-reason-code",
                    "h": "receiving-mx-helo",
                    "n": "receiving-mx-hostname",
                    "r": "receiving-ip",
                    "s": "sending-mta-ip"
                }

                fcmap = {  # failure code map
                    # maps integer numbers from the internal receiver protocol to result-types defined in RFC8460
                    # TLS negotiation failures
                    201: "starttls-not-supported",
                    202: "certificate-host-mismatch",
                    203: "certificate-not-trusted",
                    204: "certificate-expired",
                    205: "validation-failure",

                    # mta-sts related failures
                    301: "sts-policy-fetch-error",
                    302: "sts-policy-invalid",
                    303: "sts-webpki-invalid",

                    # dns related failures
                    304: "tlsa-invalid",
                    305: "dnssec-invalid",
                    306: "dane-required"
                }
                for k in fdmap:
                    if k in failure:
                        fdet[fdmap[k]] = failure[k]
                rtcode = "c"  # key for numeric result-type code in receiver data
                if rtcode in failure:
                    if failure[rtcode] in fcmap:
                        fdet["result-type"] = fcmap[failure[rtcode]]
                    else:
                        logger.error("Undefined result type code %d", rtcode)
                fdet["failed-session-count"] = failures[sfailure]
                npol["failure-details"].append(fdet)
            policies.append(npol)
        report["policies"] = policies
        cur = self.con.cursor()
        cur.execute("SELECT COUNT(*)+1 FROM reports WHERE day=? AND domain=?", (day, dom))
        uniqid = 0
        for (uniqid,) in cur:
            break
        cur.execute("INSERT INTO reports (day, domain, uniqid, report) VALUES(?,?,?,?)",
                    (day, dom, uniqid, json.dumps(report)))
        r_id = cur.lastrowid
        for rua in parse_tlsrpt_record(tlsrptrecord):
            cur.execute("INSERT INTO destinations (destination, d_r_id, retries, status, nexttry) VALUES(?,?,0,NULL,?)",
                        (rua, r_id, self.schedule_report_delivery()))

    def create_report_for(self, day, dom):
        """
        Creates one or multiple reports for a domain and a specific day.
        Multiple reports can be created if there are different TLSRPT records and therefore different recipients.
        :param day: Day for which to create the reports
        :param dom: Domain for which to create the reports
        """
        logger.debug("Will create report for day %s domain %s", day, dom)
        cur = self.con.cursor()
        cur.execute("SELECT data FROM reportdata WHERE day=? AND domain=?", (day, dom))
        reports = {}
        for (data,) in cur:
            j = json.loads(data)
            for tlsrptrecord in j:
                if tlsrptrecord not in reports:  # need to create new dict entry
                    reports[tlsrptrecord] = {}
                self.aggregate_report_from_data(reports[tlsrptrecord], j[tlsrptrecord])

        report_index = 0
        for tlsrptrecord in reports:
            report_index += 1
            rawreport = reports[tlsrptrecord]
            report_domain = dom
            report_start_datetime = tlsrpt_report_start_datetime(day)
            report_end_datetime = tlsrpt_report_end_datetime(day)
            report_id = report_start_datetime + "_idx" + str(report_index) + "_" + report_domain
            report = {"organization-name": self.cfg.organization_name,
                      "date-range": {
                          "start-datetime": report_start_datetime,
                          "end-datetime": report_end_datetime},
                      "contact-info": self.cfg.contact_info,
                      "report-id": report_id,
                      }
            self.render_report(day, dom, tlsrptrecord, rawreport, report)
        self.con.commit()

    def create_reports(self):
        """
        Create all reports possible, i.e. where no data is pending.
        """
        logger.debug("Create reports")
        curtofetch = self.con.cursor()
        self.curtoupdate = self.con.cursor()
        # Some diagnostic information
        curtofetch.execute("SELECT fetcherindex, domain FROM reportdata WHERE data IS NULL")
        for (fetcherindex, domain) in curtofetch:
            logger.warning("Incomplete data for domain %s by fetcher index %d", domain, fetcherindex)
        # fetch all data keys with complete data and no report yet
        curtofetch.execute("SELECT DISTINCT day, domain FROM reportdata WHERE status='fetched' "
                           "AND NOT (day, domain) IN "
                           "(SELECT day, domain FROM reportdata WHERE status IS NULL) "
                           "AND NOT (day, domain) IN "
                           "(SELECT day, domain FROM reports)")
        for (day, dom) in curtofetch:
            self.create_report_for(day, dom)

    def send_out_report_to_file(self, dom, d_r_id, destination, report, debugdir):
        filename = debugdir + "/testreport-" + dom + "-" + str(d_r_id) + "-" + destination.replace("/", "_") + ".json"
        logger.debug("Would send out report %s to %s, saving to %s", str(d_r_id), destination, filename)
        with open(filename, "w") as file:
            file.write(report)

    def send_out_report_to_mail(self, day, dom, d_r_id, uniqid, destination, zreport):
        # Check for debug override of destination
        dest = self.cfg.debug_send_mail_dest
        if dest is None or dest == "":
            dest = destination

        # Call send script
        msg = EmailReport()
        msg['Subject'] = self.create_email_subject(dom, d_r_id)
        msg['From'] = self.cfg.contact_info
        msg['To'] = dest
        msg.add_header("TLS-Report-Domain", dom)
        msg.add_header("TLS-Report-Submitter", self.cfg.organization_name)

        nr = uniqid
        n = self.create_report_filename(dom, day, nr)
        data = zreport
        intro = "This is an aggregate TLS report from "+self.cfg.organization_name  # .encode("ascii")
        msg.set_content(intro, charset="ascii")
        msg.add_attachment(data, maintype="application", subtype="tlsrpt+gzip", filename=n)

        # Replace MIME multipart header with TLSRPT report header
        h = msg.get_header("Content-Type")
        nh = h.replace("multipart/mixed", "multipart/report; report-type=""tlsrpt""")
        msg.replace_header("Content-Type", nh)

        reportemail = msg.as_string(policy=email.policy.SMTP)
        debugdir = self.cfg.debug_send_file_dest
        if debugdir is not None and debugdir != "":
            self.send_out_report_to_file(dom, d_r_id, "THE_EMAIL_TO_"+destination, reportemail, debugdir)
        result = False
        try:
            with smtplib.SMTP(self.cfg.smtp_server) as s:
                refused = s.send_message(msg)
                if len(refused) == 0:
                    result = True
                    logger.warning("Sent report email to %s", dest)
                else:
                    logger.warning("Delivery error in sending report email to %s: %s", dest, refused.__str__())
        except Exception as e:
            logger.error("Exception in sending report email to %s: %s", dest, e)
        return result

    def send_out_report_to_http(self, dom, d_r_id, destination, zreport):
        # Check for debug override of destination
        dest = self.cfg.debug_send_http_dest
        if dest is None or dest == "":
            dest = destination
        # Post the report
        headers = {"Content-Type": "application/tlsrpt+gzip"}
        req = urllib.request.Request(dest, zreport, headers)
        try:
            with urllib.request.urlopen(req, zreport, self.cfg.http_timeout) as response:
                result = response.read()
                logger.debug("Upload to '%s' successful: %s", destination, result)
                return True
        except urllib.error.URLError as e:
            logger.warning("Error in uploading to '%s': %s", destination, e)
            return False

    def send_out_report(self, day, dom, d_r_id, uniqid, destination, report):
        # Dump report as a file for debugging
        debugdir = self.cfg.debug_send_file_dest
        if debugdir is not None and debugdir != "":
            self.send_out_report_to_file(dom, d_r_id, destination, report, debugdir)
        # Zip the report
        zreport = gzip.compress(report.encode("utf-8"), self.cfg.compression_level)
        # Send out the actual report
        if destination.startswith("mailto:"):
            return self.send_out_report_to_mail(day, dom, d_r_id, uniqid, destination[7:], zreport)
        elif destination.startswith("https:"):
            return self.send_out_report_to_http(dom, d_r_id, destination, zreport)
        else:
            raise IndexError("Unknown protocol in report destination '%s'", destination)

    def send_out_reports(self):
        """
        Send out the finished reports.
        """
        logger.debug("Send out reports")
        cur = self.con.cursor()  # cursor for selects
        curu = self.con.cursor()  # cursor for updates
        cur.execute(
            "SELECT destination, d_r_id, uniqid, report, domain, day, retries FROM destinations "
            "LEFT JOIN reports on r_id=d_r_id WHERE destinations.status IS NULL")
        for (destination, d_r_id, uniqid, report, dom, day, retries) in cur:
            logger.info("Report delivery %d for domain %s succeeded in run %d", d_r_id, dom, retries)
            if self.send_out_report(day, dom, d_r_id, uniqid, destination, report):
                curu.execute("UPDATE destinations SET status='sent' WHERE destination=? AND d_r_id=?",
                             (destination, d_r_id))
            elif retries < self.cfg.max_retries_delivery:
                logger.warning("Report delivery %d for domain %s failed in run %d", d_r_id, dom, retries)
                curu.execute("UPDATE destinations SET retries=retries+1, nexttry=? WHERE destination=? AND d_r_id=?",
                             (self.wake_up_in(self.wait_retry_report_delivery()), destination, d_r_id))
            else:
                logger.warning("Report delivery %d for domain %s timedout after %d  retries", d_r_id, dom, retries)
                curu.execute("UPDATE destinations SET status='timedout' WHERE destination=? AND d_r_id=?",
                             (destination, d_r_id))
            self.con.commit()

    def wake_up_in(self, secs, force=False):
        """
        Schedule next main loop run in secs seconds
        :param secs: The number of seconds to sleep at most
        :param force: Set this wake up time as an override even if a shorter wake up time is already set
        :return: The new wake up time
        """
        return self.wake_up_at(tlsrpt_utc_time_now() + datetime.timedelta(seconds=secs), force)

    def wake_up_at(self, t, force=False):
        """
        Schedule next main loop run at time t
        :param t: The time to start the next main loop run
        :param force: Set this wake up time as an override even if a shorter wake up time is already set
        :return: The new wake up time
        """
        if self.wakeuptime > t:
            logger.debug(f"Changing wake up time from {self.wakeuptime} to {t}")
            self.wakeuptime = t
        elif force:
            logger.debug(f"Enforcing wake up time from {self.wakeuptime} to {t}")
            self.wakeuptime = t
        else:
            logger.debug(f"Not changing wake up time from {self.wakeuptime} to {t}")
        return self.wakeuptime

    def run_loop(self):
        """
        Main loop processing the various jobs and steps.
        """
        while True:
            self.wake_up_in(self.cfg.interval_main_loop, True)
            self.check_day()
            self.collect_domains()
            self.fetch_data()
            self.create_reports()
            self.send_out_reports()
            dt = self.wakeuptime - tlsrpt_utc_time_now()
            seconds_to_sleep = dt.total_seconds()
            if seconds_to_sleep >= 0:
                logger.info("Sleeping for %d seconds", seconds_to_sleep)
                time.sleep(seconds_to_sleep)
            else:
                logger.info("Skipping sleeping for negative %d seconds", seconds_to_sleep)

    def create_email_subject(self, dom, d_r_id):
        return "Report Domain: " + dom + " Submitter: "+self.cfg.organization_name + " Report-ID: " + str(d_r_id)

    def create_report_filename(self, dom, day, nr):
        start = tlsrpt_report_start_timestamp(day)
        end = tlsrpt_report_end_timestamp(day)
        return self.cfg.organization_name + "!" + dom + "!" + str(start) + "!" + str(end) + "!" + str(nr) + ".json.gz"


def tlsrpt_receiver_main():
    """
    Contains the main TLSRPT receiver loop. This listens on a socket to
    receive TLSRPT datagrams from the MTA (e.g. Postfix). and writes the
    datagrams to the database.
    """
    (configvars, params) = options_from_cmd_cfg_env(options_receiver,  TLSRPTReceiver.DEFAULT_CONFIG_FILE,
                                                    TLSRPTReceiver.CONFIG_SECTION, TLSRPTReceiver.ENVIRONMENT_PREFIX,
                                                    {})
    config = ConfigReceiver(**configvars)

    server_address = config.receiver_socketname

    setup_logging(config.receiver_logfilename, config.log_level)

    logger.info("TLSRPT receiver starting")
    # Make sure the socket does not already exist
    try:
        if os.path.exists(server_address):
            os.unlink(server_address)
    except OSError as err:
        logger.error("Failed to remove already existing socket %s: %s", server_address, err)
        raise

    # Create a Unix Domain Socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    # Bind the socket to the port
    if server_address is None or server_address == "":
        raise Exception("No receiver_socketname configured")
    logger.info("Listening on socket '%s'" % server_address)
    sock.bind(server_address)
    sock.settimeout(config.receiver_sockettimeout)

    # Multiple receivers to be set-up from configuration
    receivers = []
    for r in config.storage.split(","):
        receivers.append(TLSRPTReceiver.factory(r, config))
    if len(receivers) == 0:
        raise Exception("No receiver storage configured")

    while True:
        alldata = None  # clear old data to prevent accidentally processing it twice
        try:
            # Uncomment to test very low throughput
            # time.sleep(1)
            alldata, srcaddress = sock.recvfrom(TLSRPT_MAX_READ_RECEIVER)
            j = json.loads(alldata)
            for receiver in receivers:
                try:
                    receiver.add_datagram(j)
                except KeyError as err:
                    logger.error(f"KeyError {err} during processing datagram: {json.dumps(j)}")
                    raise err
        except socket.timeout:
            for receiver in receivers:
                receiver.socket_timeout()
        except OSError as err:
            logger.error(f"OS-Error: {err}")
            raise
        except UnicodeDecodeError as err:
            logger.error(f"Malformed utf8 data received: {err}")
            Path(config.dump_path_for_invalid_datagram).write_bytes(alldata)
        except json.decoder.JSONDecodeError as err:
            logger.error(f"JSON decode error: {err}")
            Path(config.dump_path_for_invalid_datagram).write_text(alldata.decode("utf-8"), encoding="utf-8")
        except sqlite3.OperationalError as err:
            logger.error(f"Database error: {err}")


def tlsrpt_fetcher_main():
    """
    Runs the fetcher main. The fetcher is used by the TLSRPT-reporter to
    read the database entries that were written by the receiver.
    """
    # TLSRPT-fetcher is tightly coupled to TLSRPT-receiver and uses its config and database
    (configvars, params) = options_from_cmd_cfg_env(options_receiver, TLSRPTReceiver.DEFAULT_CONFIG_FILE,
                                                    TLSRPTReceiver.CONFIG_SECTION, TLSRPTReceiver.ENVIRONMENT_PREFIX,
                                                    pospars_fetcher)
    config = ConfigReceiver(**configvars)

    setup_logging(config.fetcher_logfilename, config.log_level)

    # Fetcher uses the first configured storage
    url = config.storage.split(",")[0]
    if not url.startswith("sqlite:"):
        raise Exception(f"Can not fetch data from storage '{url}'")
    fetcher = TLSRPTFetcherSQLite(url, config)

    if params["day"] is None or params["day"] == "":
        print("Usage: %s day [domain]", file=sys.stderr)
        sys.exit(EXIT_USAGE)
    if params["domain"] is None:
        fetcher.fetch_domain_list(params["day"])
    else:
        fetcher.fetch_domain_details(params["day"], params["domain"])


def tlsrpt_reporter_main():
    """
    Entry point to the reporter main. The reporter is the part that finally
    sends the STMP TLS reports out the endpoints that the other MTA operators
    have published.
    """

    (configvars, params) = options_from_cmd_cfg_env(options_reporter, TLSRPTReporter.DEFAULT_CONFIG_FILE,
                                                    TLSRPTReporter.CONFIG_SECTION, TLSRPTReporter.ENVIRONMENT_PREFIX,
                                                    {})
    config = ConfigReporter(**configvars)
    setup_logging(config.reporter_logfilename, config.log_level)

    logger.info("TLSRPT reporter starting")

    reporter = TLSRPTReporter(config)
    reporter.run_loop()


if __name__ == "__main__":
    print("Call tlsrpt fetcher, receiver or reporter instead of this file", file=sys.stderr)
