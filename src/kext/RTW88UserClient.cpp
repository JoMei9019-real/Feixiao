// SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause
// RTW88UserClient.cpp — IOUserClient implementation

#include "RTW88UserClient.hpp"
#include "RTW88PCIDevice.hpp"
#include "RTW88IEEE80211.hpp"

#include <IOKit/IOLib.h>
#include <string.h>

extern "C" int rtw88_beta16_set_rate_mode(int mode);
extern "C" int rtw88_beta16_set_diag_enabled(int enabled);
extern "C" int rtw88_beta16_diag_is_enabled(void);
extern "C" int rtw88_beta16_get_rate_mode(void);

#define super IOUserClient
OSDefineMetaClassAndStructors(RTW88UserClient, IOUserClient)

/* ------------------------------------------------------------------ */
/*  Dispatch table                                                      */
/* ------------------------------------------------------------------ */

const IOExternalMethodDispatch RTW88UserClient::sMethods[kRTW88NumSelectors] = {
    /* kRTW88Scan */
    { (IOExternalMethodAction)&RTW88UserClient::sScan,
      0, 0, 0, 0 },
    /* kRTW88Connect: input struct = RTW88ConnectArgs */
    { (IOExternalMethodAction)&RTW88UserClient::sConnect,
      0, sizeof(RTW88ConnectArgs), 0, 0 },
    /* kRTW88Disconnect */
    { (IOExternalMethodAction)&RTW88UserClient::sDisconnect,
      0, 0, 0, 0 },
    /* kRTW88GetState: output struct = RTW88StateResult */
    { (IOExternalMethodAction)&RTW88UserClient::sGetState,
      0, 0, 0, sizeof(RTW88StateResult) },
    /* kRTW88GetBSSList: output = raw bytes, max 16KB */
    { (IOExternalMethodAction)&RTW88UserClient::sGetBSSList,
      0, 0, 0, kIOUCVariableStructureSize },
    /* kRTW88GetRSSI: output scalar */
    { (IOExternalMethodAction)&RTW88UserClient::sGetRSSI,
      0, 0, 1, 0 },
    /* kRTW88SetDebug: input scalar = debug level */
    { (IOExternalMethodAction)&RTW88UserClient::sSetDebug,
      1, 0, 0, 0 },
    /* kRTW88GetLog: output = log bytes */
    { (IOExternalMethodAction)&RTW88UserClient::sGetLog,
      0, 0, 0, kIOUCVariableStructureSize },
    /* kRTW88PowerOn */
    { (IOExternalMethodAction)&RTW88UserClient::sPowerOn,
      0, 0, 0, 0 },
    /* kRTW88PowerOff */
    { (IOExternalMethodAction)&RTW88UserClient::sPowerOff,
      0, 0, 0, 0 },
    /* kRTW88SetRateMode: input scalar = 0(auto), 5(MCS5), 7(MCS7) */
    { (IOExternalMethodAction)&RTW88UserClient::sSetRateMode,
      1, 0, 0, 0 },
    /* kRTW88SetDiag: input scalar = 0(off), 1(on) */
    { (IOExternalMethodAction)&RTW88UserClient::sSetDiag,
      1, 0, 0, 0 },
    /* kRTW88GetVersion: output struct = RTW88VersionResult */
    { (IOExternalMethodAction)&RTW88UserClient::sGetVersion,
      0, 0, 0, sizeof(RTW88VersionResult) },
    /* kRTW88Reset: full in-driver PCI/DMA/firmware reset */
    { (IOExternalMethodAction)&RTW88UserClient::sReset,
      0, 0, 0, 0 },
};

/* ------------------------------------------------------------------ */
/*  Factory                                                             */
/* ------------------------------------------------------------------ */

RTW88UserClient *RTW88UserClient::create(RTW88PCIDevice *dev, task_t owningTask)
{
    RTW88UserClient *uc = new RTW88UserClient;
    if (uc && !uc->init(nullptr)) { uc->release(); return nullptr; }
    if (uc) { uc->_provider = dev; uc->_owningTask = owningTask; }
    return uc;
}

/* ------------------------------------------------------------------ */
/*  IOService lifecycle                                                 */
/* ------------------------------------------------------------------ */

bool RTW88UserClient::init(OSDictionary *props)
{
    return super::init(props);
}

bool RTW88UserClient::initWithTask(task_t owningTask, void *securityID, UInt32 type, OSDictionary *properties)
{
    _owningTask = owningTask;
    if (!super::initWithTask(owningTask, securityID, type, properties)) {
        IOLog("rtw88: RTW88UserClient::initWithTask(4) super failed\n");
        return false;
    }
    return true;
}

