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


import logging
from typing import Tuple, Union
from xmlrpc.client import Boolean

logger = logging.getLogger(__name__)

import collections
import re
from abc import abstractmethod
import urllib.parse
from io import StringIO
from tlsrpt_reporter import utility


LL_DOMAINMATCHER = 5  # log level to debug matcher function, even lower than normal DEBUG=10


DestinationMapEntry = collections.namedtuple( "DestinationMapEntry", ['matcher', 'action', 'linenr'])


class MapAction:
    """
    Abstract base class for all map transformations
    """
    @abstractmethod
    def result(self, destinations: list[str]):
        """
        Transforms a list of report destinations
        :param destinations: a list of report destinations to be modified
        :type destinations: list[str]
        :return: the modified list of destinations
        :rtype: list[str]
        """
        raise NotImplementedError


class MapActionAccept(MapAction):
    """
    A MapAction that passes through the list of destinations without modifications
    """
    def result(self, destinations: list[str]):
        return destinations


class MapActionDiscard(MapAction):
    """
    A MapAction that returns an empty list of destinations, thus discarding all destinations
    """
    def result(self, destinations: list[str]):
        return []


class MapActionReplace(MapAction):
    """
    A MapAction that replaces the destinations with another set of destinations
    """
    def __init__(self, replacement_destinations):
        self.replacement_destinations = replacement_destinations
    def result(self, destinations: list[str]):
        return self.replacement_destinations


class MapActionAppend(MapAction):
    """
    A MapAction that appends a set of destinations to the existing destinations
    """
    def __init__(self, additional_destinations):
        self.additional_destinations = additional_destinations
    def result(self, destinations: list[str]):
        return destinations + self.additional_destinations


class MapActionRegexpTransform(MapAction):
    """
    A MapAction that transforms each destination using regular expressions
    """
    def __init__(self, pattern, substitution):
        self.pattern = pattern
        self.substitution = substitution
    def result(self, destinations: list[str]):
        res = []
        for d in destinations:
            (nd, n) = re.subn(self.pattern, self.substitution, d)
            res.append(nd)
        return res


def _domain_match(domain: str, pattern: str) -> Boolean:
    """
    Checks if a domain matches a domain pattern
    :param domain: The domain to be checked
    :type domain: str
    :param pattern: The patter to be checked against
    :type pattern: str
    :return: True if the domain matches the pattern, False if the domain does not match the pattern
    :rtype: Boolean
    """
    domain=utility.remove_suffix(domain, ".")
    if pattern == ".":  # catch-all
        logger.log(LL_DOMAINMATCHER, "catch-all matched %s", domain)
        return True
    if pattern.startswith(".") and domain.endswith(pattern):  # suffix-match
        logger.log(LL_DOMAINMATCHER, "suffix pattern %s matched %s", pattern, domain)
        return True
    if domain == pattern:  # exact match
        logger.log(LL_DOMAINMATCHER, "exact match of pattern %s and %s", pattern, domain)
        return True
    logger.log(LL_DOMAINMATCHER, "no match of pattern %s and %s", pattern, domain)
    return False


class MapMatcher:
    """
    Abstract base class for all matchers
    """
    @abstractmethod
    def matches(self, s):
        raise NotImplementedError


class MapMatcherRua(MapMatcher):
    """
    Matcher that expects a domain name to match a pattern
    """
    def __init__(self, domainsuffix):
        self.domainsuffix = domainsuffix
    def matches(self, s:str):
        return _domain_match(s, self.domainsuffix)


class MapMatcherHttp(MapMatcher):
    """
    Matcher that expects a HTTPS URL and extracts the hostname to match a domain pattern
    """
    def __init__(self, domainsuffix):
        self.domainsuffix = domainsuffix
    def matches(self, s:str):
        parsed = urllib.parse.urlparse(urllib.parse.unquote(s))
        return _domain_match(parsed.hostname, self.domainsuffix)


class MapMatcherMail(MapMatcher):
    """
    Matcher that expects an email address and extracts the hostname to match a domain pattern
    """
    def __init__(self, domainsuffix):
        self.domainsuffix = domainsuffix
    def matches(self, s:str):
        s = "mailto://" + utility.remove_prefix(s, "mailto:")   # work-around to make urllib.parse extract hostname
        parsed = urllib.parse.urlparse(urllib.parse.unquote(s))
        try:
            return _domain_match(parsed.hostname, self.domainsuffix)
        except Exception as e:
            logger.exception("Error parsing email address %s into user '%s', host '%s' and %s: %s",
                       s, parsed.username, parsed.hostname, parsed, e)
            return False


