# Copyright 2018 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import print_function

import argparse
from datetime import datetime, timedelta
import hashlib
import heapq
import itertools
import os
import re
import sys
import tempfile
import time

import dateutil.parser
import dateutil.tz
from six.moves.urllib.request import urlopen
import pbr.version

__version__ = pbr.version.VersionInfo('os-log-merger').version_string()

EXTRALINES_PADDING = " " * 40
CACHE_DIR = "%s/oslogmerger-cache/" % tempfile.gettempdir()

# Shorten paths
PATH_MAP = {
    'nova': 'N',
    'glance': 'G',
    'cinder': 'C',
    'keystone': 'K',
    'neutron': 'Q',
    'swift': 'S',
    'heat': 'H',
    'ceilometer': 'T',
}

# Shorten filenames
FILE_MAP = {
    # Cinder
    'scheduler': 'SCH',
    'volume': 'VOL',
    'backup': 'BAK',
    'cinder-manage': 'MNG',
    # Nova
    'nova-api': 'API',
    'nova-cert': 'CRT',
    'cert': 'CRT',
    'nova-compute': 'CPU',
    'compute': 'CPU',
    'nova-conductor': 'COND',
    'conductor': 'COND',
    'nova-consoleauth': 'CAUTH',
    'consoleauth': 'CAUTH',
    'network': 'NET',
    'nova-manage': 'MNG',
    'nova-scheduler': 'SCH',
    'nova-novncproxy': 'NOVNC',
    'keystone': 'KEY',
    'horizon': 'HRZN',
    # Neutron
    'registry': 'REG',
    'openvswitch-agent': 'AGT',
    'dhcp-agent': 'DHCP',
    'l3-agent': 'L3',
    'lbaas-agent': 'LBAAS',
    'metadata-agent': 'META',
    'metering-agent': 'MTR',
    'server': 'API',
    'linuxbridge-agent': 'SVC',
    'netprobe': 'NET',
    # Heat
    'heat-api': 'API',
    'heat-engine': 'ENG',
    'heat-manage': 'MNG',
    # Ceilometer
    'agent-notification': 'NOTIF',
    'alarm-evaluator': 'EVAL',
    'alarm-notifier': 'ALRM',
    'ceilometer-dbsync': 'DBSY',
    'central': 'CENT',
    'collector': 'COLL',
}


class LogEntry(object):
    def __init__(self, alias, dt, data, dt_str=None):
        self.alias = alias
        self.dt = dt
        self.data = data

        if dt_str is not None:
            self.dt_str = dt_str
        else:
            self.dt_str = self.dt.strftime('%Y-%m-%d %H:%M:%S.%f')

    def append_line(self, line):
        self.data += EXTRALINES_PADDING + line

    def __cmp__(self, other):
        return (self._cmp(self.dt, other.dt) * 2 +
                self._cmp(self.alias, other.alias))

    def __lt__(self, other):
        return self.dt < other.dt or (self.dt == other.dt and
                                      (self.alias < other.alias))

    def __str__(self):
        return '%s [%s] %s' % (self.dt_str, self.alias, self.data.rstrip('\n'))

    @staticmethod
    def _cmp(a, b):
        return (a > b) - (a < b)


class LogParser(object):
    def __init__(self, filename, cfg):
        self.cfg = cfg

    def parse_line(self, line):
        raise NotImplementedError


class StrptimeParser(LogParser):
    date_format = None

    def __init__(self, filename, cfg):
        super(StrptimeParser, self).__init__(filename, cfg)
        self.date_format_words = len(self.date_format.split(' '))

    def parse_line(self, line):
        # Split the input line into words, up to <date_format_words>. Data is
        # anything after that. Join the first <date_format_words> words to
        # recreate the date.
        dt_str = line.split(' ', self.date_format_words)
        data = dt_str.pop()
        dt_str = ' '.join(dt_str)

        dt = datetime.strptime(dt_str, self.date_format)
        dt = dt.replace(tzinfo=self.cfg.default_tz)

        # +1 to remove the separator so we don't have 2 spaces on output
        return dt, dt_str, data


