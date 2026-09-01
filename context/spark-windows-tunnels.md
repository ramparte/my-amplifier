# Spark-to-Windows Tunnel Policy

Direct Windows-to-Spark access never works, including through Tailscale. For
every Spark service exposed to a Windows or WSL user, follow this operational
contract proactively; do not wait for the user to request tunnel setup or
repair.

1. **Consult the authority.** Read
   `/home/ramparte/dev/ANext/dgx-spark-setup/TUNNEL-ARCHITECTURE.md` before
   allocating or repairing a route. Its allocation ledger is authoritative.
2. **Allocate safely.** Use an identity-mapped port in the inclusive
   `8400-8500` range. Recheck both the live Spark listeners and the ledger
   immediately before allocation; an unlisted port is not presumed free.
3. **Publish on the same port.** Bind the Spark service to `127.0.0.1:N`, or
   place a Spark-side loopback proxy on `127.0.0.1:N`, where `N` is the
   allocated port. Never make the WSL tunnel translate local port `N` to a
   different Spark port.
4. **Install, repair, and maintain the tunnel proactively.** Use the versioned,
   one-command Concern OS installer at
   `concern-os/tunnel/spark-tunnel.ps1`; check status and repair a missing or
   degraded persistent tunnel without waiting to be asked. Use `-RangeOnly` on
   `travelerPC`; use the full/default profile on `WILaptopRebuild`. Do not
   introduce Windows `portproxy` or an ad hoc forwarding scheme.
5. **Record the allocation.** Update the canonical ledger whenever a port is
   allocated, reassigned, or retired. Never silently change a published port;
   explain the conflict and the new allocation first.
6. **Verify the exact route.** Test the complete URL, including its path and
   query string, at all three hops: Spark `127.0.0.1:N`, WSL `localhost:N`, and
   Windows `localhost:N`. Repair the failed layer and repeat all three checks.
7. **Report the Windows URL.** Give the user
   `http://localhost:<port>/...`. Never report a raw Spark hostname, Spark
   Tailscale address, WSL address, or unforwarded service port as the usable
   Windows URL.

If terminating a WSL distribution or restarting it leaves the tunnel absent,
repair the existing versioned installation rather than changing ports or
inventing a new forwarding path, then repeat the three-hop verification.
