from __future__ import print_function
import argparse
from datetime import datetime
import hashlib
import os
import sys
import tempfile
import urllib2


__version__ = '1.0.3'

EXTRALINES_PADDING = " " * 40
CACHE_DIR = "%s/oslogmerger-cache/" % tempfile.gettempdir()


class OpenStackLog:
    def __init__(self, filename):
        self._open(filename)

    def _open(self, filename):
        self._filename = filename
        if filename.startswith("http://"):
            filename = self._cached_download(filename)
        self._file = open(filename, 'r')

    def _url_cache_path(self, url):
        md5 = hashlib.md5()
        md5.update(url)
        return CACHE_DIR + md5.hexdigest() + ".log"

    def _ensure_cache_dir(self):
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)

    def _cached_download(self, url):
        self._ensure_cache_dir()
        path = self._url_cache_path(url)
        if os.path.isfile(path):
            print("CACHED: %s at %s" % (url, path), file=sys.stderr)
            return path
        print("DOWNLOADING: %s to %s" % (url, path), file=sys.stderr)
        http_in = urllib2.urlopen(url)
        file_out = open(path, 'w')
        file_out.write(http_in.read())
        file_out.close()
        http_in.close()
        return path

    def _extract_with_date(self, line):
        try:
            # TODO(mangelajo): We support the default log format
            #                  so far, but we may need to discover
            #                  different ones.
            chunks = line.split(" ")
            datetime_str = ' '.join(chunks[:2])
            # this is likely to be not necessary, we can just compare
            # strings, and that's going to be faster than parsing
            # and regenerating later, but, could be useful when mixing
            # log and date formats.
            date_object = datetime.strptime(
                  datetime_str, "%Y-%m-%d %H:%M:%S.%f")
            pid, level = chunks[2], chunks[3]
            rest = ' '.join(chunks[4:])
            return (date_object, self._filename, pid, level, rest)
        except IndexError:
            return None

    def log_entries(self):
        entry = None
        while True:
            line = self._file.readline()
            if line == "":
                break
            try:
                new_entry = self._extract_with_date(line)
                if new_entry is None:
                    continue
                if entry:
                    yield entry
                entry = new_entry
            except ValueError:
                # it's a non-dated line, just append to the entry
                # extra info
                if entry:
                    (date_object, filename, pid, level, rest) = entry
                    entry = (date_object, filename, pid, level,
                             rest + EXTRALINES_PADDING + line)

        if entry:
            yield entry


def process_logs(log_base, files, log_postfix):
    all_entries = []
    filename_alias = {}
    for filename in files:
        # check if filename has an alias for log output, in the form of
        # /path/filename:alias
        filename_and_alias = filename.split(':')
        filename = log_base + filename_and_alias[0] + log_postfix
        alias = filename_and_alias[1:]

        if filename == 'http' and alias and alias[0].startswith('//'):
            filename = filename_and_alias[0] + ':' + filename_and_alias[1]
            alias = filename_and_alias[2:]

        if alias:
            filename_alias[filename] = "[%s]" % alias[0]
        else:
            filename_alias[filename] = filename

        # read the log
        oslog = OpenStackLog(filename)
        for entry in oslog.log_entries():
            all_entries.append(entry)

    sorted_entries = sorted(all_entries, key=lambda log_entry: log_entry[0])
    for entry in sorted_entries:
        (date_object, filename, pid, level, rest) = entry
        print (' '.join(
                [date_object.strftime("%Y-%m-%d %H:%M:%S.%f"),
                 filename_alias[filename], pid,
                 level, rest]).rstrip('\n'))


def parse_args():
    class MyParser(argparse.ArgumentParser):
        """Class to print verbose help on error."""
        def error(self, message):
            self.print_help()
            sys.stderr.write('\nerror: %s\n' % message)
            sys.exit(2)

    general_description = """os-log-merger tool

    The tool will read all the log files, sort entries based on datetime,
and output the ordered sequence of log lines via stdout. A new column is
appended after datetime containing the file path of the log line, or the
alias. Use the aliases if you want shorter line lengths.

    Logs are expected to contain lines in the following format:

Y-m-d H:M:S.mmm PID LOG-LEVEL ............
Y-m-d H:M:S.mmm PID LOG-LEVEL ............
[  extra line info .....      ]
"""

    parser = MyParser(description=general_description, version=__version__,
                      argument_default='',
                      formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--log-base ', '-b', dest='log_base',
                        help='Base path for all the log files')
    parser.add_argument('--log-postfix ', '-p', dest='log_postfix',
                        help='Append to all the log files path')
    parser.add_argument('logfiles', nargs='+', metavar='log_file',
                        help='File in the format of log_file[:ALIAS]')
    return parser.parse_args()


def main():
    cfg = parse_args()
    process_logs(cfg.log_base,
                 cfg.logfiles,
                 cfg.log_postfix)


if __name__ == "__main__":
    main()