class OSLogParser(StrptimeParser):
    """OpenStack default log: 2016-02-01 10:22:59.239"""
    date_format = '%Y-%m-%d %H:%M:%S.%f'


class MsgLogParser(StrptimeParser):
    """Message format: Oct 15 14:11:19"""
    date_format = '%b %d %H:%M:%S'

    def __init__(self, filename, cfg):
        super(MsgLogParser, self).__init__(filename, cfg)
        stat = os.stat(filename)

        # TODO: handle the case where log file was closed after a year boundary
        log_modified = datetime.fromtimestamp(stat.st_mtime)
        self.year = log_modified.year

    def parse_line(self, line):
        dt, dt_str, data = super(MsgLogParser, self).parse_line(line)
        return dt.replace(self.year), dt_str, data


class MsgLogWithMicrosecondsParser(MsgLogParser):
    """Message format: Mar 13 15:19:08.525234"""
    date_format = '%b %d %H:%M:%S.%f'


def make_tzinfo(name, sign, hours, minutes):
    tzoffset = int(minutes) * 60 + int(hours) * 3600
    if sign == '-':
        tzoffset = -tzoffset
    elif sign != '+':
        raise ValueError('Invalid timezone sign: %s' % sign)

    return dateutil.tz.tzoffset(name, tzoffset)


class LibvirtdParser(LogParser):
    """Message format: 2017-09-18 18:08:49.163+0000:
       OR:             2017-09-18T18:08:49.216429Z qemu-kvm:

    This parser handles libvirtd.log and libvirt domain logs. Domain logs
    contain a mixture of libvirt and qemu logs, hence the 2 log formats.
    """
    LIBVIRT = re.compile('(\d{4})-(\d{2})-(\d{2}) '  # Date
                         '(\d{2}):(\d{2}):(\d{2})\.(\d{3})'  # Time
                         '('
                         '([+-])(\d{2})(\d{2})'  # Timezone
                         '):\s*')

    QEMU = re.compile('(\d{4})-(\d{2})-(\d{2})T'  # Date
                      '(\d{2}):(\d{2}):(\d{2})\.(\d+)Z\s*')  # Time

    def parse_line(self, line):
        m = self.LIBVIRT.match(line)
        if m is not None:
            return self._parse_libvirt(line, m)

        m = self.QEMU.match(line)
        if m is not None:
            return self._parse_qemu(line, m)

        raise ValueError('Unsupported format')

    def _parse_libvirt(self, line, match):
        groups = list(match.groups())

        (tzminutes, tzhours, tzsign, tzstr) = (
                groups.pop(), groups.pop(), groups.pop(), groups.pop())
        tzinfo = make_tzinfo(tzstr, tzsign, tzhours, tzminutes)

        dt = datetime(
            year=int(groups.pop(0)),
            month=int(groups.pop(0)),
            day=int(groups.pop(0)),
            hour=int(groups.pop(0)),
            minute=int(groups.pop(0)),
            second=int(groups.pop(0)),
            microsecond=int(groups.pop(0)) * 1000,
            tzinfo=tzinfo,
        )

        # Strip colon and trailing whitespace from full date string
        dt_str = match.group(0).rstrip()[:-1]

        return dt, dt_str, line[match.end():]

    def _parse_qemu(self, line, match):
        groups = list(match.groups())

        dt = datetime(
            year=int(groups.pop(0)),
            month=int(groups.pop(0)),
            day=int(groups.pop(0)),
            hour=int(groups.pop(0)),
            minute=int(groups.pop(0)),
            second=int(groups.pop(0)),
            microsecond=int(groups.pop(0)),
            # The trailing 'Z' means UTC
            tzinfo=dateutil.tz.tzutc(),
        )

        # Strip trailing whitespace from full date string
        dt_str = match.group(0).rstrip()

        return dt, dt_str, line[match.end():]


