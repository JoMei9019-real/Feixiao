#!/usr/bin/env python3
from pathlib import Path

rxp = Path("../rtw88-stable/drivers/net/wireless/realtek/rtw88/rx.c")
txp = Path("../rtw88-stable/drivers/net/wireless/realtek/rtw88/tx.c")
phyp = Path("../rtw88-stable/drivers/net/wireless/realtek/rtw88/phy.c")

rx = rxp.read_text()
tx = txp.read_text()
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
	 * Feixiao Beta 16: preserve the safe Beta-11 architecture but feed the
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
 * Feixiao Beta 16: isolated RSSI -> firmware RA refresh.
 *
 * The normal watchdog is intentionally still disabled in the macOS port
 * because DIG/DPK/power tracking were suspected of destabilising TX.  This
 * helper mirrors only the RA-relevant subset of the stock watchdog:
 *
 *   avg_rssi -> rssi_level -> rtw_fw_send_rssi_info()
 *
 * Beta 16 deliberately does NOT call rtw_update_sta_info() from this timer.
 * The station RA mask remains the one established during association; only
 * the firmware RSSI feedback is refreshed here.  This avoids reprogramming
 * RA state in the middle of WPA/early rate probing.
 *
 * The caller owns a live associated STA.  No ieee80211_find_sta* lookup occurs.
 */
void rtw88_beta16_ra_refresh(struct rtw_dev *rtwdev,
			     struct ieee80211_sta *sta)
{
	static u32 refresh_count;
	struct rtw_sta_info *si;
	u8 rssi, old_level, new_level;
	u32 n;

	if (!rtwdev || !sta || !test_bit(RTW_FLAG_RUNNING, rtwdev->flags))
		return;

	si = (struct rtw_sta_info *)sta->drv_priv;
	rssi = ewma_rssi_read(&si->avg_rssi);
	old_level = si->rssi_level;
	n = ++refresh_count;

	rtw88_diag_log(
		"rtw88: RSSI_DBG timer t_ms=%lu n=%u sta=%p si=%p ewma=%u level_before=%u\n",
		(unsigned long)jiffies, n, sta, si, (unsigned)rssi, (unsigned)old_level);

	if (!rssi) {
		rtw88_diag_log(
			"rtw88: RSSI_DBG timer t_ms=%lu n=%u no-rssi; RA update skipped\n",
			(unsigned long)jiffies, n);
		return;
	}

	new_level = rtw_phy_get_rssi_level(old_level, rssi);

	if (!mutex_trylock(&rtwdev->mutex)) {
		rtw88_diag_log(
			"rtw88: RSSI_DBG timer t_ms=%lu n=%u mutex_busy; RA update deferred\n",
			(unsigned long)jiffies, n);
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
	 * Beta 16: restore only the firmware WL_PHY_INFO feedback that the
	 * disabled watchdog normally sends.  Preserve the association-time RA
	 * mask: do NOT call rtw_update_sta_info() here.
	 */
	{
		struct rtw_traffic_stats *stats = &rtwdev->stats;
		u32 tx_unicast_mbps = stats->tx_unicast >> RTW_TP_SHIFT;
		u32 rx_unicast_mbps = stats->rx_unicast >> RTW_TP_SHIFT;

		ewma_tp_add(&stats->tx_ewma_tp, tx_unicast_mbps);
		ewma_tp_add(&stats->rx_ewma_tp, rx_unicast_mbps);
		stats->tx_throughput = ewma_tp_read(&stats->tx_ewma_tp);
		stats->rx_throughput = ewma_tp_read(&stats->rx_ewma_tp);

		rtw_fw_update_wl_phy_info(rtwdev);

		rtw88_diag_log(
			"rtw88: PHYINFO t_ms=%lu tx_sample=%u rx_sample=%u tx_tp=%u rx_tp=%u "
			"tx_rate=0x%02x rx_rate=0x%02x evm=%d\n",
			(unsigned long)jiffies,
			(unsigned)tx_unicast_mbps, (unsigned)rx_unicast_mbps,
			(unsigned)stats->tx_throughput, (unsigned)stats->rx_throughput,
			(unsigned)rtwdev->dm_info.tx_rate,
			(unsigned)rtwdev->dm_info.curr_rx_rate,
			(int)rtwdev->dm_info.rx_evm_dbm[RF_PATH_A]);

		stats->tx_unicast = 0;
		stats->rx_unicast = 0;
		stats->tx_cnt = 0;
		stats->rx_cnt = 0;
	}

	/* Keep the association-time RA mask intact. */
	mutex_unlock(&rtwdev->mutex);

	rtw88_diag_log(
		"rtw88: RSSIRA t_ms=%lu n=%u sta=%p si=%p rssi=%u level=%u->%u mask_refresh=0 "
		"ra_desc=0x%02x ra_bitrate=%u ra_mask=0x%llx\n",
		(unsigned long)jiffies, n, sta, si, (unsigned)rssi, (unsigned)old_level,
		(unsigned)new_level,
		(unsigned)si->ra_report.desc_rate,
		(unsigned)si->ra_report.bit_rate,
		(unsigned long long)si->ra_mask);
}
"""

if "void rtw88_beta16_ra_refresh(" not in phy:
    if anchor not in phy:
        raise SystemExit("phy.c RSSI classification anchor not found")
    phy = phy.replace(anchor, helper, 1)


# Beta 16: RTL8821CE is 1T1R.  Force STBC off even if a stale/misdetected
# hal.txrx_1ss flag would otherwise allow si->stbc_en into the descriptor.
stbc_old = "\tstbc = rtwdev->hal.txrx_1ss ? false : si->stbc_en;\n"
stbc_new = """\tif (rtwdev->chip->id == RTW_CHIP_TYPE_8821C)
\t\tstbc = false;
\telse
\t\tstbc = rtwdev->hal.txrx_1ss ? false : si->stbc_en;
"""
if stbc_old in tx:
    tx = tx.replace(stbc_old, stbc_new, 1)
elif stbc_new not in tx:
    raise SystemExit("tx.c STBC insertion point not found")

# Beta 16: cap sparse TX-status diagnostics so enabling diagnostics can never
# build a large tx_report queue.  This is a diagnostic path only.
report_anchor = """static void rtw_tx_report_enable(struct rtw_dev *rtwdev,
				 struct rtw_tx_pkt_info *pkt_info)
{
	struct rtw_tx_report *tx_report = &rtwdev->tx_report;

