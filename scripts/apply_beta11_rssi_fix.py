#!/usr/bin/env python3
from pathlib import Path

p = Path("../rtw88-stable/drivers/net/wireless/realtek/rtw88/rx.c")
s = p.read_text()

old = r"""	sta = ieee80211_find_sta_by_ifaddr(rtwdev->hw, hdr->addr2,
					   vif->addr);
	if (!sta)
		return;

	si = (struct rtw_sta_info *)sta->drv_priv;
	ewma_rssi_add(&si->avg_rssi, pkt_stat->rssi);
"""

new = r"""	/*
	 * Feixiao Beta 11: do not return a raw ieee80211_sta pointer from the
	 * mac80211 lookup shim.  Beta 8 proved that path can race station teardown
	 * and freeze the machine at association time.  The compat layer owns the
	 * single registered peer and performs the tiny EWMA update synchronously
	 * under its own lifetime lock.
	 */
	rtw88_record_sta_rssi(hdr->addr2, pkt_stat->rssi);
"""

if old not in s:
    raise SystemExit("rx.c station RSSI insertion point not found")

s = s.replace(old, new, 1)
p.write_text(s)
print("Beta 11 safe RSSI path applied to", p)