class RawSyslog(LogParser):
    """Raw syslog: <183>1 2017-04-03T21:48:21.781459-03:30"""

    # NOTE(mdbooth): Parsing the date in this regexp and reconstructing it
    # manually is a *lot* faster than passing the whole string to
    # dateutil.parse(). Didn't try strptime due to having to parse tzinfo
    # manually anyway.
    HEADER = re.compile('<\d+>\d+\s'
                        '('
                        '(\d{4})-(\d{2})-(\d{2})T'  # Date
                        '(\d{2}):(\d{2}):(\d{2})\.(\d+)'  # Time
                        '('
                        '([+-])(\d{2}):(\d{2})'  # Timezone
                        ')'
                        ')\s*')

    def parse_line(self, line):
        m = RawSyslog.HEADER.match(line)
        if m is None:
            raise ValueError("Not syslog packet")

        groups = list(m.groups())
        dt_str = groups.pop(0)

        (tzminutes, tzhours, tzsign, tzstr) = (
                groups.pop(), groups.pop(), groups.pop(), groups.pop())
        tzinfo = make_tzinfo(tzstr, tzsign, tzhours, tzminutes)

        dt = datetime(
            year=int(groups.pop(0)),
            month=int(groups.pop(0)),
            day=int(groups.pop(0)),
            hour=int(groups.pop(0)),
            minute=int(groups.pop(0)),
            second=int(groups.pop(0)),
            microsecond=int(groups.pop(0)),
            tzinfo=tzinfo,
        )

        return dt, dt_str, line[m.end():]


class TSLogParser(LogParser):
    """Timestamped log: [275514.814982]"""

    def __init__(self, filename, cfg):
        super(TSLogParser, self).__init__(filename, cfg)

        stat = os.stat(filename)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        timestamp = self._get_last_timestamp(filename)
        if timestamp is None:
            raise ValueError("Didn't find timestamp")
        self.start_date = mtime - timedelta(seconds=timestamp)

    @classmethod
    def _get_last_timestamp(cls, filename):
        result = None
        with open(filename, 'r') as f:
            file_size = os.fstat(f.fileno()).st_size
            # We will jump to the last KB so we don't have to read all file
            offset = max(0, file_size - 1024)
            f.seek(offset)
            for line in f:
                try:
                    __, result = cls._read_timestamp(line)
                except ValueError:
                    continue

            return result

    @staticmethod
    def _read_timestamp(line):
        # skip leading '['
        start = 1
        end = line.index(']')

        if end < start:
            raise ValueError

        return end, float(line[start:end])

    def parse_line(self, line):
        end, timestamp = self._read_timestamp(line)
        dt = self.start_date + timedelta(seconds=timestamp)
        dt = dt.replace(tzinfo=self.cfg.default_tz)
        return dt, line[:end + 1], line[end + 1:]


class LogFile(object):
    def _detect_format(self, filename, cfg):
        parsers = []
        for cls in list(LOG_TYPES.values()) + DETECTED_LOG_TYPES:
            if cls is None:
                continue

            try:
                parsers.append(cls(filename, cfg))
            except ValueError:
                # Don't consider the parser if we can't instantiate it for this
                # file
                pass

        # Try to parse the first few lines with each parser in turn, returning
        # the first to successfully parse a line
        for line in itertools.islice(self._lines(), 0, 5):
            for parser in parsers:
                try:
                    parser.parse_line(line)

                    # It worked!
                    print('Detected %s as %s' %
                          (filename, parser.__class__.__name__),
                          file=sys.stderr)
                    return parser
                except ValueError:
                    pass

        raise ValueError("Failed to detect format of %s" % self.alias)

    def __init__(self, filename, alias, cfg, parser_cls=None):
        if filename.startswith("http://"):
            self.filename = self._cached_download(filename)
        else:
            self.filename = filename

        self.alias = alias

        if parser_cls is None:
            self.parser = self._detect_format(filename, cfg)
        else:
            self.parser = parser_cls(filename, cfg)

    def _lines(self):
        with open(self.filename, 'r') as logfile:
            while True:
                line = logfile.readline()
                if line == "":
                    break

                line.replace('\0', ' ')
                yield line

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
        http_in = urlopen(url)
        file_out = open(path, 'w')
        file_out.write(http_in.read())
        file_out.close()

        # Set the file time to the one from the URL
        info = http_in.info()
        m_date = info.getdate('date')
        mtime = time.mktime(m_date)
        os.utime(path, (mtime, mtime))

        http_in.close()
        return path

    def __iter__(self):
        entry = None
        for line in self._lines():
            try:
                dt, dt_str, data = self.parser.parse_line(line)

                # If we successfully parsed a line, it means that we've
                # finished appending un-timestamped lines to the previous entry
                if entry:
                    yield entry

                entry = LogEntry(self.alias, dt, data, dt_str=dt_str)

            except ValueError:
                # it's probably a non-dated line, or a garbled entry, just
                # append to the entry extra info
                if entry:
                    entry.append_line(line)

        # We reached EOF, to return the in-progress entry
        if entry is not None:
            yield entry


