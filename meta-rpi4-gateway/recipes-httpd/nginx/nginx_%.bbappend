FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

# Enable HTTP/2 module in addition to the defaults
PACKAGECONFIG:append = " http2"
