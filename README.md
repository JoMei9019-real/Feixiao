# Feixiao

Feixiao is an open-source macOS kernel extension that ports the Linux `rtw88`
driver to macOS and provides Wi-Fi support for selected Realtek PCIe adapters.

The current development release is **Feixiao 1.1.0 RC1**. The 1.1.0 series
contains major stability, WPA, receive-path and transmit-rate-control fixes.
The current RC has been validated primarily on **RTL8821CE**.

> **Release status:** 1.1.0 RC1 is a release candidate. The validated Beta 16
> data path is intentionally frozen; RC work is limited to release and
> usability polishing unless a regression is discovered.

## Supported hardware

Feixiao currently targets these Realtek PCIe chipsets:

- RTL8822BE
- RTL8822CE
- RTL8821CE
- RTL8812AE
- RTL8814AE

### Validation status

RTL8821CE is currently the most extensively tested device. On that chipset,
1.1.0 RC1 has been validated with 2.4 GHz and 5 GHz networking, 80 MHz VHT,
automatic firmware rate adaptation, WPA2, A-MPDU and runtime diagnostics.

Support for the other listed PCIe chipsets remains part of the project, but
they have not received the same level of 1.1.0 RC validation.

**USB and SDIO variants are currently unsupported and are not planned targets.**

## What works in 1.1.0 RC1

### Wi-Fi and connection handling

- System sleep/wake recovery through IOKit power management.
- Firmware/core shutdown before sleep and restart after wake.
- Automatic reconnect to the previously associated AP after a successful wake.
- RSSI/PHY H2C refresh is suspended while the device is asleep, preventing
  the repeated `failed to send h2c command` state seen in earlier builds.

- Native 2.4 GHz and 5 GHz scanning.
- Open networks.
- WPA/WPA2 connectivity.
- CCMP/AES and supported mixed-mode security handling.
- Association and reconnect handling.
- Clean AP-originated deauthentication/disassociation cleanup.
- Duplicate WPA2 Message 3 handling without reinstalling PTK/GTK.
- Connection-state reporting through `rtw88ctl status`.

### Performance and rate control

- 20/40/80 MHz channel-width handling where supported by the peer and card.
- HT and VHT operation.
- Short Guard Interval (SGI).
- A-MPDU transmit/receive support.
- Firmware automatic rate adaptation enabled by default.
- RTL8821CE TX-STBC is explicitly disabled because the card is 1T1R; this
  fixes the severe MCS0/performance regression seen during development.
- Corrected RSSI EWMA semantics.
- Periodic RSSI and firmware PHY-information feedback without repeatedly
  rebuilding the station RA mask.
- RX batching/flush improvements carried forward from earlier 1.0.8 betas.

On the validated RTL8821CE test system, the STBC/rate-control fix allowed the
firmware to move normally between VHT MCS levels instead of remaining stuck at
VHT MCS0.

### Diagnostics

Detailed diagnostics are **disabled by default** so normal operation does not
pay the cost of verbose logging or TX-status sampling.

They can be enabled at runtime without rebooting:

```sh
sudo rtw88ctl diag on
```

and disabled again with:

```sh
sudo rtw88ctl diag off
```

When diagnostics are enabled, sparse TX-status sampling is rate-limited and
the TX-report queue is capped so diagnostic traffic cannot build the
hundreds-of-entry pending queue seen in earlier beta builds.

### Version matching

1.1.0 RC1 adds:

```sh
rtw88ctl version
```

This reports both the control utility and the loaded driver build, together
with the current diagnostics state and TX-rate mode. This makes it easy to
spot an old `rtw88ctl` binary being used with a newer Kext.

Example:

```text
rtw88ctl:    1.1.0 RC1
Driver:      1.1.0 RC1
Channel:     Release Candidate
Diagnostics: off
TX rate:     auto
```

## rtw88ctl command reference

`rtw88ctl` is the userspace control and diagnostics utility shipped with
Feixiao. Most commands require the Kext to be loaded. Depending on how the
driver was installed, you may need to run them with `sudo`.

### `version`