# Log file formats with command line options
LOG_TYPES = {
    'logfiles_detect': None,
    'logfiles_o': OSLogParser,
    'logfiles_m': MsgLogParser,
    'logfiles_ms': MsgLogWithMicrosecondsParser,
    'logfiles_t': TSLogParser,
}


# Log file formats which can only be auto-detected
DETECTED_LOG_TYPES = [
    LibvirtdParser,
    RawSyslog,
]


def process_logs(cfg):
    logs = []

    paths_aliases = {}
    paths_parsers = {}
    for arg_name, parser_cls in LOG_TYPES.items():
        for filename in getattr(cfg, arg_name):
            path, alias, is_url = get_path_and_alias(filename, cfg.log_base,
                                                     cfg.log_postfix)
            paths_aliases[path] = (filename, alias, is_url)
            paths_parsers[path] = parser_cls

    # NOTE(mdbooth): I feel like generate_aliases should take a single path,
    # which would make this loop much tidier. I don't want to unpick it right
    # now, though.
    aliases = generate_aliases(paths_aliases, cfg)

    logs = []
    for path, parser_cls in paths_parsers.items():
        try:
            logs.append(LogFile(path, aliases[path], cfg,
                                parser_cls=parser_cls))
        except ValueError:
            print('WARNING: %s unable to determine format, ignoring' % path,
                  file=sys.stderr)

    entry_iters = [iter(log) for log in logs]
    for entry in heapq.merge(*entry_iters):
        print(entry)


def get_path_and_alias(filename, log_base, log_postfix):
    # check if filename has an alias for log output, in the form of
    # /path/filename:alias
    filename_and_alias = filename.rsplit(':', 1)
    filename = log_base + filename_and_alias[0] + log_postfix
    alias = filename_and_alias[1:]

    is_url = False
    if filename == 'http' and alias and alias[0].startswith('//'):
        filename = filename_and_alias[0] + ':' + filename_and_alias[1]
        alias = filename_and_alias[2:]
        is_url = True

    return filename, alias[0] if alias else None, is_url


# If we are in level 3, we must reduce all paths to the minimum
def reduce_strings(strings):
    num_strs = len(strings)
    if num_strs == 1:
        return {strings[0]: strings[0][-1]}

    # Convert each string to a list
    str_list = [list(s) for s in strings]
    result = [s.pop() for s in str_list]

    while len(set(result)) != num_strs:
        for i, s in enumerate(str_list):
            if s:
                letter = s.pop()
                str_list[i].insert(0, letter)
                result[i] = letter + result[i]
    result = [''.join(r) for r in result]
    return {strings[i]: s for i, s in enumerate(result)}


def reduce_tree(tree):
    # If there are no subdirectories we have finished with this subtree
    if not len(tree[1]):
        return tree
    # Reduce the names of all subdirectories in this directory
    reduced = reduce_strings(list(tree[1].keys()))
    # For each of those subdirectories reduce subtrees using the reduced name
    # but we still use the original diretory's name as the directory key.
    return (tree[0],
            {k: reduce_tree((reduced[k], v[1], v[2]))
             for k, v in tree[1].items()},
            tree[2])


