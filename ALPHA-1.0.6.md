# Feixiao Alpha 1.0.6

Experimental WPA2 group-key rekey support and persistent EAPOL diagnostics.

## Why

A connected RTL8821CE client was deauthenticated by the AP with reason 16
(group key update timeout). The existing MLME only consumed EAPOL while the
initial 4-way handshake was active, so later GTK rekeys were not processed.

## Changes

- Consume EAPOL frames while CONNECTED as well as during the initial handshake.
- Detect RSN Group Key Handshake message 1/2.
- Verify the EAPOL MIC with the current PTK KCK.
- AES-unwrap encrypted key data with the current PTK KEK.
- Extract and install the replacement GTK.
- Send RSN Group Key Handshake message 2/2 using the AP's descriptor version.
- Persist EAPOL and group-rekey diagnostics in the rtw88ctl log ring.
- Keep the Alpha 1.0.5 WPA2/WPA3 transition-mode fallback and association-response safety fix.

## Safety scope

This patch does not add new PCIe/MMIO, firmware-control, interrupt, or hot-reload
paths. Group-rekey handling uses fixed-size stack buffers and existing validated
AES unwrap / GTK KDE parsing / key-install helpers.

This alpha still does not implement SAE/WPA3 authentication or 802.11w PMF.