	/* [11:8], reserved, fills with zero
	 * [7:2],  tx report sequence number
	 * [1:0],  firmware use, fills with zero
	 */
	pkt_info->sn = (atomic_inc_return(&tx_report->sn) << 2) & 0xfc;
	pkt_info->report = true;
}
"""
report_replacement = report_anchor + """
bool rtw88_beta16_tx_report_can_sample(struct rtw_dev *rtwdev)
{
	struct rtw_tx_report *tx_report;
	unsigned long flags;
	u32 pending;

	if (!rtwdev)
		return false;

	tx_report = &rtwdev->tx_report;
	spin_lock_irqsave(&tx_report->q_lock, flags);
	pending = skb_queue_len(&tx_report->queue);
	spin_unlock_irqrestore(&tx_report->q_lock, flags);

	return pending < 8;
}
"""
if "bool rtw88_beta16_tx_report_can_sample(" not in tx:
    if report_anchor not in tx:
        raise SystemExit("tx.c report helper insertion point not found")
    tx = tx.replace(report_anchor, report_replacement, 1)

req_anchor = """\tif (info->flags & IEEE80211_TX_CTL_REQ_TX_STATUS)
\t\trtw_tx_report_enable(rtwdev, pkt_info);
"""
req_replacement = """\tif (info->flags & IEEE80211_TX_CTL_REQ_TX_STATUS) {
\t\tif (rtw88_beta16_tx_report_can_sample(rtwdev)) {
\t\t\trtw_tx_report_enable(rtwdev, pkt_info);
\t\t} else {
\t\t\t/* Hard cap: do not leave REQ_TX_STATUS set, otherwise pci.c
\t\t\t * would enqueue the skb even though no firmware report was requested. */
\t\t\tinfo->flags &= ~IEEE80211_TX_CTL_REQ_TX_STATUS;
\t\t}
\t}
"""
if req_anchor in tx:
    tx = tx.replace(req_anchor, req_replacement, 1)
elif "Hard cap: do not leave REQ_TX_STATUS set" not in tx:
    raise SystemExit("tx.c TX status cap insertion point not found")


# Runtime fixed-rate diagnostic for RTL8821CE unicast data only.
rate_anchor = """\tfix_rate = dm_info->fix_rate;
\tif (fix_rate < DESC_RATE_MAX) {
\t\tpkt_info->rate = fix_rate;
\t\tpkt_info->dis_rate_fallback = true;
\t\tpkt_info->use_rate = true;
\t}
"""
rate_replacement = rate_anchor + """
\t/*
\t * Feixiao Beta 16 diagnostic: bypass firmware RA for data frames when
\t * requested from rtw88ctl.  Management and EAPOL rate handling are untouched.
\t * Auto mode (0) preserves normal firmware rate adaptation.
\t */
\textern int rtw88_beta16_force_rate_mode;
\tif (rtwdev->chip->id == RTW_CHIP_TYPE_8821C &&
\t    sta && sta->deflink.vht_cap.vht_supported &&
\t    be16_to_cpu(skb->protocol) != ETH_P_PAE &&
\t    (rtw88_beta16_force_rate_mode == 5 ||
\t     rtw88_beta16_force_rate_mode == 7)) {
\t\tpkt_info->rate = DESC_RATEVHT1SS_MCS0 + rtw88_beta16_force_rate_mode;
\t\tpkt_info->use_rate = true;
\t\tpkt_info->dis_rate_fallback = true;
\t\tpkt_info->stbc = false;
\t}
"""
if "rtw88_beta16_force_rate_mode" not in tx:
    if rate_anchor not in tx:
        raise SystemExit("tx.c fixed-rate insertion point not found")
    tx = tx.replace(rate_anchor, rate_replacement, 1)


rxp.write_text(rx)
txp.write_text(tx)
phyp.write_text(phy)
print("Beta 16 TX diagnostics + RSSI/PHY feedback applied")
