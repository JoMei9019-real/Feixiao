#!/usr/bin/env python3
from pathlib import Path

root = Path("../rtw88-stable/drivers/net/wireless/realtek/rtw88")
txp = root / "tx.c"
fwp = root / "fw.c"

tx = txp.read_text()

# --------------------------------------------------------------------
# TX report accounting: sparse sampled reports requested by the wrapper
# --------------------------------------------------------------------
needle = r"""void rtw_tx_report_purge_timer(struct timer_list *t)
{"""
repl = r"""static u32 beta7_txr_enqueued;
static u32 beta7_txr_completed;
static u32 beta7_txr_acked;
static u32 beta7_txr_failed;
static u32 beta7_txr_timed_out;

void rtw_tx_report_purge_timer(struct timer_list *t)
{"""
if needle not in tx:
    raise SystemExit("tx.c report counter insertion point not found")
tx = tx.replace(needle, repl, 1)

needle = r"""	if (skb_queue_len(&tx_report->queue) == 0)
		return;

	rtw_warn(rtwdev, "failed to get tx report from firmware\n");"""
repl = r"""	{
		u32 pending = skb_queue_len(&tx_report->queue);
		if (pending == 0)
			return;
		beta7_txr_timed_out += pending;
		rtw88_diag_log(
			"rtw88: TXRPT timeout pending=%u enq=%u done=%u ack=%u fail=%u timeout=%u\n",
			pending, beta7_txr_enqueued, beta7_txr_completed,
			beta7_txr_acked, beta7_txr_failed, beta7_txr_timed_out);
	}

	rtw_warn(rtwdev, "failed to get tx report from firmware\n");"""
if needle not in tx:
    raise SystemExit("tx.c purge diagnostic insertion point not found")
tx = tx.replace(needle, repl, 1)

needle = r"""	spin_lock_irqsave(&tx_report->q_lock, flags);
	__skb_queue_tail(&tx_report->queue, skb);
	spin_unlock_irqrestore(&tx_report->q_lock, flags);

	mod_timer(&tx_report->purge_timer, jiffies + RTW_TX_PROBE_TIMEOUT);"""
repl = r"""	spin_lock_irqsave(&tx_report->q_lock, flags);
	__skb_queue_tail(&tx_report->queue, skb);
	beta7_txr_enqueued++;
	u32 beta7_pending = skb_queue_len(&tx_report->queue);
	spin_unlock_irqrestore(&tx_report->q_lock, flags);

	rtw88_diag_log(
		"rtw88: TXRPT enqueue total=%u pending=%u sn=0x%02x\n",
		beta7_txr_enqueued, beta7_pending, sn);

	mod_timer(&tx_report->purge_timer, jiffies + RTW_TX_PROBE_TIMEOUT);"""
if needle not in tx:
    raise SystemExit("tx.c enqueue diagnostic insertion point not found")
tx = tx.replace(needle, repl, 1)

needle = r"""		if (*n == sn) {
			__skb_unlink(cur, &tx_report->queue);
			rtw_tx_report_tx_status(rtwdev, cur, st == 0);
			break;
		}"""
repl = r"""		if (*n == sn) {
			__skb_unlink(cur, &tx_report->queue);
			beta7_txr_completed++;
			if (st == 0)
				beta7_txr_acked++;
			else
				beta7_txr_failed++;
			rtw88_diag_log(
				"rtw88: TXRPT complete sn=0x%02x status=%u result=%s pending=%u "
				"enq=%u done=%u ack=%u fail=%u timeout=%u\n",
				sn, st, st == 0 ? "ACK" : "FAIL",
				skb_queue_len(&tx_report->queue),
				beta7_txr_enqueued, beta7_txr_completed,
				beta7_txr_acked, beta7_txr_failed, beta7_txr_timed_out);
			rtw_tx_report_tx_status(rtwdev, cur, st == 0);
			break;
		}"""
if needle not in tx:
    raise SystemExit("tx.c report completion insertion point not found")
