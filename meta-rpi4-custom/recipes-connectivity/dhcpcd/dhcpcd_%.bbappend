do_install:append() {
    # Ensure domain_name and domain_search options are requested and applied
    printf '\n# Request and apply domain name from DHCP\noption domain_name, domain_name_servers, domain_search\n' \
        >> ${D}${sysconfdir}/dhcpcd.conf
}
