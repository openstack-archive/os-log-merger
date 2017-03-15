from __future__ import print_function
import argparse
from datetime import datetime, timedelta
import hashlib
import os
import sys
import tempfile
import time
import urllib2


__version__ = '1.1.0'

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
    'openvswitch-agent': 'VSWI',
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
    'compute': 'CPT',
}


class LogEntry(object):
    separator = ' '
    date_format = None
    _date_parse_msg = 'unconverted data remains: '

    def __init__(self, **kwargs):
        self._date_length = None
        self.__dict__.update(**kwargs)

    @classmethod
    def get_init_args(cls, filename):
        return {}

    def prepare_line(self, line):
        return line.replace('\0', ' ')

    def parse_date(self, line):
        try:
            dt = datetime.strptime(line, self.date_format)
        except ValueError as e:
            if not e.args[0].startswith(self._date_parse_msg):
                raise
            prepared_date_length = (len(line) - len(e.args[0]) +
                                    len(self._date_parse_msg))
            dt = datetime.strptime(line[:prepared_date_length],
                                   self.date_format)
            self._date_length = prepared_date_length
        return dt

    def _calculate_date_length(self):
        return len(self.date.strftime(self.date_format))

    @property
    def date_length(self):
        if not self._date_length:
            self._date_length = self._calculate_date_length()
        return self._date_length

    @classmethod
    def factory(cls, filename, line, **kwargs):
        self = cls(**kwargs)

        self.filename = filename
        if not line:
            raise ValueError

        # Prepare the line for date parsing
        prepared_line = self.prepare_line(line)

        # Extract the datetime
        self.date = self.parse_date(prepared_line)

        if (len(line) == self.date_length or
                line[self.date_length] != self.separator):
            raise ValueError

        self.date_str = line[:self.date_length]
        # +1 to remove the separator so we don't have 2 spaces on output
        self.data = line[self.date_length + 1:]
        return self

    def append_line(self, line):
        self.data += EXTRALINES_PADDING + line

    def __cmp__(self, other):
        return cmp(self.date, other.date)


class LogFile(object):
    log_entry_class = LogEntry

    @staticmethod
    def factory(cls, filename):
        instance = LogFile(filename)
        instance.log_entry_class = cls
        instance.entry_kwargs = cls.get_init_args(filename)
        return instance

    def __init__(self, filename):
        self.open(filename)

    def open(self, filename):
        self._filename = filename
        if filename.startswith("http://"):
            filename = self._cached_download(filename)

        self._file = open(filename, 'r')
        stat = os.stat(filename)
        self.mtime = datetime.fromtimestamp(stat.st_mtime)

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

        # Set the file time to the one from the URL
        info = http_in.info()
        m_date = info.getdate('date')
        mtime = time.mktime(m_date)
        os.utime(path, (mtime, mtime))

        http_in.close()
        return path

    def __iter__(self):
        self.entry = None
        self.next_entry = None
        return self

    def _readline(self, entry):
        while True:
            line = self._file.readline()
            if line == "":
                return entry, None

            try:
                new_entry = self.log_entry_class.factory(self._filename,
                                                         line,
                                                         **self.entry_kwargs)
                if new_entry is None:
                    continue
                if entry:
                    return entry, new_entry
                entry = new_entry

            except Exception:
                # it's probably a non-dated line, or a garbled entry, just
                # append to the entry extra info
                if entry:
                    entry.append_line(line)

    def __next__(self):
        return self.next()

    def next(self):
        self.entry, self.next_entry = self._readline(self.next_entry)
        if self.entry is None:
            raise StopIteration()
        return self.entry

    def peek(self):
        return self.entry

    def __cmp__(self, other):
        if other.peek() is None or self.peek() is None:
            if self.peek() is None:
                return 0 if other.peek() is None else 1
            return -1

        if (other.peek() or self.peek()) is None:
            return 0 if self.peek() is None else -1
        return cmp(self.peek(), other.peek())


class MsgLogEntry(LogEntry):
    """Message format: Oct 15 14:11:19"""
    date_format = '%Y%b %d %H:%M:%S'

    @classmethod
    def get_init_args(cls, filename):
        kwargs = super(MsgLogEntry, cls).get_init_args(filename)
        stat = os.stat(filename)
        kwargs['file_year'] = datetime.fromtimestamp(stat.st_mtime).year
        return kwargs

    def prepare_line(self, line):
        # TODO: If year of file creation and file last modification are
        # different we should start with the cration year and then change to
        # the next year once the months go back.
        line = super(MsgLogEntry, self).prepare_line(line)
        return '%s%s' % (self.file_year, line)

    def _calculate_date_length(self):
        return super(MsgLogEntry, self)._calculate_date_length() - 4


