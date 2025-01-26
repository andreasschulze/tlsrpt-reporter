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

import os
import sys


def mprint(mp, line):
    """
    Print to a file with reorder3ed arguments for better code visualization
    :param mp: the manpage´s file object
    :param line: the line to print into the manpage source file
    """
    print(line, file=mp)


def see_also(function_name):
    """
    Manually adjust the "see also" links for the manpage
    :param function_name: The name of the function described in the manpage
    :return: a list of manpage references to put into the "see also" section
    """
    refs = ["man:tlsrpt_strerror[3]", "man:tlsrpt_error_code_is_internal[3]"]
    special_refs = {"tlsrpt_strerror": ["man:tlsrpt_error_code_is_internal[3]", "man:tlsrpt_errno_from_error_code[3]"],
                    "tlsrpt_error_code_is_internal": ["man:tlsrpt_strerror[3]", "man:tlsrpt_errno_from_error_code[3]"],
                    "tlsrpt_errno_from_error_code": ["man:tlsrpt_error_code_is_internal[3]", "man:tlsrpt_strerror[3]"],
                    "tlsrpt_open": ["man:tlsrpt_close[3]", *refs],
                    "tlsrpt_close": ["man:tlsrpt_open[3]", *refs],
                    "tlsrpt_init_delivery_request": ["man:tlsrpt_cancel_delivery_request[3]",
                                                     "man:tlsrpt_finish_delivery_request[3]", *refs],
                    "tlsrpt_cancel_delivery_request": ["man:tlsrpt_init_delivery_request[3]",
                                                       "man:tlsrpt_finish_delivery_request[3]", *refs],
                    "tlsrpt_finish_delivery_request": ["man:tlsrpt_init_delivery_request[3]",
                                                       "man:tlsrpt_cancel_delivery_request[3]", *refs],
                    "tlsrpt_init_policy": ["man:tlsrpt_finish_policy[3]", *refs],
                    "tlsrpt_finish_policy": ["man:tlsrpt_init_policy[3]", *refs],
                    "tlsrpt_set_blocking": ["man:tlsrpt_set_nonblocking[3]"],
                    "tlsrpt_set_nonblocking": ["man:tlsrpt_set_blocking[3]"],
                    "tlsrpt_set_malloc_and_free": ["man:tlsrpt_open[3]", "man:tlsrpt_init_delivery_request[3]"],
                    }
    return special_refs.get(function_name, refs)


def rettype(function_name):
    """
    Manually adjust information not yet extractable from the API documntation.
    :param function_name: The name of the function to get information about
    :return: A dict of the function´s return type and a descriptive text
    """
    voiddesc = "has no return value."
    return_types = {"tlsrpt_strerror": {"type": "const char*", "desc": "returns a static string describing the error."},
                    "tlsrpt_set_blocking": {"type": "void", "desc": voiddesc},
                    "tlsrpt_set_nonblocking": {"type": "void", "desc": voiddesc},
                    "tlsrpt_set_malloc_and_free": {"type": "void", "desc": voiddesc},
                    "tlsrpt_get_socket": {"type": "int", "desc": "returns the socket file descriptor used within a "
                                                                 "tlsrpt_connection_t."},
                    "tlsrpt_error_code_is_internal": {"type": "int", "desc": "returns if the error code is internal to "
                                                                             "the TLSRPT library."},
                    }
    return return_types.get(function_name, {"type": "int", "desc": "returns 0 on success and a combined error code on "
    "failure.\nThe combined error code can be analyzed with the _tlsrpt_strerror_ function."})


