# Feixiao Alpha 1.0.4

Experimental diagnostics build for RTL8821CE/macOS testing.

## Changes

- Mirrors deauthentication/disassociation events into the `rtw88ctl log` ring buffer.
- Logs 802.11 Action frame category/action/source information.
- Detects and logs 802.11v WNM BSS Transition Management Requests.
- Parses 802.11v Neighbor Report candidate entries, including candidate preference.
- Detects and logs 802.11k Neighbor Report Responses.
- Keeps existing BlockAck handling unchanged.

## Scope

This alpha is diagnostic only. It does not yet perform automatic 802.11k/802.11v roaming or BSS transitions.

Target test setup: RTL8821CE on macOS Tahoe 26.7, including mesh/repeater environments.
