import datetime


# DELETEME/REVIEW: No used anywhere in the code. Should be removed
def myprint(*args, **kwargs):
    pass
    return print(*args, **kwargs)

def parse_tlsrpt_record(s):
    # first split into the main parts: version and RUAs
    mparts = s.split(";")
    if(len(mparts) < 2):
        raise Exception("Malformed TLSRPT record: No semicolon found")
    if(mparts[0] != "v=TLSRPTv1"):
        raise Exception("Unsupported TLSRPT version: " + mparts[0])
    ruapart = mparts[1].strip()
    if not ruapart.startswith("rua="):
        raise Exception("Malformed TLSRPT record: No rua found")
    ruapart=ruapart[4:]
    ruas=ruapart.split(",")
    return ruas


def tlsrpt_utc_time_now():
    """
    Returns a timezone aware datetime object of the current UTC time.
    """
    return datetime.datetime.now().astimezone(datetime.timezone.utc)


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