def create_manpage_source(srcdir, function_name, clines, docfile):
    """
    Create manpage for function function_name into directory srcdir using the asciidoc lines in list clines.
    :param srcdir: The directory where the manpage spource file will be created
    :param function_name: The name of the function described in this manpage
    :param clines: The lines extracted from the API documentation for further parsing
    :param docfile: The API documentation file this manpage source is created from
    """
    if function_name is None:
        return
    function_name.strip()
    line = clines[0].replace("\n", "")

    params = []
    sep = ", "
    if line == "Parameters:::":
        clines.pop(0)
        while True:
            line = clines.pop(0).replace("\n", "")
            line.strip()
            if line == "":
                break
            param = line.partition("::")[0]
            param = param.strip().rstrip()
            params.append(param)
    print("manpage for", f"{function_name}({sep.join(params)})")

    short = clines[0].replace("\n", "")
    short = short.partition(" function ")[2]
    short = short.replace(".", "")

    with open(os.path.join(srcdir, function_name + ".adoc"), mode="w") as mp:
        mprint(mp, f"// !!! DO NOT EDIT THIS FILE !!!")
        mprint(mp, f"// !!! THIS FILE IS AUTOMATICALLY CREATED FROM {os.path.basename(docfile)} !!!")
        mprint(mp, f"// !!! DO NOT EDIT THIS FILE !!!")
        mprint(mp, f"//")
        mprint(mp, f"= {function_name}(3)")
        mprint(mp, f"Boris Lohner")
        mprint(mp, f"v0.5.0")
        mprint(mp, f":doctype: manpage")
        mprint(mp, f":manmanual: {function_name}")
        mprint(mp, f":mansource: {function_name}")
        mprint(mp, f":man-linkstyle: pass:[blue R < >]")
        mprint(mp, f"")
        mprint(mp, f"== Name")
        mprint(mp, f"")
        mprint(mp, f"{function_name} - {short}")
        mprint(mp, f"")
        mprint(mp, f"== Synopsis")
        mprint(mp, f"")
        mprint(mp, f"#include <tlsrpt.h>")
        mprint(mp, f"")
        ret = rettype(function_name)
        mprint(mp, f"{ret['type']} {function_name}({sep.join(params)})")
        mprint(mp, f"")
        mprint(mp, f"== Description")
        mprint(mp, f"")
        for dline in clines:
            dline = dline.replace("\n", "")
            dline.strip()
            mprint(mp, dline)
        mprint(mp, f"")
        mprint(mp, f"== Return value")
        mprint(mp, f"")
        mprint(mp, f"The {function_name} function {ret['desc']}")
        mprint(mp, f"")
        mprint(mp, f"== See also")
        mprint(mp, ", ".join(see_also(function_name)))
        mprint(mp, f"")
        mprint(mp, f"")
        mprint(mp, f"")
        mprint(mp, f"")
        mprint(mp, f"")
        mprint(mp, f"")


def create_manpage_sources(docfile, srcdir):
    """
    Read docfile in asciidoc format and extract function descriptions into separate source files for the manpages.
    :param docfile: The API documentation document
    :param srcdir: The directory where the manpage spource files will be created
    """
    print(f"Creating manpage sources into {srcdir} from {docfile}")
    if not os.path.isdir(srcdir):
        print(f"ERROR: '{srcdir}' is not a directory", file=sys.stderr)
        sys.exit(2)
    if not os.path.isfile(docfile):
        print(f"ERROR: '{docfile}' is not a file", file=sys.stderr)
        sys.exit(2)
    clines = []
    function_name = None
    with open(docfile) as doc:
        lines = doc.readlines()
        lines.append("=")  # add a new dummy section to flush out the last man page
        for line in lines:
            tags = line.partition(" ")
            if tags[0].startswith("="):
                create_manpage_source(srcdir, function_name, clines, docfile)
                clines = []
                function_name = None
                if tags[2].startswith("`tlsrpt_"):  # NEW FUNCTION
                    function_name = tags[2].replace("`", "", 2).replace("\n", "")
            else:
                clines.append(line)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} source.adoc mansrcdir/", file=sys.stderr)
        sys.exit(2)

    create_manpage_sources(sys.argv[1], sys.argv[2])
