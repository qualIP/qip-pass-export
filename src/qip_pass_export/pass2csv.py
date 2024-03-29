#!/usr/bin/env python
"""
pass2csv: Exports passwords from pass to CSV format

This software is distributed by qualIP Software under the GNU GENERAL PUBLIC
LICENSE v3 in the hope that others may find it useful too.

The original source and a copy of the GPLv3 license can be found here:
https://github.com/qualIP/qip-pass-export
"""

import argparse
import csv
import io
import os
import re
import sys
import types
from pathlib import Path

try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"


def main():
    parser = argparse.ArgumentParser(
        prog="pass2csv",
        description="Exports passwords from pass to CSV format",
    )
    parser.add_argument("-V", "--version",
                        action="version", version="%(prog)s " + __version__)
    parser.add_argument("passfiles",
                        metavar="passfile", nargs=argparse.ONE_ORMORE, type=Path,
                        help="Password file(s) (*.gpg) to export")
    args = parser.parse_args()

    try:
        import gnupg
    except ImportError as err:
        print(err, file=sys.stderr)
        print("The python-gnupg module is required to run this software.", file=sys.stderr)
        sys.exit(1)
    gpg = gnupg.GPG()
    gpg.encoding = "utf-8"

    # https://help.passbolt.com/faq/start/import-passwords
    # Using Csv (BitWarden) format
    csv_fields = (
        "description",
        "folder",
        "favorite",  # unused
        "type",  # unused
        "name",
        "notes",
        "fields",  # unused
        "reprompt",  # unused
        "login_uri",
        "login_username",
        "login_password",
        "login_totp",  # unused
    )
    csvwriter = csv.DictWriter(sys.stdout, fieldnames=csv_fields)
    csvwriter.writeheader()

    for passfile in args.passfiles:
        relfile = passfile
        try:
            relfile = relfile.absolute().relative_to(Path.home() / ".password-store")
        except ValueError:
            try:
                relfile = relfile.absolute().relative_to(Path.home())
            except ValueError:
                pass
        if passfile.suffix == ".gpg":
            with open(passfile, "rb") as fp:
                indata = gpg.decrypt_file(fp)
            assert indata.ok
            indata = str(indata)
            indata = io.StringIO(indata)
            csvrow = types.SimpleNamespace(**{k: "" for k in csv_fields})
            csvrow.notes = []
            for iline, line in enumerate(indata, start=1):
                line = line.rstrip("\r\n")
                if iline == 1:
                    csvrow.login_password = line
                    continue
                m = not csvrow.login_uri and re.match(
                    r"(?i)^(?:URL|URI)(?: *1)? *: *(?P<content>.*)$", line
                )
                if m:
                    content = m.group("content").strip()
                    if content:
                        if not re.match(r"(?i)^[a-z]+://", content):
                            content = "https://" + content
                        csvrow.login_uri = content
                    continue
                m = not csvrow.login_username and re.match(
                    r"(?i)^(?:Login|Username) *: *(?P<content>.*)$", line
                )
                if m:
                    content = m.group("content").strip()
                    if content:
                        csvrow.login_username = content
                    continue
                csvrow.notes.append(line)
            csvrow.name = relfile.stem
            csvrow.folder = os.fspath(relfile.parent)
            csvrow.notes = "\n".join(csvrow.notes)
            csvwriter.writerow(csvrow.__dict__)
            csvrow = None
        else:
            raise NotImplementedError(os.fspath(passfile))


if __name__ == "__main__":
    main()