def generate_aliases(aliases, cfg):
    """Generate aliases according to command line and level generation."""
    def process(aliased, what, method):
        checking = {k: method(f) for k, f in what.items()}
        if all_unique_values(aliased, checking):
            return checking
        return what

    def remove_extension(filename):
        return filename.rsplit('.', 1)[0]

    def map_file(processed_and_not):
        # Get the filename and split the extension if we haven't already
        filename = processed_and_not[0][-1].rsplit('.', 1)
        mapping = FILE_MAP.get(filename[0], filename[0])
        # I f we hadn't removed the extension it was because we would be
        # creating duplicates, so replacing with an alias must also preserve
        # the extension.
        if len(filename) == 2:
            mapping = mapping + '.' + filename[1]
        return (processed_and_not[0][:-1], mapping)

    def map_dir(processed_and_not):
        # If there are more path elements try to map the next directory
        if processed_and_not[0]:
            elem = processed_and_not[0][-1]
            if elem in PATH_MAP:
                return (processed_and_not[0][:-1],
                        PATH_MAP[elem] + '-' + processed_and_not[1])
        return processed_and_not

    level = cfg.alias_level
    if level <= 1:
        return {p: a or (f if level else p)
                for p, (f, a, u) in aliases.items()}

    aliased = {p: a for p, (f, a, u) in aliases.items() if a}
    # For URLs we will remote the http:// part
    non_aliased = {p: f[7:] if u else f
                   for p, (f, a, u) in aliases.items() if not a}

    # Remove file extesions if they were not specified with the postfix and
    # they don't make duplicates
    if not cfg.log_postfix:
        non_aliased = process(aliased, non_aliased, remove_extension)

    # Split the path, and mark it all as not processed
    for k, v in non_aliased.items():
        split = v.split('/')
        # If it's an absolute path we remove the split string and add / to the
        # first directory
        if split and not split[0]:
            del split[0]
            split[0] = '/' + split[0]
        non_aliased[k] = (split, '')

    non_aliased = process(aliased, non_aliased, map_file)
    non_aliased = process(aliased, non_aliased, map_dir)

    # Remove all paths that are not unique within their respective directories
    # For convenience we'll use a dictionary as a tree
    tree = (None, {}, [])
    for k, v in non_aliased.items():
        last_tree = tree
        for directory in v[0]:
            last_tree[1].setdefault(directory, (directory, {}, []))
            last_tree = last_tree[1][directory]
        # We have to store the filename in the last directory we visited
        last_tree[2].append(v[1])

    # Reduce all paths as much as possible if alias level is 3
    if level == 3:
        tree = reduce_tree(tree)

    # Cleanup directories from the non processed part
    for k, v in non_aliased.items():
        last_tree = tree
        path = []
        for directory in v[0]:
            # If a directory is non relevant (there is only 1 directory and no
            # files in it) we can remove it from the resulting path.
            if len(last_tree[1]) > 1 or last_tree[2]:
                path.append(last_tree[1][directory][0])
            last_tree = last_tree[1][directory]
        non_aliased[k] = (path, v[1])

    # Add aliased items back
    result = {k: reconstruct_path(v) for k, v in non_aliased.items()}
    result.update({k: v for k, v in aliased.items()})
    return result


def reconstruct_path(path):
    result = '/'.join(path[0])
    if result:
        return result + '/' + path[1]
    return path[1]


def all_unique_values(*args):
    original_len = sum(len(a) for a in args)

    values = set()
    for a in args:
        vals = list(a.values())
        if vals and isinstance(vals[0], tuple):
            vals = [reconstruct_path(v) for v in vals]
        values.update(vals)

    return original_len == len(values)


class TimezoneAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")

        super(TimezoneAction, self).__init__(option_strings, dest, **kwargs)

    @staticmethod
    def parse(tzstr):
        # Format: +HHMM
        if len(tzstr) != 5:
            raise ValueError('Invalid timezone: %s' % tzstr)

        sign = tzstr[0]
        hours = tzstr[1:3]
        minutes = tzstr[3:5]

        return make_tzinfo(tzstr, sign, hours, minutes)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, self.parse(values))


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

Y-m-d H:M:S.mmm ............
Y-m-d H:M:S.mmm ............
[  extra line info .....      ]

    Logs with default /var/log/messages datetime format (Oct 15 14:11:19)
can optionally be merged as well using "--msg-logs" or "-ml"
options.  Year will be taken from the last modified time of the file.

    Logs with timestamp format -[    0.003036]- are also supported with
