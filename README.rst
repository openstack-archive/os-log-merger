os-log-merger
=============

.. image:: https://img.shields.io/pypi/v/os-log-merger.svg
        :target: https://pypi.python.org/pypi/os-log-merger

.. image:: https://img.shields.io/pypi/pyversions/os-log-merger.svg
         :target: https://pypi.python.org/pypi/os-log-merger

.. image:: https://img.shields.io/:license-apache-blue.svg
         :target: http://www.apache.org/licenses/LICENSE-2.0


What is os-log-merger?
~~~~~~~~~~~~~~~~~~~~~~

os-log-merger stands for OpenStack LOG merger, it's a tool designed to take a
bunch of openstack logs across different projects, and merge them in a single
file, ordered by time entries.

It should work as long as the logs are based on oslo logger output.

Quick presentation: http://mangelajo.github.io/openstack-debugging-presentation/

Limitations
~~~~~~~~~~~

This tool is not able to properly (or meaningfully) merge logs if your servers
are not time synced to a common time source.

By default os-log-merger uses a memory hogging implementation because it
provides a considerable time reduction to complete the merging.  This
implementation loads all file contents in memory and then sorts and then
proceeds to output merged result.

For operation on memory constrained systems and with log files of considerable
sizes os-log-merger can operate on a memory conservative mode where log entries
will be read from files one by one and sorted as they come.

This memory reduction has an impact on processing speed, and will increase the
time to process the files by 25%.


How to install
~~~~~~~~~~~~~~
pip install os-log-merger

Basic Usage
~~~~~~~~~~~

.. code:: bash

    $ os-log-merger ../bz/1257567/40-os1ctrl01/var/log/neutron/server.log:NS1 \
                    ../bz/1257567/50-os1ctrl02/var/log/neutron/server.log:NS2 \
                    ../bz/1257567/40-os1ctrl01/var/log/neutron/openvswitch-agent.log:OVS1 \
                    ../bz/1257567/50-os1ctrl02/var/log/neutron/openvswitch-agent.log:OVS2


Please note that the :NS1, :NS2, :OVS1, :OVS2 are aliases and can be omitted,
and in such case, the extra column used to associate a log file to a log line
will use the original file path instead of the [ALIAS]

The previous example would produce something like this::

    2015-08-25 09:37:15.463 [NS1] 15062 DEBUG neutron.context [req-b751a750-f5d8-4b6e-9af3-82d143ef9416 None] Arguments dropped when creating context: {u'project_name': None, u'tenant': None} __init__ /usr/lib/python2.7/site-packages/neutron/context.py:83
    2015-08-25 09:37:15.463 [NS1] 15062 DEBUG neutron.plugins.ml2.db [req-b751a750-f5d8-4b6e-9af3-82d143ef9416 None] get_ports_and_sgs() called for port_ids [u'4136d577-e02f-47c1-b543-f0bfd65ef85e', u'5d5ea109-4807-4df3-bef4-b5d89c3ffebc', u'6adcffbf-09d5-4a85-9339-9d6beb2bf82c', u'6b4d7b51-c87d-483e-9606-0e2a54ad8184', u'743ccaa6-7ed9-4195-aabd-3d55006338e1', u'dc662767-61a5-4807-b2ed-a7c76b541fd6', u'4decdd33-6f13-46df-b2f0-d9ff99878514', u'34b826df-9787-443c-9bef-084374827a85', u'7bbc404b-3df7-498a-b6fb-e81f9370a19f', u'c12e6e06-ff6a-44dc-b75f-78ec55dd3dd3', u'586cd86d-59d0-434b-ab27-76975ce5abc4', u'79b33879-3232-4b3a-a27c-c0a79da10379', u'ba6a28cc-9851-4cd7-acae-40034a19c761', u'05c4115a-da58-41db-b3f7-7326e1a22971'] get_ports_and_sgs /usr/lib/python2.7/site-packages/neutron/plugins/ml2/db.py:224
    2015-08-25 09:37:15.463 [OVS1] 12613 DEBUG neutron.agent.linux.utils [req-588c942a-6526-464f-a447-782a5e2d436a None]
                                        Command: ['sudo', 'neutron-rootwrap', '/etc/neutron/rootwrap.conf', 'ovs-vsctl', '--timeout=10', 'list-ports', 'br-int']
                                        Exit code: 0
                                        Stdout: 'ha-2cdba01d-e4\nha-44dca3a9-44\nha-499d3db7-97\nha-55a19f5e-ef\nha-b2d04f15-f2\nha-b5b271a1-d8\nha-fa58d644-81\nint-br-enp7s0\nint-br-ex\nqr-34b826df-97\nqr-5d5ea109-48\nqr-6adcffbf-09\nqr-743ccaa6-7e\nqr-79b33879-32\nqr-c12e6e06-ff\nqr-dc662767-61\n'