bool RTW88UserClient::initWithTask(task_t owningTask, void *securityID, UInt32 type)
{
    _owningTask = owningTask;
    if (!super::initWithTask(owningTask, securityID, type)) {
        IOLog("rtw88: RTW88UserClient::initWithTask(3) super failed\n");
        return false;
    }
    return true;
}

bool RTW88UserClient::start(IOService *provider)
{
    if (!super::start(provider)) {
        IOLog("rtw88: RTW88UserClient::start() super::start failed\n");
        return false;
    }
    _provider = OSDynamicCast(RTW88PCIDevice, provider);
    if (!_provider) {
        IOLog("rtw88: RTW88UserClient::start() OSDynamicCast to RTW88PCIDevice failed\n");
        return false;
    }
    return true;
}

void RTW88UserClient::stop(IOService *provider)
{
    super::stop(provider);
}

void RTW88UserClient::free()
{
    super::free();
}

IOReturn RTW88UserClient::clientClose()
{
    terminate();
    return kIOReturnSuccess;
}

/* ------------------------------------------------------------------ */
/*  externalMethod dispatch                                             */
/* ------------------------------------------------------------------ */

IOReturn RTW88UserClient::externalMethod(uint32_t selector,
                                          IOExternalMethodArguments *args,
                                          IOExternalMethodDispatch *dispatch,
                                          OSObject *target, void *reference)
{
    if (selector >= kRTW88NumSelectors)
        return kIOReturnUnsupported;

    const IOExternalMethodDispatch *d = &sMethods[selector];
    return super::externalMethod(selector, args,
                                  const_cast<IOExternalMethodDispatch *>(d),
                                  this, nullptr);
}

/* ------------------------------------------------------------------ */
/*  Individual selectors                                                */
/* ------------------------------------------------------------------ */

IOReturn RTW88UserClient::sScan(RTW88UserClient *uc, void *ref,
                                  IOExternalMethodArguments *args)
{
    if (!uc->_provider || !uc->_provider->get80211()) return kIOReturnOffline;
    return uc->_provider->get80211()->cmdScan();
}

IOReturn RTW88UserClient::sConnect(RTW88UserClient *uc, void *ref,
                                     IOExternalMethodArguments *args)
{
    if (!uc->_provider || !uc->_provider->get80211()) return kIOReturnOffline;
    if (!args->structureInput || args->structureInputSize < sizeof(RTW88ConnectArgs))
        return kIOReturnBadArgument;

    const RTW88ConnectArgs *ca = (const RTW88ConnectArgs *)args->structureInput;
    return uc->_provider->get80211()->cmdConnect(ca->ssid, ca->password);
}

IOReturn RTW88UserClient::sDisconnect(RTW88UserClient *uc, void *ref,
                                        IOExternalMethodArguments *args)
{
    if (!uc->_provider || !uc->_provider->get80211()) return kIOReturnOffline;
    return uc->_provider->get80211()->cmdDisconnect();
}

IOReturn RTW88UserClient::sGetState(RTW88UserClient *uc, void *ref,
                                      IOExternalMethodArguments *args)
{
    if (!args->structureOutput || args->structureOutputSize < sizeof(RTW88StateResult))
        return kIOReturnBadArgument;

    RTW88StateResult *result = (RTW88StateResult *)args->structureOutput;
    memset(result, 0, sizeof(*result));

    if (!uc->_provider || !uc->_provider->get80211()) {
        strlcpy(result->chip_name, "Uninitialized", sizeof(result->chip_name));
        args->structureOutputSize = sizeof(*result);
        return kIOReturnSuccess;
    }

    IOReturn ret = uc->_provider->get80211()->cmdGetState(result);
    if (ret != kIOReturnSuccess) return ret;

    args->structureOutputSize = sizeof(*result);
    return kIOReturnSuccess;
}

IOReturn RTW88UserClient::sGetBSSList(RTW88UserClient *uc, void *ref,
                                        IOExternalMethodArguments *args)
{
    if (!args->structureOutput) return kIOReturnBadArgument;
    if (!uc->_provider || !uc->_provider->get80211()) {
        args->structureOutputSize = 0;
        return kIOReturnSuccess;
    }

    uint32_t len = (uint32_t)args->structureOutputSize;
    IOReturn ret = uc->_provider->get80211()->cmdGetBSSList(
        (uint8_t *)args->structureOutput, &len);
    args->structureOutputSize = len;
    return ret;
}