tx = tx.replace(needle, repl, 1)

# --------------------------------------------------------------------
# SGI propagation: si->sgi_enable was calculated but never encoded.
# --------------------------------------------------------------------
needle = r"""	stbc = rtwdev->hal.txrx_1ss ? false : si->stbc_en;
	ldpc = si->ldpc_en;

out:"""
repl = r"""	stbc = rtwdev->hal.txrx_1ss ? false : si->stbc_en;
	ldpc = si->ldpc_en;
	/* Beta 7: propagate the station's negotiated SGI capability into the
	 * per-packet descriptor. The port previously calculated si->sgi_enable
	 * but left pkt_info->short_gi at zero for every data frame. */
	pkt_info->short_gi = si->sgi_enable;

out:"""
if needle not in tx:
    raise SystemExit("tx.c SGI insertion point not found")
tx = tx.replace(needle, repl, 1)

# --------------------------------------------------------------------
# Deep per-packet TX diagnostics retained from Beta 6.
# --------------------------------------------------------------------
needle = r"""	/* maybe merge with tx status ? */
	rtw_tx_stats(rtwdev, vif, skb);
}"""
repl = r"""	/* Beta 7 diagnostics: sample exact values handed to the Realtek TX
	 * descriptor builder. First 16 data frames, then every 64th. */
	if (ieee80211_is_data(fc)) {
		static u32 beta7_tx_diag_count;
		u32 n = ++beta7_tx_diag_count;
		if (n <= 16 || (n & 63) == 0) {
			if (sta) {
				si = (struct rtw_sta_info *)sta->drv_priv;
				rtw88_diag_log(
					"rtw88: TXDIAG n=%u len=%u seq=%u ampdu=%u factor=%u density=%u "
					"rate=0x%02x rate_id=%u bw=%u use_rate=%u fallback=%u rts=%u "
					"sgi=%u stbc=%u ldpc=%u sec=%u qsel=%u macid=%u fix=0x%02x "
					"si_bw=%u si_rate_id=%u si_sgi=%u si_vht=%u rssi_lvl=%u "
					"ra_desc=0x%02x ra_mbps=%u ra_mask=0x%llx\n",
					n, pkt_info->tx_pkt_size, pkt_info->seq,
					pkt_info->ampdu_en, pkt_info->ampdu_factor,
					pkt_info->ampdu_density, pkt_info->rate,
					pkt_info->rate_id, pkt_info->bw, pkt_info->use_rate,
					pkt_info->dis_rate_fallback, pkt_info->rts,
					pkt_info->short_gi, pkt_info->stbc, pkt_info->ldpc,
					pkt_info->sec_type, pkt_info->qsel, pkt_info->mac_id,
					rtwdev->dm_info.fix_rate, si->bw_mode, si->rate_id,
					si->sgi_enable, si->vht_enable, si->rssi_level,
					si->ra_report.desc_rate, si->ra_report.bit_rate,
					(unsigned long long)si->ra_mask);
			} else {
				rtw88_diag_log(
					"rtw88: TXDIAG n=%u len=%u seq=%u NO_STA ampdu=%u rate=0x%02x "
					"rate_id=%u bw=%u rts=%u fix=0x%02x\n",
					n, pkt_info->tx_pkt_size, pkt_info->seq,
					pkt_info->ampdu_en, pkt_info->rate, pkt_info->rate_id,
					pkt_info->bw, pkt_info->rts, rtwdev->dm_info.fix_rate);
			}
		}
	}

	/* maybe merge with tx status ? */
	rtw_tx_stats(rtwdev, vif, skb);
}"""
if needle not in tx:
    raise SystemExit("tx.c pkt_info diagnostic insertion point not found")
tx = tx.replace(needle, repl, 1)

