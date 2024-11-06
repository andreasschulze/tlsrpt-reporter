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

import os
import sys

def manpage_error(msg, got):
    print("ERROR:", msg, "but got", got)
    exit(1)


def mprint(mp, line):
    print(line, file=mp)


def rettype(function):
    return ("int", "")


def create_manpage_stub(srcdir, function_name, clines):
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
        mprint(mp, f"int {function_name}({sep.join(params)})")
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
        mprint(mp, f"The {function_name} function returns 0 on success and a combined error code on failure.")
        mprint(mp, f"The combined error code can be analyzed with the _tlsrpt_strerror_ function.")
        mprint(mp, f"")
        mprint(mp, f"== See also")
        mprint(mp, f"man:tlsrpt_strerror[3], man:tlsrpt_error_code_is_internal[3]")
        mprint(mp, f"")
        mprint(mp, f"")
        mprint(mp, f"")
        mprint(mp, f"")
        mprint(mp, f"")
        mprint(mp, f"")


def create_manpage_stubs(docfile, srcdir):
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
                create_manpage_stub(srcdir, function_name, clines)
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

    create_manpage_stubs(sys.argv[1], sys.argv[2])
