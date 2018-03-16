vmware-vspc
===========

Virtual Serial Port Concentrator for use in the vSphere environment. It collects
serial console logs from VMs which have configured virtual serial port pointing
to it. It can also accept client connections and provide interactive serial consoles
if the ``enable_clients`` option is set to ``True``. When ``enable_clients=True``
for each connected VM the program creates a server socket bound to the ``client_host``
interface and forwards the traffic between connected clients and the corresponding VM.
This effectively creates two-way communication to the VM's serial port.

There is also an admin interface running at ``admin_host:admin_port`` which allows
querying which host and port correspond to which VM. It is used by Nova for implementing
the serial console feature.

Usage with OpenStack
--------------------

Copy ``vspc.conf.sample`` as ``vspc.conf`` and edit as appropriate::

    [DEFAULT]
    debug = True
    host = 0.0.0.0
    port = 13370
    cert = cert.pem
    key = key.pem
    uri = vmware-vspc
    serial_log_dir = /opt/vmware/vspc

Then start with::

    $ vmware-vspc --config-file vspc.conf

In ``nova.conf`` add the following properties::

    [vmware]
    serial_port_service_uri = vmware-vspc
    serial_port_proxy_uri = telnets://<vspc_host>:13370#thumbprint=<vspc_thumbprint>

where ``vspc_host`` is the host where VSPC runs and ``vspc_thumbprint`` is the SHA1
thumbprint of the configured certificate.

Usage with Devstack
-------------------

There is a devstack plugin, so simply add this to your ``local.conf``::

    [[local|localrc]]
    enable_plugin vmware-vspc https://github.com/openstack/vmware-vspc