class MapMatcherGenericRegexp(MapMatcher):
    """
    Matcher that matches a regexp against anything
    Can be used for all three map types because this Matcher acts on the whole string
    and does not need to extract the domain part in different ways
    """
    def __init__(self, pattern):
        try:
            self.cpattern = re.compile(pattern)
        except Exception as e:
            raise MapParseError(f"Could not compile regexp match '{pattern}'")
    def matches(self, s:str):
        return self.cpattern.match(s) is not None  # force match return type to boolean via "is not None"


class InvalidDestinationScheme(Exception):
    """
    An invalid URI scheme was passed into the mapping
    """
    pass


class UnsupportedDestinationScheme(Exception):
    """
    An unsupported URI scheme was the result after the first mapping
    """
    pass


class MapParseError(Exception):
    """
    Error during parsing a map
    """
    pass


def _parse_map_entry(line:str, linenr: int, map_name: str) -> Union[Tuple[str, str, MapAction], Tuple[None, None, None]]:
    """
    Parses one line of a map configuration file
    :param line: The line to be parsed
    :type line: str
    :param linenr: The number of the line
    :type linenr: int
    :param map_name: The name of the map
    :type map_name: str
    :return: A tuple of the match type, pattern to be matched and the MapAction to be performed in case of a match
    :rtype:
    """
    log_prefix = f"{map_name} line {linenr}:"
    line = line.strip()
    if line == "":
        return None, None, None
    if line.startswith("#"):
        return None, None, None
    parts = line.split(maxsplit=2)
    if len(parts) < 2:
        raise MapParseError(f"{log_prefix} Missing action")
    part_match = parts[0]
    # check part_match for ":" to support different match type in the future like "regexp:", "ip:", "whois:"
    match_components = part_match.split(sep=":", maxsplit=1)
    match_type = "domain"  # without a "matchtype:" prefix assume "domain:"
    if len(match_components) > 1:
        match_type = match_components[0]
        part_match = match_components[1]
    if match_type not in ['domain', 'regexp']:  # catch wrong types here already to report map name and line number
        raise MapParseError(f"{log_prefix} Unsupported match type '{match_components[0]}'")
    # provide empty third part
    part_action = parts[1]
    if len(parts) <3:
        part_rest=""
    else:
        part_rest = parts[2]

    if part_action == "ACCEPT":
        if part_rest != "":
            raise MapParseError(f"{log_prefix} Map action ACCEPT does not accept additional parameters")
        action = MapActionAccept()
    elif part_action == "DISCARD":
        if part_rest != "":
            raise MapParseError(f"{log_prefix} Map action DISCARD does not accept additional parameters")
        action = MapActionDiscard()
    elif part_action == "REPLACE":
        if part_rest == "":
            raise MapParseError(f"{log_prefix} Map action REPLACE needs additional parameters")
        action = MapActionReplace(part_rest.split())
    elif part_action == "APPEND":
        if part_rest == "":
            raise MapParseError(f"{log_prefix} Map action APPEND needs additional parameters")
        action = MapActionAppend(part_rest.split())
    elif part_action == "REGEXP":
        regexp_params = part_rest.split()
        n = len(regexp_params)
        if n != 2:
            raise MapParseError(f"{log_prefix} Map action REGEXP needs 2 additional parameters but got {n}")
        action = MapActionRegexpTransform(regexp_params[0], regexp_params[1])
    else:
        raise MapParseError(f"{log_prefix} Unknown action {part_action}")
    return match_type, part_match, action


