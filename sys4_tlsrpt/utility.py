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
    :return: Timestamp of the report start the in the format required by RFC 8460
    """
    return day + "T00:00:00Z"

def tlsrpt_report_end_datetime(day):
    """
    Return end time of report for a specific day.
    :param day:  Day for which to create the end time.
    :return: Timestamp of the report end the in the format required by RFC 8460
    """
    return day + "T23:59:59Z"

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
