oslogmerger
===========

What is oslogmerger?
~~~~~~~~~~~~~~~~~~~~

oslogmerger stands for OpenStack LOG merger, it's a tool designed to take a
bunch of openstack logs across different projects, and merge them in a single
file, ordered by time entries.

It should work as long as the logs are based on oslo logger output.

Limitations
~~~~~~~~~~~

This tool is not able to properly (or meaningfully) merge logs if your servers
are not time synced to a common source.

This is a naive implementation, not smart at all, instead of runtime comparing
input dates as they come from log files, we create a big memory list with
all log lines, sort them, and spite them out. This can be improved.

How to install
~~~~~~~~~~~~~~
pip install oslogmerger

How to use it
~~~~~~~~~~~~~

.. code:: bash

     oslogmerger ../bz/1257567/40-os1ctrl01/var/log/neutron/server.log:NS1 \
                 ../bz/1257567/50-os1ctrl02/var/log/neutron/server.log:NS2 \
                 ../bz/1257567/40-os1ctrl01/var/log/neutron/openvswitch-agent.log:OVS1 \
                 ../bz/1257567/50-os1ctrl02/var/log/neutron/openvswitch-agent.log:OVS2


Please note that the :NS1, :NS2, :OVS1, :OVS2 are aliases and can be omitted,
and in such case, the extra column used to associate a log file to a log line
will use the original file path instead of the [ALIAS]

The previous example would produce something like this::

    2015-08-25 09:37:15.463000 [NS1] 15062 DEBUG neutron.context [req-b751a750-f5d8-4b6e-9af3-82d143ef9416 None] Arguments dropped when creating context: {u'project_name': None, u'tenant': None} __init__ /usr/lib/python2.7/site-packages/neutron/context.py:83
    2015-08-25 09:37:15.463000 [NS1] 15062 DEBUG neutron.plugins.ml2.db [req-b751a750-f5d8-4b6e-9af3-82d143ef9416 None] get_ports_and_sgs() called for port_ids [u'4136d577-e02f-47c1-b543-f0bfd65ef85e', u'5d5ea109-4807-4df3-bef4-b5d89c3ffebc', u'6adcffbf-09d5-4a85-9339-9d6beb2bf82c', u'6b4d7b51-c87d-483e-9606-0e2a54ad8184', u'743ccaa6-7ed9-4195-aabd-3d55006338e1', u'dc662767-61a5-4807-b2ed-a7c76b541fd6', u'4decdd33-6f13-46df-b2f0-d9ff99878514', u'34b826df-9787-443c-9bef-084374827a85', u'7bbc404b-3df7-498a-b6fb-e81f9370a19f', u'c12e6e06-ff6a-44dc-b75f-78ec55dd3dd3', u'586cd86d-59d0-434b-ab27-76975ce5abc4', u'79b33879-3232-4b3a-a27c-c0a79da10379', u'ba6a28cc-9851-4cd7-acae-40034a19c761', u'05c4115a-da58-41db-b3f7-7326e1a22971'] get_ports_and_sgs /usr/lib/python2.7/site-packages/neutron/plugins/ml2/db.py:224
    2015-08-25 09:37:15.463000 [OVS1] 12613 DEBUG neutron.agent.linux.utils [req-588c942a-6526-464f-a447-782a5e2d436a None]
                                        Command: ['sudo', 'neutron-rootwrap', '/etc/neutron/rootwrap.conf', 'ovs-vsctl', '--timeout=10', 'list-ports', 'br-int']
                                        Exit code: 0
                                        Stdout: 'ha-2cdba01d-e4\nha-44dca3a9-44\nha-499d3db7-97\nha-55a19f5e-ef\nha-b2d04f15-f2\nha-b5b271a1-d8\nha-fa58d644-81\nint-br-enp7s0\nint-br-ex\nqr-34b826df-97\nqr-5d5ea109-48\nqr-6adcffbf-09\nqr-743ccaa6-7e\nqr-79b33879-32\nqr-c12e6e06-ff\nqr-dc662767-61\n'

References to http url files instead of local files is also supported. Files
will be cached locally to avoid re-downloading on next runs.