needle = r"""	if (pkt_info->tim_offset)
		tx_desc->w9 |= le32_encode_bits(1, RTW_TX_DESC_W9_TIM_EN) |
			       le32_encode_bits(pkt_info->tim_offset, RTW_TX_DESC_W9_TIM_OFFSET);
}"""
repl = r"""	if (pkt_info->tim_offset)
		tx_desc->w9 |= le32_encode_bits(1, RTW_TX_DESC_W9_TIM_EN) |
			       le32_encode_bits(pkt_info->tim_offset, RTW_TX_DESC_W9_TIM_OFFSET);

	/* Raw descriptor sample: verify AGG_EN / USE_RTS / DATA_BW / DATARATE /
	 * SHORT_GI exactly as encoded for hardware. */
	if (pkt_info->qsel == 0 && !pkt_info->bmc) {
		static u32 beta7_desc_diag_count;
		u32 n = ++beta7_desc_diag_count;
		if (n <= 8 || (n & 127) == 0)
			rtw88_diag_log(
				"rtw88: TXDESC n=%u w0=%08x w1=%08x w2=%08x w3=%08x "
				"w4=%08x w5=%08x w9=%08x\n",
				n, le32_to_cpu(tx_desc->w0), le32_to_cpu(tx_desc->w1),
				le32_to_cpu(tx_desc->w2), le32_to_cpu(tx_desc->w3),
				le32_to_cpu(tx_desc->w4), le32_to_cpu(tx_desc->w5),
				le32_to_cpu(tx_desc->w9));
	}
}"""
if needle not in tx:
    raise SystemExit("tx.c descriptor diagnostic insertion point not found")
tx = tx.replace(needle, repl, 1)

txp.write_text(tx)

# --------------------------------------------------------------------
# Firmware C2H / rate-adaptation diagnostics.
# --------------------------------------------------------------------
fw = fwp.read_text()

needle = r"""	si->ra_report.desc_rate = rate;
	si->ra_report.bit_rate = bit_rate;

	sta->deflink.agg.max_rc_amsdu_len = get_max_amsdu_len(bit_rate);"""
repl = r"""	si->ra_report.desc_rate = rate;
	si->ra_report.bit_rate = bit_rate;

	rtw88_diag_log(
		"rtw88: RAREPORT macid=%u rate=0x%02x sgi=%u bw=%u bitrate=%u "
		"flags=0x%x mcs=%u nss=%u si_bw=%u rate_id=%u ra_mask=0x%llx\n",
		mac_id, rate, sgi, bw, bit_rate,
		(unsigned)si->ra_report.txrate.flags,
		(unsigned)si->ra_report.txrate.mcs,
		(unsigned)si->ra_report.txrate.nss,
		(unsigned)si->bw_mode, (unsigned)si->rate_id,
		(unsigned long long)si->ra_mask);

	sta->deflink.agg.max_rc_amsdu_len = get_max_amsdu_len(bit_rate);"""
if needle not in fw:
    raise SystemExit("fw.c RA report insertion point not found")
fw = fw.replace(needle, repl, 1)

needle = r"""	if (!test_bit(RTW_FLAG_RUNNING, rtwdev->flags))
		goto unlock;

	switch (c2h->id) {"""
repl = r"""	if (!test_bit(RTW_FLAG_RUNNING, rtwdev->flags))
		goto unlock;

	{
		static u32 beta7_c2h_count;
		u32 n = ++beta7_c2h_count;
		if (c2h->id == C2H_RA_RPT || c2h->id == C2H_CCX_TX_RPT ||
		    n <= 16 || (n & 63) == 0)
			rtw88_diag_log(
				"rtw88: C2HDIAG n=%u id=0x%02x seq=0x%02x len=%u c2h_q=%u txr_q=%u\n",
				n, c2h->id, c2h->seq, len,
				skb_queue_len(&rtwdev->c2h_queue),
				skb_queue_len(&rtwdev->tx_report.queue));
	}

	switch (c2h->id) {"""
if needle not in fw:
    raise SystemExit("fw.c C2H insertion point not found")
fw = fw.replace(needle, repl, 1)

fwp.write_text(fw)
print("Beta 7 TX/RA diagnostics and SGI fix applied")