Show the `rtw88ctl` version and query the loaded driver build.

```sh
rtw88ctl version
```

Alias:

```sh
rtw88ctl --version
```

It also reports:

- driver build label
- release channel
- diagnostics state
- TX-rate mode

If the loaded driver is older and does not support the version query,
`rtw88ctl` reports it as an older/incompatible build.

### `status`

Show the current driver and connection state.

```sh
sudo rtw88ctl status
```

The output includes, where available:

- driver state
- detected Realtek card
- MAC address
- firmware version
- scan-offload capability
- radio power state
- SSID/BSSID
- RSSI
- channel
- current TX/RX byte counters

### `scan`

Start a Wi-Fi scan and print the resulting network list when the scan
finishes.

```sh
sudo rtw88ctl scan
```

The default wait time is 10 seconds. A custom wait time can be supplied with
`-w`:

```sh
sudo rtw88ctl scan -w 15
```

If the scan is still running when the timeout expires, the currently available
partial results are printed.

### `list`

Print the most recently stored scan results without starting another scan.

```sh
sudo rtw88ctl list
```

The table contains SSID, BSSID, RSSI, channel and detected security mode.

### `connect`

Connect to a network.

WPA/WPA2 example:

```sh
sudo rtw88ctl connect "MyWiFi" "password123"
```

Open-network example:

```sh
sudo rtw88ctl connect "OpenNetwork"
```

The command waits for the connection state machine and reports whether the
connection reached the connected state.

### `disconnect`

Disconnect from the current access point.

```sh
sudo rtw88ctl disconnect
```

### `power on|off`

Enable or disable the IEEE80211 radio.

```sh
sudo rtw88ctl power off
sudo rtw88ctl power on
```

### `log`

Read data from Feixiao's internal driver log buffer.

```sh
sudo rtw88ctl log
```

The log buffer is consumed as it is read. A single call returns a bounded
chunk, so large backlogs may require multiple calls.

Useful diagnostic filter:

```sh
sudo rtw88ctl log | grep -E "TXRPT|TXDIAG|RAREPORT|PHYINFO|RSSIRA"
```

### `debug <level>`

Set the normal driver logging level.

```sh
sudo rtw88ctl debug 0
sudo rtw88ctl debug 1
sudo rtw88ctl debug 2
sudo rtw88ctl debug 3
```

Levels:

| Level | Meaning |
| ---: | --- |
| 0 | Errors |
| 1 | Warnings |
| 2 | Informational messages |
| 3 | Debug messages |

This is separate from the detailed runtime diagnostics controlled by
`diag on|off`.

### `diag on|off`

Enable or disable the detailed Feixiao runtime diagnostics.

Enable:

```sh
sudo rtw88ctl diag on
```

Disable:

```sh
sudo rtw88ctl diag off
```

Detailed diagnostics include the development-time RSSI, RA, PHY, TX descriptor
and sampled TX-report information used to validate 1.1.0.

Normal users should leave diagnostics **off** unless troubleshooting.

### `rate auto|mcs5|mcs7`

Control the diagnostic TX-rate mode.

Normal/default operation:

```sh
sudo rtw88ctl rate auto
```

Diagnostic fixed-rate modes:

```sh
sudo rtw88ctl rate mcs5
sudo rtw88ctl rate mcs7
```

`auto` is the **boot default** and should be used for normal operation. The
MCS5/MCS7 modes bypass normal firmware rate selection for supported VHT
unicast data frames and exist only for debugging.

Management and EAPOL/WPA traffic are not forced through the diagnostic fixed
rate.

## Recommended normal configuration

For normal use with 1.1.0 RC1, no special command is required after boot.

The defaults are:

```text
TX rate:     auto
Diagnostics: off
```

On RTL8821CE, TX-STBC is disabled automatically by the driver.

You can verify the active state with:

```sh
sudo rtw88ctl version
sudo rtw88ctl status
```

## Building from source

### Requirements

- macOS with Xcode Command Line Tools / Xcode toolchain
- MacKernelSDK
- the pinned `rtw88-stable` Linux driver source
- Python 3 for build-time patch/generation scripts