class DestinationMap:
    def __init__(self):
        self.ruamap = []
        self.mailmap = []
        self.httpmap = []

    def add_rua_mapping(self, match_type:str, pattern:str, action:MapAction, linenr:int):
        if match_type == "domain":
            matcher = MapMatcherRua(pattern)
        elif match_type == "regexp":
            matcher = MapMatcherGenericRegexp(pattern)
        else:
            raise MapParseError(f"Cannot instantiate matcher for match type '{match_type}'")
        self.ruamap.append(DestinationMapEntry(matcher, action, linenr))

    def add_http_mapping(self, match_type:str, pattern:str, action:MapAction, linenr:int):
        if match_type == "domain":
            matcher = MapMatcherHttp(pattern)
        elif match_type == "regexp":
            matcher = MapMatcherGenericRegexp(pattern)
        else:
            raise MapParseError(f"Cannot instantiate matcher for match type '{match_type}'")
        self.httpmap.append(DestinationMapEntry(matcher, action, linenr))

    def add_mail_mapping(self, match_type:str, pattern:str, action:MapAction, linenr:int):
        if match_type == "domain":
            matcher = MapMatcherMail(pattern)
        elif match_type == "regexp":
            matcher = MapMatcherGenericRegexp(pattern)
        else:
            raise MapParseError(f"Cannot instantiate matcher for match type '{match_type}'")
        self.mailmap.append(DestinationMapEntry(matcher, action, linenr))

    def read_from_files(self, rua_map_name:str, mail_map_name:str, http_map_name:str):
        if rua_map_name is not None and rua_map_name != "":
            rua_map_io = open(rua_map_name, "r")
        else:
            rua_map_io = StringIO()
        if mail_map_name is not None and mail_map_name != "":
            mail_map_io = open(mail_map_name, "r")
        else:
            mail_map_io = StringIO()
        if http_map_name is not None and http_map_name != "":
            http_map_io = open(http_map_name, "r")
        else:
            http_map_io = StringIO()
        self.read_from_ios(rua_map_io, mail_map_io, http_map_io)

    def read_from_ios(self, rua_map_io, mail_map_io, http_map_io):
        self._read_one_map(rua_map_io, "rua map", DestinationMap.add_rua_mapping)
        self._read_one_map(mail_map_io, "mail map", DestinationMap.add_mail_mapping)
        self._read_one_map(http_map_io, "http map", DestinationMap.add_http_mapping)

    def _read_one_map(self, map_io, map_name, adder_func):
        linenr = 0
        for line in map_io:
            linenr += 1
            (match_type, pattern,action) = _parse_map_entry(line, linenr, map_name)
            if pattern is not None and action is not None:
                adder_func(self, match_type, pattern, action, linenr)
                logger.debug("Added line %d to map %s", linenr, map_name)
            elif pattern is None and action is None:
                pass
            else:
                raise MapParseError("Internal error: Pattern xor action is missing while expecting both or none")
        logger.debug("Parsed %d lines for %s", linenr, map_name)

    @staticmethod
    def pre_flight_check(destinations):
        # pre-flight check if destinations are valid "https:" or "mailto:", we need to avoid a smuggled in "directory:"
        for d in destinations:
            if d.startswith("https:"):
                pass
            elif d.startswith("mailto:"):
                pass
            else:
                raise InvalidDestinationScheme(d)
        return True

    def map_destination(self, domain, destinations, logger):
        self.pre_flight_check(destinations)
        logger.info("LOGTEST domain:%s destinations:%s", domain, destinations)
        for m in self.ruamap:
            if m.matcher.matches(domain):
                nds = m.action.result(destinations)
                logger.info("Destination rewrite: tlsrpt-record-map line %d changed %s to %s", m.linenr, destinations, nds)
                destinations = nds
                break
        # mangle each single destination depending on its type
        result_destinations = []
        for d in destinations:
            if d.startswith("directory:"):
                result_destinations.append(d)
            elif d.startswith("https:"):
                result_destinations.extend(DestinationMap._map(self.httpmap, "http-upload-map", d, logger))
            elif d.startswith("mailto:"):
                result_destinations.extend(DestinationMap._map(self.mailmap, "mail-destination-map" , d, logger))
            else:
                raise UnsupportedDestinationScheme(d)
        return result_destinations

    @staticmethod
    def _map(themap, mapname, destination, logger):
        for m in themap:
            if m.matcher.matches(destination):
                nds = m.action.result((destination,))  # new destinations
                logger.info("Destination rewrite: %s line %d changed %s to %s", mapname, m.linenr, destination, nds)
                return nds  # return the modified destination which can be a list of zero, one or more elements
        return (destination,)  # return the unmodified destination as a list of one element
