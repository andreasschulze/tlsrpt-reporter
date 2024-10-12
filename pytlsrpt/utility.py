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

import datetime

#  used only for development
def myprint(*args, **kwargs):
    pass
    return print(*args, **kwargs)

def parse_tlsrpt_record(tlsrpt_record):
    """
    Parses a TLSRPT DNS record and extracts the destination URIs
    :param s:
    :return:
    """
    # first split into the main parts: version and RUAs
    mparts = tlsrpt_record.split(";")
    if(len(mparts) < 2):
        raise Exception("Malformed TLSRPT record: No semicolon found")
    if(mparts[0] != "v=TLSRPTv1"):
        raise Exception("Unsupported TLSRPT version: " + mparts[0])
    ruapart = mparts[1].strip()
    if not ruapart.startswith("rua="):
        raise Exception("Malformed TLSRPT record: No rua found")
    ruapart=ruapart[4:]  # remove leading "rua="
    ruas=ruapart.split(",")
    return ruas

def tlsrpt_report_start_datetime(day):
    """
    Return start time of report for a specific day.
    :param day:  Day for which to create the start time.
    :return: Timestamp of the report start in the format required by RFC 8460
    """
    return day + "T00:00:00Z"

def tlsrpt_report_end_datetime(day):
    """
    Return end time of report for a specific day.
    :param day:  Day for which to create the end time.
    :return: Timestamp of the report end in the format required by RFC 8460
    """
    return day + "T23:59:59Z"

def tlsrpt_report_start_timestamp(day):
    """
    Return start time of report for a specific day.
    :param day:  Day for which to create the start time.
    :return: Timestamp of the report start as unix timestamp
    """
    day = datetime.datetime.fromisoformat(day)
    return day.timestamp()

def tlsrpt_report_end_timestamp(day):
    """
    Return timestamp of report for a specific day.
    :param day:  Day for which to create the timestamp.
    :return: Timestamp of the report end as unix timestamp
    """
    start = tlsrpt_report_start_timestamp(day)
    print("Value is", start, "and type is", type(start))
    return start+24*3600-1

def tlsrpt_utc_time_now():
    """
    Returns a timezone aware datetime object of the current UTC time.
    """
    return datetime.datetime.now(datetime.timezone.utc)


def tlsrpt_utc_date_now():
    """
    Returns the current date in UTC.
    """
    return tlsrpt_utc_time_now().date()


def tlsrpt_utc_date_yesterday():
    """
    Returns the date of yesterday in UTC.
    """
    ts = tlsrpt_utc_time_now()   # Making sure, ts is timezone-aware and UTC.
    dt = datetime.timedelta(days=-1)
    return (ts + dt).date()


class Duration:
    """
    Time duration and rate measurement class
    """
    def __init__(self):
        self.start()
        self.count = 0

    def start(self):
        self.begin = datetime.datetime.now(datetime.timezone.utc)

    def time(self):
        n = datetime.datetime.now(datetime.timezone.utc)
        d = n - self.begin
        return d

    def add(self, n=1):
        self.count += n

    def rate(self):
        return self.count / self.time().total_seconds()
