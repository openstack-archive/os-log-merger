from __future__ import print_function
from datetime import datetime
import hashlib
import os
import sys
import tempfile
import urllib2


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
            chunks = line.split(" ")
            datetime_str = ' '.join(chunks[:2])
            # this is likely to be not necessary, we can just compare
            # strings, and that's going to be faster than parsing
            # and regenerating later
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
                (date_object, filename, pid, level, rest) = entry
                entry = (date_object, filename, pid, level,
                         rest + EXTRALINES_PADDING + line)

        if entry:
            yield entry


def help():
    print ("""oslogmerger tool

usage instructions:
    oslogmerger /path/log_file1[:ALIAS] /path/log_file2[:ALIAS2] ..

    The tool will read all the log files, sort entries based on datetime,
and output the ordered sequence of log lines via stdout. A new column is
appended after datetime containing the file path of the log line, or the
alias. Use the aliases if you want shorter line lengths.

    Logs are expected to contain lines in the following format:

Y-m-d H:M:S.mmm PID LOG-LEVEL ............
Y-m-d H:M:S.mmm PID LOG-LEVEL ............
[  extra line info .....      ]
""")


def process_logs(files):
    if len(files) == 0:
        help()
        return 1
    all_entries = []
    filename_alias = {}
    for filename in files:

        # check if filename has an alias for log output, in the form of
        # /path/filename:alias
        filename_and_alias = filename.split(':')
        filename = filename_and_alias[0]
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
    return 0


def main():
    sys.exit(process_logs(sys.argv[1:]))

if __name__ == "__main__":
    main()