References to http url files instead of local files is also supported. Files
will be cached locally to avoid re-downloading on next runs.

Limit memory usage
~~~~~~~~~~~~~~~~~~

We can disabled default speed optimized operation for those case were we want
to favor a small memory footprint by using option `-m` (`--min-memory`).

Common Base
~~~~~~~~~~~

In many cases we'll have a common base directory where log reside and they'll
probably share the .log extension. So for the shake of brevity os-log-merger
allows setting the base directory and postfix for all files with the `-b` and
`-p` option (`--log-base` and `--log-postfix` long options).

Example for Cinder:

.. code:: bash

    $ os-log-merger -b /var/log/cinder/ -p .log api:api scheduler:sch volume:vol


/var/log/messages
~~~~~~~~~~~~~~~~~

os-log-merger also supports /var/log/messages type of files with options `-ml`
and `--msg-logs` options.

Since the format for those files is missing year information -MAR 24 14:11:19-
the year from the last file modification will be used.

These files can also be specified with globs and they support alias definition
as well.

Beware that openstack files should be listed before `-ml` option files.

Example for Cinder:

.. code:: bash

    $ os-log-merger -b /var/log/ cinder/api.log:API -ml messages:MSG *.log


Timestamped logs
~~~~~~~~~~~~~~~~

os-log-merger also supports timestamped -[    0.003036]- with options `-tl`
and `--timestamp-logs` options.

Since timestamp many times will not take epoc time as the source of the
timestamp but the time the system started, the initial datetime will be
calculated by substracting from the file modified datetime the last timestamp
in the file.

These files can also be specified with globs and they support alias definition
as well.

Beware that openstack files should be listed before `-tl` option files.

Example for Cinder:

.. code:: bash

    $ os-log-merger -b /var/log/ cinder/api.log:API -tl dmesg:DMSG


Auto Alias
~~~~~~~~~~

As we've seen above you can easily set you alias using `:ALIAS` after each log
file, but since most of log files names and locations are well known,
os-log-merger has an auto alias feature with different levels to adapt to your
specific needs.

If an alias has been defined in the command line it will disable the auto alias
on that file.

**Level 0**

The most basic auto alias generation level is level 0, and is the default
behavior explained above, where the file path is used as an alias.

**Level 1**

Since default configuration will create considerable long aliases, you can use
level 1 when using base directory and log postfix options to remove them from
the alias.

Then the following command line:

.. code:: bash

    $ os-log-merger -a1 -b /var/log/cinder/ -p .log api scheduler volume

Would use `api`, `scheduler` and `volume` aliases::


    2016-02-01 12:11:17.573 [api] ...
    2016-02-01 12:11:17.701 [scheduler] ...
    2016-02-01 11:11:18.667 [volume] ...

**Level 2**

In some cases we may want to use globbing patterns and auto alias level 1 is no
longer useful, so you want to have the filename extensions removed as well as
the common paths and reduce the well know log filenames.

With level 2 os-log-merger will remove all common parts of the path as long as
resulting paths can still uniquely identify the files within the prefixing path.

It will also rename well known files like cinder/scheduler.log with c-sch like
in this example:

.. code:: bash

    $ os-log-merger -a2 node?/var/log/{cinder,nova}/*.log

That will give you::

    2016-02-01 10:23:34.680 [node1/C-API] ...
    2016-02-01 10:24:34.690 [node1/C-SCH] ...
    2016-02-01 10:25:34.700 [node1/C-VOL] ...
    2016-02-01 10:26:34.710 [node1/N-API] ...
    2016-02-01 10:27:34.680 [node2/N-CPU] ...

**Level 3**

Depending on the name of your non common directories in your log paths you may
want to go one step further and reduce them to the minimum instead of
preserving them unaltered.

Replacing Level 2 auto alias generation in the previous command with the same
files:

.. code:: bash

    $ os-log-merger -a3 node?/var/log/{cinder,nova}/*.log

Would result in::

    2016-02-01 10:23:34.680 [1/C-API] ...
    2016-02-01 10:24:34.690 [1/C-SCH] ...
    2016-02-01 10:25:34.700 [1/C-VOL] ...
    2016-02-01 10:26:34.710 [1/N-API] ...
    2016-02-01 10:27:34.680 [2/N-CPU] ...
