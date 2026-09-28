#!/usr/bin/env python3
from pathlib import Path

p = Path("../rtw88-stable/drivers/net/wireless/realtek/rtw88/pci.c")
src = p.read_text()

anchor = r"""static int rtw_pci_init(struct rtw_dev *rtwdev)
{
	struct rtw_pci *rtwpci = (struct rtw_pci *)rtwdev->priv;
	int ret = 0;

	rtwpci->irq_mask[0] = IMR_HIGHDOK |
			      IMR_MGNTDOK |
			      IMR_BKDOK |
			      IMR_BEDOK |
			      IMR_VIDOK |
			      IMR_VODOK |
			      IMR_ROK |
			      IMR_BCNDMAINT_E |
			      IMR_C2HCMD |
			      0;
	rtwpci->irq_mask[1] = IMR_TXFOVW |
			      0;
	rtwpci->irq_mask[3] = IMR_H2CDOK |
			      0;
	spin_lock_init(&rtwpci->irq_lock);
	spin_lock_init(&rtwpci->hwirq_lock);
	ret = rtw_pci_init_trx_ring(rtwdev);

	return ret;
}
"""

replacement = anchor + r"""
#ifdef RTW88_MACOS
/*
 * Development 1.2: no PCI TX/RX descriptors survive system sleep.
 * Sleep tears every ring down after rtw_core_stop(); wake allocates fresh
 * rings only after BAR2 has been remapped.
 */
int rtw88_macos_pci_sleep_deinit(struct rtw_dev *rtwdev)
{
	if (!rtwdev)
		return -EINVAL;

	rtw_pci_deinit(rtwdev);
	rtw_info(rtwdev, "macOS sleep PCI TX/RX rings destroyed\n");
	return 0;
}

int rtw88_macos_pci_wake_init(struct rtw_dev *rtwdev)
{
	struct rtw_pci *rtwpci;
	struct rtw_pci_tx_ring *be;
	int ret;

	if (!rtwdev)
		return -EINVAL;

	rtwpci = (struct rtw_pci *)rtwdev->priv;

	/* RTW88PCIDevice has remapped BAR2. Refresh pci.c's cached VA before
	 * rtw_pci_init()/rtw_core_start() can access MMIO. */
	rtwpci->mmap = pci_ioremap_bar(rtwpci->pdev, 2);
	if (!rtwpci->mmap) {
		rtw_err(rtwdev, "macOS wake BAR2 remap unavailable\n");
		return -ENODEV;
	}

	ret = rtw_pci_init(rtwdev);
	if (ret) {
		rtw_err(rtwdev, "macOS wake PCI ring init failed: %d\n", ret);
		return ret;
	}

	/* The BE software ring must be absolutely pristine before core start.
	 * Any queued skb or non-zero pointer means stale pre-sleep state survived. */
	be = &rtwpci->tx_rings[RTW_TX_QUEUE_BE];
	if (be->r.wp != 0 || be->r.rp != 0 || skb_queue_len(&be->queue) != 0) {
		rtw_err(rtwdev,
			"macOS wake BE ring dirty before core start: wp=%u rp=%u qlen=%u\n",
			be->r.wp, be->r.rp, skb_queue_len(&be->queue));
		rtw_pci_deinit(rtwdev);
		return -EIO;
	}

	rtw_info(rtwdev,
		 "macOS wake PCI rings fresh: BE wp=0 rp=0 qlen=0\n");
	return 0;
}
#endif
"""
if "int rtw88_macos_pci_sleep_deinit(" not in src:
    if anchor not in src:
        raise SystemExit("pci.c rtw_pci_init anchor not found")
    src = src.replace(anchor, replacement, 1)

p.write_text(src)
print("Development 1.2 PCI sleep teardown / wake init patch applied")
