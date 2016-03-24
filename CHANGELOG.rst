Changelog
=========

1.1.0 (unreleased)
------------------

**Features:**

- Add base log path option: `-b` `--log-base`.
- Log postfix option: `-p` `--log-postfix`.
- Auto alias generation: `-a` `--alias-level`.
- Add support for default /var/log/messages datetime format files with
  `-ml [FILE [FILE]]`

**Bugfixes:**

- #13: timestamp output adding 000 to microseconds.

1.0.3 (2015-11-08)
------------------

- Initial release as os-log-merger.
