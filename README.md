# Feixiao

Feixiao is a macOS kernel extension that ports the Linux `rtw88` driver, bringing support for Realtek PCIe Wi-Fi cards to macOS.

## Supported Hardware

Feixiao aims to support the following Realtek chipsets:
- RTL8822BE
- RTL8822CE
- RTL8821CE
- RTL8812AE
- RTL8814AE

*Note: USB and SDIO variants are unsupported, and are not planned to be supported.*

## Features

- Native scanning of 2.4GHz and 5GHz bands.
- Connection to Open and WPA/WPA2 (incl. mixed modes) (CCMP/PSK/TKIP/AES/TKIP+AES) networks.
- Custom `rtw88ctl` command-line utility to control the driver, with possibility to use [Starskiff](https://github.com/thegwchr/Starskiff) as GUI alternative

## Build Instructions

To build Feixiao from source, you will need the rtw88 driver from Linux kernel source, Xcode Command Line Tools and the macOS Kernel SDK.

```sh
# Clone the repository
git clone https://github.com/thegwchr/Feixiao.git
cd Feixiao
git submodule update --recursive
```

Before building Feixiao, clone the Linux `rtw88` driver source from thegwchr/rtw88-stable:

```sh
git clone https://github.com/thegwchr/rtw88-stable.git
```

Directory structure must be:

```
parent/
├── Feixiao/        # this repository
└── rtw88-stable/   # Linux kernel tree root (driver at drivers/net/wireless/realtek/rtw88/)
```

If you name the clone differently, update `LINUX_SRC` in `Makefile` accordingly.


```sh
# Build the kext and control utility
make all
```

The compiled kernel extension (`rtw88.kext`) and the command-line utility (`rtw88ctl`) will be generated in the `build/out/` directory.

## Release Candidate

The current 1.0.8 release candidate defaults to firmware automatic rate
adaptation. Detailed diagnostics are disabled during normal operation and can
be enabled temporarily with `rtw88ctl diag on`.

Use `rtw88ctl version` to verify that the control utility and loaded driver
belong to the same build.

## Installation & Usage


1. **Load the Kext:**
   To load it manually for testing:
   ```sh
   sudo chown -R root:wheel build/out/rtw88.kext
   sudo kextload build/out/rtw88.kext
   ```
   *(You may be prompted to approve the extension in System Settings -> Privacy & Security. If you are using a Hackintosh, you can inject it via OpenCore).*

2. **Check Version and Status:**
   Verify that the control utility matches the loaded driver, then check the
   current connection state:
   ```sh
   ./build/out/rtw88ctl version
   ./build/out/rtw88ctl status
   ```

3. **Scan for Networks:**
   ```sh
   # Trigger a hardware scan
   ./build/out/rtw88ctl scan
   
   # List the discovered access points
   ./build/out/rtw88ctl list
   ```

4. **Connect to a Network:**
   ```sh
   ./build/out/rtw88ctl connect "Your_SSID" "Your_Password"
   ```

### Runtime diagnostics

Detailed diagnostics are off by default:

```sh
./build/out/rtw88ctl diag on
./build/out/rtw88ctl log
./build/out/rtw88ctl diag off
```

The optional fixed-rate modes are intended for diagnostics only. Normal use
should remain on automatic rate adaptation:

```sh
./build/out/rtw88ctl rate auto
```

## Troubleshooting


You can view driver logs using `dmesg` if you're injecting it as pre-link (OpenCore):
```sh
dmesg | grep -i rtw88
```

or, if you're loading via `kextload/kmutil`:

```sh
log stream --predicate 'process == "kernel" and (eventMessage contains "rtw88" or message contains "rtw88")' --info
```

If you encounter kernel panics or connection failures, ensure you are using the latest commit and that your specific card's PCI ID is bound to the driver.

## Acknowledgements

- **Realtek** for the original Linux `rtw88` driver source code and WLAN card;
- **Apple** for the OS;
- **AcidAnthera** for MacKernelSDK;
- **OpenIntelWireless** for itlwm as reference;
- **FreeBSD** for LinuxKPI as reference on how Linux drivers get implemented in BSD.
