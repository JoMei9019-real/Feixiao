# Feixiao Alpha 1.0.5

Experimental WPA2/WPA3 transition-mode compatibility build.

## Changes

- Parses RSN AKM suites and detects WPA2/WPA3 transition networks (PSK + SAE).
- Parses RSN capabilities and records MFPC/MFPR (802.11w PMF capability/requirement).
- Selects an explicit WPA2-PSK/CCMP fallback profile on transition networks.
- Reuses the exact same selected RSN IE in both the Association Request and EAPOL M2.
- Refuses PMF-required networks cleanly instead of entering an unsupported half-associated state.
- Keeps Alpha 1.0.4 802.11k/v and deauth/disassoc diagnostics.
- Fixes an existing association-response use-after-free (the skb was freed before status/AID were read), reducing kernel-panic/random-association risk.

## Safety scope

This alpha does not implement SAE/WPA3 or 802.11w protected management frames.
It deliberately avoids new firmware/PCIe control paths, dynamic kernel allocations, or hot-reload logic.
