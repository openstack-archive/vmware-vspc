vmware-vspc
===========

Virtual Serial Port Concentrator for use in the vSphere environment. It collects
serial console logs from VMs which have configured virtual serial port pointing
to it.

Usage
=====

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