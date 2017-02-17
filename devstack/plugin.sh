# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

NOVA_CONF=/etc/nova/nova.conf
VSPC_CONF_DIR=/etc/vmware
VSPC_CONF=$VSPC_CONF_DIR/vspc.conf
VSPC_PORT=${VSPC_PORT:-13370}
VSPC_URI=vspc-uri
VSPC_LOG_DIR=$DATA_DIR/vspc

function install_vspc {
    # save the old values of PYTHON3_VERSION and USE_PYTHON3
    # since we are going to change them
    PYTHON3_VERSION_OLD=$PYTHON3_VERSION
    USE_PYTHON3_OLD=$USE_PYTHON3
    PYTHON3_VERSION=${PYTHON3_VERSION:-3.5}
    USE_PYTHON3=True
    install_python3
    USE_PYTHON3=True PYTHON3_VERSION=$PYTHON3_VERSION $TOP_DIR/tools/install_pip.sh
    echo_summary "Installing vmware-vspc"
    setup_package $DEST/vmware-vspc -e
    USE_PYTHON3=$USE_PYTHON3_OLD
    PYTHON3_VERSION=$PYTHON3_VERSION_OLD
}

function configure_vspc {
    echo_summary "Generating VSPC certificate and key"
    sudo install -d -o $STACK_USER $VSPC_CONF_DIR
    openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 \
        -subj '/CN=devstack' -keyout $VSPC_CONF_DIR/key.pem \
        -out $VSPC_CONF_DIR/cert.pem
    THUMBPRINT=$(openssl x509 -in $VSPC_CONF_DIR/cert.pem -sha1 -noout -fingerprint | awk -F'=' '{print $2}')

    echo_summary "Creating VSPC config file"
    rm -f $VSPC_CONF
    iniset $VSPC_CONF DEFAULT debug "$ENABLE_DEBUG_LOG_LEVEL"
    iniset $VSPC_CONF DEFAULT host "$SERVICE_HOST"
    iniset $VSPC_CONF DEFAULT port "$VSPC_PORT"
    iniset $VSPC_CONF DEFAULT cert "$VSPC_CONF_DIR/cert.pem"
    iniset $VSPC_CONF DEFAULT key "$VSPC_CONF_DIR/key.pem"
    iniset $VSPC_CONF DEFAULT uri "$VSPC_URI"
    sudo install -d -o $STACK_USER $VSPC_LOG_DIR
    iniset $VSPC_CONF DEFAULT serial_log_dir "$VSPC_LOG_DIR"

    echo_summary "Configuring VSPC settings in nova.conf"
    PROXY_URI="telnets://$SERVICE_HOST:$VSPC_PORT#thumbprint=$THUMBPRINT"
    iniset $NOVA_CONF vmware serial_port_service_uri "$VSPC_URI"
    iniset $NOVA_CONF vmware serial_port_proxy_uri "$PROXY_URI"
}

function start_vspc {
    echo_summary "Starting vmware-vspc ..."
    BIN_DIR=$(get_python_exec_prefix)
    run_process vmware-vspc "$BIN_DIR/vmware-vspc --config-file $VSPC_CONF"
}

# check for service enabled
if is_service_enabled vmware-vspc; then

    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        install_vspc

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        configure_vspc

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize and start vmware-vspc
        start_vspc
    fi

    if [[ "$1" == "unstack" ]]; then
        stop_process vmware-vspc
    fi
fi

# Restore xtrace
$XTRACE

