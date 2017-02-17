vmware-vspc
===========

Virtual Serial Port Concentrator for use in the vSphere environment. It collects
serial console logs from VMs which have configured virtual serial port pointing
to it.

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

where ``vspc_host`` is the host where VSPC runs and ``vspc_thumbprint`` is the SHA1 thumbprint of the configured certificate.

Usage with Devstack
-------------------

There is a devstack plugin, so simply add this to your ``local.conf``::

    [[local|localrc]]
    enable_plugin vmawre-vspc https://github.com/openstack/vmware-vspc
