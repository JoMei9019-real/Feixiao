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
 * macOS system sleep can power-cycle the PCIe function while the kext and
 * its software-side rtw_pci object survive.  rtw_core_stop()/start() resets
 * hardware indices but intentionally keeps the rings allocated.  After a
 * real PCIe power loss those stale DMA mappings/ring contents can produce
 * RX-tag mismatches ("pci bus timeout, check dma status") indefinitely.
 *
 * Recreate every TX/RX ring and DMA mapping before rtw_core_start() programs
 * the descriptors back into the device.  Caller must have stopped the core.
 */
int rtw88_macos_pci_reinit(struct rtw_dev *rtwdev)
{
	struct rtw_pci *rtwpci;
	int ret;

	if (!rtwdev)
		return -EINVAL;

	rtwpci = (struct rtw_pci *)rtwdev->priv;

	/*
	 * pci.c cached the pre-sleep BAR VA in rtwpci->mmap at probe time.
	 * RTW88PCIDevice remaps BAR2 first; refresh the driver's cached pointer
	 * before any post-wake MMIO access.
	 */
	rtwpci->mmap = pci_ioremap_bar(rtwpci->pdev, 2);
	if (!rtwpci->mmap) {
		rtw_err(rtwdev, "macOS wake BAR2 remap unavailable\n");
		return -ENODEV;
	}

	rtw_pci_deinit(rtwdev);
	ret = rtw_pci_init(rtwdev);
	if (ret)
		rtw_err(rtwdev, "macOS wake PCI ring reinit failed: %d\n", ret);
	else
		rtw_info(rtwdev, "macOS wake PCI TX/RX rings reinitialized\n");

	return ret;
}
#endif
"""

if "int rtw88_macos_pci_reinit(" not in src:
    if anchor not in src:
        raise SystemExit("pci.c rtw_pci_init anchor not found")
    src = src.replace(anchor, replacement, 1)

p.write_text(src)
print("macOS PCI sleep/wake ring reinit patch applied")