options "--timestamp-logs" or "-tl".  Since timestamp many times will
not take epoc time as the source of the timestamp but the time the
system started, the initial datetime will be calculated by substracting
from the file modified datetime the last timestamp in the file.

    These log files will aso be affected by log base directory and log
postfix.
"""

    general_epilog = """
    If an alias has been defined in the command line it will have precedence
over any kind of filename reduction.

    There are 4 levels for generating an alias by reducing the filename when
one has not been provided:'
    - 0: means disabled, and will return the full file.
         Ex:
            $ oslogmerger -b /var/log/cinder -p .log api scheduler
                2016-02-01 10:23:34.680 [/var/log/cinder/api.log] ...
                2016-02-01 10:24:34.680 [/var/log/cinder/scheduler.log] ...
    - 1: use filename without prefix or postfix.
            $ oslogmerger -a1 -b /var/log/cinder -p .log api scheduler
                2016-02-01 10:23:34.680 [api] ...
                2016-02-01 10:24:34.680 [scheduler] ...
    - 2: same as level 1, but it will also remove filename extensions if they
         have not been defined with the postfix, will reduce log filenames
         (volume=VOL, scheduler=SCH, backup=BAK, ...) and immediate directory
         (cinder=C, nova=N, neutron=Q, ...), and will remove all non relevant
         directories.
         Ex:
            $ oslogmerger -a2 node?/var/log/{cinder,nova}/*.log
                2016-02-01 10:23:34.680 [node1/C-API] ...
                2016-02-01 10:24:34.680 [node1/C-SCH]
                2016-02-01 10:25:34.680 [node1/C-VOL]
                2016-02-01 10:26:34.680 [node1/N-API]
                2016-02-01 10:27:34.680 [node2/N-CPU]
    - 3: same as level 2, plus reduce directory names
         Ex:
            $ oslogmerger -a3 node?/var/log/{cinder,nova}/*.log
                2016-02-01 10:23:34.680 [1/C-API] ...
                2016-02-01 10:24:34.680 [1/C-SCH]
                2016-02-01 10:25:34.680 [1/C-VOL]
                2016-02-01 10:26:34.680 [1/N-API]
                2016-02-01 10:27:34.680 [2/N-CPU]
"""
    parser = MyParser(description=general_description,
                      epilog=general_epilog, argument_default='',
                      formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--log-base ', '-b', dest='log_base',
                        help='Base path for all the log files')
    parser.add_argument('--log-postfix ', '-p', dest='log_postfix',
                        help='Append to all the log files path')
    parser.add_argument('logfiles_detect', nargs='*',
                        metavar='log_file[:ALIAS]',
                        help='Log file (auto-detect format)')
    parser.add_argument('--alias-level', '-a', type=int, default=0,
                        dest='alias_level',
                        help='Level of smart alias naming (0-3)')
    parser.add_argument('--min-memory', '-m', default=False,
                        action='store_true', dest='limit_memory',
                        help='This option is deprecated and has no effect')
    parser.add_argument('--os-logs', '-ol', default=[], nargs='+',
                        dest='logfiles_o', metavar='file[:ALIAS]',
                        help='Openstack log files')
    parser.add_argument('--msg-logs', '-ml', default=[], nargs='+',
                        dest='logfiles_m', metavar='file[:ALIAS]',
                        help='Message log files with format: Oct 15 14:11:19')
    parser.add_argument('--msg-logs-ms', '-ms', default=[], nargs='+',
                        dest='logfiles_ms', metavar='file[:ALIAS]',
                        help='Message log files with format: '
                             'Mar 13 15:19:08.525234')
    parser.add_argument('--timestamp-logs', '-tl', default=[], nargs='+',
                        dest='logfiles_t', metavar='file[:ALIAS]',
                        help='Message log files with timestamp: [   0.003036]')
    parser.add_argument('--default-tz', '-tz',
                        default=TimezoneAction.parse('+0000'),
                        dest='default_tz', action=TimezoneAction,
                        help="Default timezone for timestamps without a "
                             "timezone, specified as UTC offset. "
                             "Default: +0000")

    return parser.parse_args()


def main():
    cfg = parse_args()
    process_logs(cfg)


if __name__ == "__main__":
    main()
