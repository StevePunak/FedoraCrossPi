# meta-rpi4-gateway

The image for stilgar, the home gateway Pi: dnsmasq, nginx with the
gateway-admin UI, Tailscale, and Let's Encrypt via acme.sh.

## Owed reflash

These changes are committed here and applied to the running stilgar by
hand. The next reflash makes them part of the image. None of them is
urgent.

- **2026-10-02: no SSH over the tailnet.** `sshd.socket` refuses
  connections from `100.64.0.0/10` and `fd7a:115c:a1e0::/48`, so SSH works
  only from the LAN. Remote shells go through archie. On the running
  stilgar the drop-in was written by hand; after the reflash it comes from
  the image.

Remove an entry once a reflash has carried it.
