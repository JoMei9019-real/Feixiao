# Feixiao Alpha 1.0.7 Diagnostics

Performance-instrumentation build based on Alpha 1.0.6.

## Goal

Investigate the remaining low-bandwidth problem without changing the Wi-Fi data path.

The diagnostics are informed by upstream Feixiao issue #2 and by the
chvsolucoes/Feixiao performance experiments. In particular, this build tracks
TX queue/backpressure behavior together with RX delivery and the existing
hardware/software ring pointers.

## Changes

- Keep the Alpha 1.0.6 WPA2/WPA3 transition fallback and Group Key Rekey work.
- Add 5-second PERF snapshots:
  - submitted TX packets
  - delivered RX packets and bytes
  - interrupt count
  - cumulative TX stall/resume count
  - BE ring available slots
  - current stalled state
- Persist TXSTATE diagnostics into the rtw88ctl log ring.
- Emit TXSTATE every 5 seconds so RX_rp/RX_hwwp and HW/SW TX ring movement can
  be correlated with throughput tests.
- Keep the normal per-packet RX flush path.
- Do not enable RX batching.
- Do not change DMA, watchdog, rate adaptation, A-MPDU, VHT channel width,
  backpressure thresholds, firmware control, or interrupt behavior.

## Test

Enable debug logging:

    sudo rtw88ctl debug 3

Run a speed test or a sustained transfer for at least 20-30 seconds, then:

    sudo rtw88ctl log | grep -Ei 'PERF 5s|TXSTATE|deauth|disassoc|group rekey|EAPOL'

For latency correlation, run a router ping in parallel.

This branch is diagnostics-only. Its measurements should guide a later,
single-variable A/B performance patch.
