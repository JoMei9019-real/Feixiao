#!/usr/bin/env python3
from pathlib import Path

rxp = Path("../rtw88-stable/drivers/net/wireless/realtek/rtw88/rx.c")
phyp = Path("../rtw88-stable/drivers/net/wireless/realtek/rtw88/phy.c")

rx = rxp.read_text()
phy = phyp.read_text()

# Beta 11 may already have replaced the stock station lookup. Accept either
# stock upstream or Beta-11-patched input so the script is idempotent across
# development rebuilds.
stock = r"""	sta = ieee80211_find_sta_by_ifaddr(rtwdev->hw, hdr->addr2,
					   vif->addr);
	if (!sta)
		return;

	si = (struct rtw_sta_info *)sta->drv_priv;
	ewma_rssi_add(&si->avg_rssi, pkt_stat->rssi);
"""
patched = r"""	/*
	 * Feixiao Beta 11: do not return a raw ieee80211_sta pointer from the
	 * mac80211 lookup shim.  Beta 8 proved that path can race station teardown
	 * and freeze the machine at association time.  The compat layer owns the
	 * single registered peer and performs the tiny EWMA update synchronously
	 * under its own lifetime lock.
	 */
	rtw88_record_sta_rssi(hdr->addr2, pkt_stat->rssi);
"""
replacement = r"""	/*
	 * Feixiao Beta 13: preserve the safe Beta-11 architecture but feed the
	 * exact rtw88 native RSSI sample into the registered associated peer.
	 * Generic ieee80211_find_sta*() remains unused here because Beta 8 showed
	 * that exposing a raw STA through those compatibility APIs can deadlock.
	 */
	rtw88_record_sta_rssi(hdr->addr2, pkt_stat->rssi);
"""
if stock in rx:
    rx = rx.replace(stock, replacement, 1)
elif patched in rx:
    rx = rx.replace(patched, replacement, 1)
elif replacement not in rx:
    raise SystemExit("rx.c station RSSI insertion point not found")

anchor = r"""static u8 rtw_phy_get_rssi_level(u8 old_level, u8 rssi)
{
	u8 table[RA_FLOOR_TABLE_SIZE] = {20, 34, 38, 42, 46, 50, 100};
	u8 new_level = 0;
	int i;

	for (i = 0; i < RA_FLOOR_TABLE_SIZE; i++)
		if (i >= old_level)
			table[i] += RA_FLOOR_UP_GAP;

	for (i = 0; i < RA_FLOOR_TABLE_SIZE; i++) {
		if (rssi < table[i]) {
			new_level = i;
			break;
		}
	}

	return new_level;
}
"""

helper = anchor + r"""
/*
 * Feixiao Beta 13: isolated RSSI -> firmware RA refresh.
 *
 * The normal watchdog is intentionally still disabled in the macOS port
 * because DIG/DPK/power tracking were suspected of destabilising TX.  This
 * helper mirrors only the RA-relevant subset of the stock watchdog:
 *
 *   avg_rssi -> rssi_level -> rtw_fw_send_rssi_info()
 *
 * and every fourth invocation (the same cadence as stock rtw_phy_ra_info_update)
 * refreshes the station RA mask via rtw_update_sta_info().
 *
 * The caller owns a live associated STA.  No ieee80211_find_sta* lookup occurs.
 */
void rtw88_beta13_ra_refresh(struct rtw_dev *rtwdev,
			     struct ieee80211_sta *sta)
{
	static u32 refresh_count;
	struct rtw_sta_info *si;
	u8 rssi, old_level, new_level;
	bool refresh_mask = false;
	u32 n;

	if (!rtwdev || !sta || !test_bit(RTW_FLAG_RUNNING, rtwdev->flags))
		return;

	si = (struct rtw_sta_info *)sta->drv_priv;
	rssi = ewma_rssi_read(&si->avg_rssi);
	old_level = si->rssi_level;
	n = ++refresh_count;

	rtw88_diag_log(
		"rtw88: RSSI_DBG timer n=%u sta=%p si=%p ewma=%u level_before=%u\n",
		n, sta, si, (unsigned)rssi, (unsigned)old_level);

	if (!rssi) {
		rtw88_diag_log(
			"rtw88: RSSI_DBG timer n=%u no-rssi; RA update skipped\n", n);
		return;
	}

	new_level = rtw_phy_get_rssi_level(old_level, rssi);

	if (!mutex_trylock(&rtwdev->mutex)) {
		rtw88_diag_log(
			"rtw88: RSSI_DBG timer n=%u mutex_busy; RA update deferred\n", n);
		return;
	}
	if (!test_bit(RTW_FLAG_RUNNING, rtwdev->flags)) {
		mutex_unlock(&rtwdev->mutex);
		return;
	}

	si->rssi_level = new_level;
	rtwdev->dm_info.pre_min_rssi = rtwdev->dm_info.min_rssi;
	rtwdev->dm_info.min_rssi = rssi;
	rtw_fw_send_rssi_info(rtwdev, si);

	/*
	 * Stock rtw_phy_ra_info_update() executes once every four watchdog runs.
	 * Refresh immediately on a level transition, otherwise every fourth Beta-13
	 * timer tick, so firmware sees the updated RSSI-dependent RA mask without
	 * enabling the rest of rtw_phy_dynamic_mechanism().
	 */
	if (new_level != old_level || (n & 0x3) == 0) {
		rtw_update_sta_info(rtwdev, si, false);
		refresh_mask = true;
	}
	mutex_unlock(&rtwdev->mutex);

	rtw88_diag_log(
		"rtw88: RSSIRA n=%u sta=%p si=%p rssi=%u level=%u->%u mask_refresh=%u "
		"ra_desc=0x%02x ra_bitrate=%u ra_mask=0x%llx\n",
		n, sta, si, (unsigned)rssi, (unsigned)old_level,
		(unsigned)new_level, refresh_mask ? 1U : 0U,
		(unsigned)si->ra_report.desc_rate,
		(unsigned)si->ra_report.bit_rate,
		(unsigned long long)si->ra_mask);
}
"""

if "void rtw88_beta13_ra_refresh(" not in phy:
    if anchor not in phy:
        raise SystemExit("phy.c RSSI classification anchor not found")
    phy = phy.replace(anchor, helper, 1)

rxp.write_text(rx)
phyp.write_text(phy)
print("Beta 13 isolated RSSI/RA path applied")
