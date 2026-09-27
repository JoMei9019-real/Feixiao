/* SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause */
#pragma once

#define RTW88_VERSION_STRING        "1.0.8"
#define RTW88_BUILD_LABEL           "1.0.8 RC1"
#define RTW88_BUILD_CHANNEL         "Release Candidate"
#define RTW88_RELEASE_CANDIDATE     1

struct RTW88VersionResult {
    char version[16];
    char build_label[32];
    char build_channel[24];
    unsigned int rc_number;
    int rate_mode;
    unsigned char diagnostics_enabled;
    unsigned char reserved[3];
};
