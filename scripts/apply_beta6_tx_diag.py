#!/usr/bin/env python3
from pathlib import Path

p = Path("../rtw88-stable/drivers/net/wireless/realtek/rtw88/tx.c")
s = p.read_text()

needle = r"""	/* maybe merge with tx status ? */
	rtw_tx_stats(rtwdev, vif, skb);
}"""
repl = r"""	/* Beta 6 diagnostics: sample the exact values handed to the Realtek TX
	 * descriptor builder. First 16 data frames are logged, then every 64th.
	 * This is intentionally rate-limited so diagnostics do not become the
	 * throughput bottleneck themselves. */
	if (ieee80211_is_data(fc)) {
		static u32 beta6_tx_diag_count;
		u32 n = ++beta6_tx_diag_count;
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
if needle not in s:
    raise SystemExit("tx.c pkt_info insertion point not found")
s = s.replace(needle, repl, 1)

needle2 = r"""	if (pkt_info->tim_offset)
		tx_desc->w9 |= le32_encode_bits(1, RTW_TX_DESC_W9_TIM_EN) |
			       le32_encode_bits(pkt_info->tim_offset, RTW_TX_DESC_W9_TIM_OFFSET);
}"""
repl2 = r"""	if (pkt_info->tim_offset)
		tx_desc->w9 |= le32_encode_bits(1, RTW_TX_DESC_W9_TIM_EN) |
			       le32_encode_bits(pkt_info->tim_offset, RTW_TX_DESC_W9_TIM_OFFSET);

	/* Raw descriptor sample, less frequent than TXDIAG.  This lets us verify
	 * AGG_EN / USE_RTS / DATA_BW / DATARATE as actually encoded for hardware. */
	if (pkt_info->qsel == 0 && !pkt_info->bmc) {
		static u32 beta6_desc_diag_count;
		u32 n = ++beta6_desc_diag_count;
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
if needle2 not in s:
    raise SystemExit("tx.c descriptor insertion point not found")
s = s.replace(needle2, repl2, 1)

p.write_text(s)
print("Beta 6 TX diagnostics applied to", p)
