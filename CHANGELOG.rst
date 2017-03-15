Changelog
=========

1.1.0 (2017-03-17)
------------------

**Features:**

- Add optional reduced memory operation `-m` `--min-memory`
- Add base log path option: `-b` `--log-base`.
- Log postfix option: `-p` `--log-postfix`.
- Auto alias generation: `-a` `--alias-level`.
- Add support for default /var/log/messages datetime format files with
  `-ml [FILE [FILE]]`
- Add support for timestamped log files with `-tl [FILE [FILE]]`

**Bugfixes:**

- #13: timestamp output adding 000 to microseconds.
- lp#1672921: os-log-merger crashes on strings with null bytes

1.0.3 (2015-11-08)
------------------

- Initial release as os-log-merger.
