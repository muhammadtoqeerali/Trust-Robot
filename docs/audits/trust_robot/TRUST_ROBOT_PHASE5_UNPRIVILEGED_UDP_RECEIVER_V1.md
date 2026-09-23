# TRUST-ROBOT Phase-5 Unprivileged Dual UDP Receiver V1

## Motivation

Passive packet capture is unavailable to the current workstation account.

A loopback feasibility audit independently verified that an ordinary
`AF_INET` / `SOCK_DGRAM` user-space receiver can receive both prospective
LiDAR UDP channels without root, sudo, `CAP_NET_RAW` or tcpdump.

This layer therefore replaces passive packet sniffing as the candidate raw
payload acquisition mechanism.

## Evidence preserved

For each delivered UDP datagram the receiver preserves:

- exact UDP payload bytes;
- stream identity;
- datagram index;
- payload byte offset in the stream archive;
- payload byte count;
- payload SHA-256;
- source IPv4 address;
- source UDP port;
- explicitly supplied destination bind address and destination UDP port;
- host userspace monotonic receive time;
- host userspace wall-clock receive time.

The payload archives contain only UDP payload bytes.

Datagram boundaries are preserved by metadata offset/length records.

## What is not preserved

The receiver is not a passive packet sniffer.

It does not preserve:

- Ethernet headers;
- IP headers;
- UDP headers.

It only receives datagrams that the operating system delivers to the bound
UDP socket.

## Host-time boundary

Host userspace receive timestamps are transport provenance only.

They are not claimed to be:

- physical LiDAR measurement time;
- synchronization evidence;
- interval-binding evidence.

No timing tolerance, offset or interpolation is selected.

## Packet-loss boundary

Receipt of UDP datagrams does not establish absence of packet loss.

Datagram count is descriptive acquisition evidence only.

No packet-count or packet-rate health threshold is introduced.

## Publication integrity

A fresh acquisition-session directory is required.

Stream payload and metadata artifacts are first written to same-directory
`.partial` files.

Normal successful completion uses the already-frozen executor-safety
publication contract:

- fsync;
- SHA-256 before publication;
- same-directory atomic publication;
- directory fsync;
- SHA-256 after publication;
- exact pre/post hash equality.

A stream with zero captured datagrams is not published as raw evidence by
this receiver.

That behavior is fail-closed acquisition handling, not a health-state label.

## Test-recovery note

The initial targeted run reached 27/28 PASS.

The sole failure was a test implementation false positive: the test searched
the entire module text for the substring `sudo`, while the module
intentionally contains the metadata declaration `requires_sudo: false`.

The production config and receiver module were not changed.

The repaired test instead inspects Python AST for the actual socket
constructor and requires exactly `socket.AF_INET` plus `socket.SOCK_DGRAM`,
while continuing to reject `SOCK_RAW` and `AF_PACKET`.

## Current scientific state

Loopback user-space dual-stream receiving is implemented and tested.

Real VLP-32C receiving is not yet verified.

No actual workstation bind address is selected.

No actual VLP-32C measurement port is selected.

No actual VLP-32C position port is selected.

No real sensor address is selected.

No real output root is selected.

No sensor has been contacted.

Raw real-sensor capture artifacts: **0**.

Accepted baseline-nominality sources: **0**.

Accepted health-supervision sources: **0**.

Real health labels: **0**.

Interval binding remains unselected.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

Real-sensor execution remains unauthorized.

Phase-5 exit evidence remains **NOT YET SATISFIED**.