Clone Feixiao:

```sh
git clone https://github.com/JoMei9019-real/Feixiao.git
cd Feixiao
git submodule update --init --recursive
```

For development/RC work:

```sh
git checkout development
```

Clone the Linux driver source next to the Feixiao directory:

```sh
cd ..
git clone https://github.com/thegwchr/rtw88-stable.git
git -C rtw88-stable checkout d029a677c49266fad86750714eb5612becd134d3
```

Expected layout:

```text
parent/
├── Feixiao/
└── rtw88-stable/
    └── drivers/net/wireless/realtek/rtw88/
```

Build both the Kext and utility:

```sh
cd Feixiao
make clean
make all
```

Outputs:

```text
build/out/rtw88.kext
build/out/rtw88ctl
```

## Installation

### OpenCore / Hackintosh

Copy:

```text
build/out/rtw88.kext
```

to your OpenCore `EFI/OC/Kexts` directory and add it to
`Kernel -> Add` in `config.plist`.

Typical entry:

```text
BundlePath:     rtw88.kext
Enabled:        YES
ExecutablePath: Contents/MacOS/rtw88
PlistPath:      Contents/Info.plist
MinKernel:      20.0.0
MaxKernel:      <empty>
```

Then place the matching `rtw88ctl` somewhere convenient, for example
`/usr/local/bin/rtw88ctl`.

Always keep the Kext and `rtw88ctl` from the **same release**.

### Manual test loading

For development systems where manual Kext loading is available:

```sh
sudo chown -R root:wheel build/out/rtw88.kext
sudo kextload build/out/rtw88.kext
```

or use the appropriate `kmutil` workflow for your macOS version.

## Troubleshooting

### Verify Kext/CLI compatibility

Run:

```sh
rtw88ctl version
```

If the CLI reports an older/incompatible driver build, replace both the Kext
and `rtw88ctl` with files from the same Feixiao release.

### Enable detailed diagnostics

```sh
sudo rtw88ctl diag on
```

Reproduce the problem, then inspect the internal log:

```sh
sudo rtw88ctl log
```

Disable diagnostics when finished:

```sh
sudo rtw88ctl diag off
```

### macOS kernel logging

For OpenCore/prelinked setups:

```sh
dmesg | grep -i rtw88
```

For live system logging:

```sh
log stream --predicate 'process == "kernel" and (eventMessage contains "rtw88" or message contains "rtw88")' --info
```

### Connection problems

Useful first checks:

```sh
sudo rtw88ctl version
sudo rtw88ctl status
sudo rtw88ctl scan -w 10
```

When reporting an issue, include:

- Feixiao version/build
- chipset and PCI ID
- macOS version
- firmware version shown by `status`
- whether 2.4 GHz or 5 GHz is affected
- relevant `rtw88ctl log` output with diagnostics enabled

## Important implementation notes for 1.1.0

The 1.1.0 release line intentionally keeps the full upstream rtw88 watchdog
dynamic-mechanism work disabled in this macOS port. Instead, Feixiao restores
only the pieces required for stable RSSI/rate feedback.

In particular:

- the station RA mask is established at association and is not rebuilt every
  two seconds;
- RSSI feedback and PHY information are refreshed separately;
- generic mac80211 station lookup shims are not used for the active station
  path;
- detailed TX-status requests are diagnostics only;
- diagnostics are opt-in and rate-limited.

These choices are deliberate stability measures based on the 1.0.8
development cycle.

## Acknowledgements

- **Realtek** for the original Linux `rtw88` driver and firmware ecosystem.
- **thegwchr** for `rtw88-stable` and the original Feixiao work.
- **Apple** for macOS and IOKit.
- **Acidanthera** for MacKernelSDK.
- **OpenIntelWireless** for itlwm as a reference.
- **FreeBSD** for LinuxKPI as a reference for porting Linux drivers to BSD-like
  environments.

## License

Feixiao contains code under GPL-2.0 and BSD-compatible licensing as indicated
by the individual source files.