IOReturn RTW88UserClient::sGetRSSI(RTW88UserClient *uc, void *ref,
                                     IOExternalMethodArguments *args)
{
    if (!args->scalarOutput || args->scalarOutputCount < 1) return kIOReturnBadArgument;
    if (!uc->_provider || !uc->_provider->get80211()) {
        args->scalarOutput[0] = (uint64_t)(int64_t)-100;
        return kIOReturnSuccess;
    }
    int rssi = -100;
    IOReturn ret = uc->_provider->get80211()->cmdGetRSSI(&rssi);
    args->scalarOutput[0] = (uint64_t)(int64_t)rssi;
    return ret;
}

IOReturn RTW88UserClient::sSetDebug(RTW88UserClient *uc, void *ref,
                                      IOExternalMethodArguments *args)
{
    if (args->scalarInputCount >= 1) {
        extern int rtw88_log_level;
        rtw88_log_level = (int)args->scalarInput[0];
    }
    return kIOReturnSuccess;
}

extern "C" {
    uint32_t rtw88_read_log(char *out_buf, uint32_t max_len);
}

IOReturn RTW88UserClient::sGetLog(RTW88UserClient *uc, void *ref,
                                    IOExternalMethodArguments *args)
{
    if (!args->structureOutput || args->structureOutputSize == 0)
        return kIOReturnBadArgument;

    uint32_t max_len = (uint32_t)args->structureOutputSize;
    uint32_t read = rtw88_read_log((char *)args->structureOutput, max_len);
    
    args->structureOutputSize = read;
    return kIOReturnSuccess;
}

IOReturn RTW88UserClient::sPowerOn(RTW88UserClient *uc, void *ref,
                                   IOExternalMethodArguments *args)
{
    if (!uc->_provider || !uc->_provider->get80211()) return kIOReturnOffline;
    return uc->_provider->get80211()->cmdPowerOn();
}

IOReturn RTW88UserClient::sPowerOff(RTW88UserClient *uc, void *ref,
                                    IOExternalMethodArguments *args)
{
    if (!uc->_provider || !uc->_provider->get80211()) return kIOReturnOffline;
    return uc->_provider->get80211()->cmdPowerOff();
}

IOReturn RTW88UserClient::sSetRateMode(RTW88UserClient *uc, void *ref,
                                       IOExternalMethodArguments *args)
{
    if (!args || args->scalarInputCount < 1)
        return kIOReturnBadArgument;
    int mode = (int)args->scalarInput[0];
    int ret = rtw88_beta16_set_rate_mode(mode);
    return ret == 0 ? kIOReturnSuccess : kIOReturnBadArgument;
}

IOReturn RTW88UserClient::sSetDiag(RTW88UserClient *uc, void *ref,
                                   IOExternalMethodArguments *args)
{
    if (!args || args->scalarInputCount < 1)
        return kIOReturnBadArgument;
    uint64_t enabled = args->scalarInput[0];
    if (enabled > 1)
        return kIOReturnBadArgument;
    rtw88_beta16_set_diag_enabled(enabled ? 1 : 0);
    return kIOReturnSuccess;
}

IOReturn RTW88UserClient::sGetVersion(RTW88UserClient *uc, void *ref,
                                      IOExternalMethodArguments *args)
{
    if (!args || !args->structureOutput ||
        args->structureOutputSize < sizeof(RTW88VersionResult))
        return kIOReturnBadArgument;

    RTW88VersionResult *result =
        (RTW88VersionResult *)args->structureOutput;
    memset(result, 0, sizeof(*result));
    strlcpy(result->version, RTW88_VERSION_STRING, sizeof(result->version));
    strlcpy(result->build_label, RTW88_BUILD_LABEL, sizeof(result->build_label));
    strlcpy(result->build_channel, RTW88_BUILD_CHANNEL,
            sizeof(result->build_channel));
    result->rc_number = RTW88_RELEASE_CANDIDATE;
    result->rate_mode = rtw88_beta16_get_rate_mode();
    result->diagnostics_enabled =
        rtw88_beta16_diag_is_enabled() ? 1 : 0;
    args->structureOutputSize = sizeof(*result);
    return kIOReturnSuccess;
}


IOReturn RTW88UserClient::sReset(RTW88UserClient *uc, void *ref,
                                 IOExternalMethodArguments *args)
{
    if (!uc || !uc->_provider)
        return kIOReturnOffline;
    return uc->_provider->resetWireless();
}
