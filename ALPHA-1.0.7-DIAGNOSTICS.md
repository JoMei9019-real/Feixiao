# Feixiao Alpha 1.0.7

Group-key rekey reliability fix plus performance diagnostics, based on Alpha 1.0.6.

## Group-key rekey fix

A captured failure showed repeated RSN Group Key Handshake message 1/2 frames followed by AP deauthentication with reason 16 (group key update timeout). Alpha 1.0.7 changes only the acknowledgement path after the PTK already exists:

- Send Group M2 through the pairwise-protected CCMP data path.
- Never mark EAPOL control frames for TX A-MPDU aggregation.
- Mirror the received EAPOL version and key descriptor type in Group M2.
- Log Group M2 key-info and replay counter before transmit.
- Detect retransmitted Group M1 frames and resend M2 without reinstalling the same GTK.
- Reject stale Group M1 replay counters.
- Keep unrelated vendor-specific category-127 action traffic out of the persistent rtw88ctl ring unless it comes from the connected AP.

The initial WPA2 4-way handshake path is otherwise unchanged.

## Performance diagnostics

The existing diagnostics from the low-bandwidth investigation remain enabled. They were informed by upstream Feixiao issue #2 and the chvsolucoes/Feixiao performance experiments, but do not enable the fork's RX batching or aggressive DMA/watchdog experiments.

Every 5 seconds the driver records:

- submitted TX packets
- delivered RX packets and bytes
- interrupt count
- cumulative TX stall/resume count
- BE ring available slots
- HW/SW TX ring state and RX read/write pointers

## Test

Enable debug logging:

    sudo rtw88ctl debug 3

After the connection has been up long enough for a group rekey, inspect:

    sudo rtw88ctl log | grep -Ei 'groupM1|group M2 tx|group rekey|reason=16|deauth|disassoc|PERF 5s|TXSTATE|EAPOL'

A successful rekey should show a Group M1, one Group M2 transmit, and no later reason=16 deauthentication.