class OSLogEntry(LogEntry):
    """OpenStack default log: 2016-02-01 10:22:59.239"""
    date_format = '%Y-%m-%d %H:%M:%S.%f'

    def _calculate_date_length(self):
        return super(OSLogEntry, self)._calculate_date_length() - 3


class TSLogEntry(LogEntry):
    """Timestamped log: [275514.814982]"""

    @classmethod
    def get_init_args(cls, filename):
        kwargs = super(TSLogEntry, cls).get_init_args(filename)
        stat = os.stat(filename)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        timestamp = cls._get_last_timestamp(filename)
        kwargs['start_date'] = mtime - timedelta(seconds=timestamp)
        return kwargs

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
        start = line.index('[') + 1
        end = line.index(']')

        if end < start:
            raise ValueError

        return end, float(line[start:end])

    def parse_date(self, date_str):
        end, timestamp = self._read_timestamp(date_str)
        self._date_length = end + 1
        return self.start_date + timedelta(seconds=timestamp)


def process_logs_limit_memory_usage(logs):
    oslogs = [iter(log) for log in logs]

    def process_entry(entry_iterable):
        try:
            next(entry_iterable)
        except StopIteration:
            # There are no more entries in the iterable, we can remove it
            # from the list to process
            oslogs.remove(entry_iterable)

    for log in oslogs:
        process_entry(log)

    while oslogs:
        entry_iterable = min(oslogs)
        result = entry_iterable.peek()
        if result is None:
            break
        yield result
        process_entry(entry_iterable)


def process_logs_memory_hog(logs):
    all_entries = []
    # read all the logs
    for log in logs:
        for entry in log:
            all_entries.append(entry)

    sorted_entries = sorted(all_entries)
    for entry in sorted_entries:
        yield entry


LOG_TYPES = [
    ('logfiles', OSLogEntry),
    ('logfiles_m', MsgLogEntry),
    ('logfiles_t', TSLogEntry),
]


def process_logs(cfg):
    filename_alias = {}
    logs = []
    for arg_name, entry_cls in LOG_TYPES:
        for filename in getattr(cfg, arg_name):
            path, alias, is_url = get_path_and_alias(filename,
                                                     cfg.log_base,
                                                     cfg.log_postfix)
            filename_alias[path] = (filename, alias, is_url)
            logs.append(LogFile.factory(entry_cls, path))

    alias = generate_aliases(filename_alias, cfg)

    if cfg.limit_memory:
        method = process_logs_limit_memory_usage
    else:
        method = process_logs_memory_hog

    for entry in method(logs):
        print('%s [%s] %s' % (entry.date_str, alias[entry.filename],
              entry.data.rstrip('\n')))


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
    reduced = reduce_strings(tree[1].keys())
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
        vals = a.values()
        if vals and isinstance(vals[0], tuple):
            vals = [reconstruct_path(v) for v in vals]
        values.update(vals)

    return original_len == len(values)


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

    parser = MyParser(description=general_description, version=__version__,
                      epilog=general_epilog, argument_default='',
                      formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--log-base ', '-b', dest='log_base',
                        help='Base path for all the log files')
    parser.add_argument('--log-postfix ', '-p', dest='log_postfix',
                        help='Append to all the log files path')
    parser.add_argument('logfiles', nargs='+', metavar='log_file[:ALIAS]',
                        help='OpenStack log file.')
    parser.add_argument('--alias-level', '-a', type=int, default=0,
                        dest='alias_level',
                        help='Level of smart alias naming (0-3)')
    parser.add_argument('--min-memory', '-m', default=False,
                        action='store_true', dest='limit_memory',
                        help='Limit memory usage')
    parser.add_argument('--msg-logs', '-ml', default=[], nargs='+',
                        dest='logfiles_m', metavar='file[:ALIAS]',
                        help='Message log files with format: Oct 15 14:11:19')
    parser.add_argument('--timestamp-logs', '-tl', default=[], nargs='+',
                        dest='logfiles_t', metavar='file[:ALIAS]',
                        help='Message log files with timestamp: [   0.003036]')

    return parser.parse_args()


def main():
    cfg = parse_args()
    process_logs(cfg)


if __name__ == "__main__":
    main()
