/* SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause */
#ifndef RTW88_PEER_AMPDU_H
#define RTW88_PEER_AMPDU_H

#include <stdint.h>
#include <stddef.h>

struct RTW88PeerAmpdu {
    uint8_t ht_factor;
    uint8_t ht_density;
    uint8_t vht_factor;
    bool has_ht;
    bool has_vht;
};

/* Receive limits advertised by the AP, not by our own radio. Decode wire
 * bytes explicitly: the shim's HT/VHT structs are not wire-format structs. */
static inline RTW88PeerAmpdu rtw88ParsePeerAmpdu(const uint8_t *ies, size_t len)
{
    RTW88PeerAmpdu out = {};
    if (!ies) return out;
    for (size_t pos = 0; len - pos >= 2; ) {
        const uint8_t id = ies[pos];
        const size_t size = ies[pos + 1];
        pos += 2;
        if (size > len - pos) break;
        const uint8_t *p = ies + pos;
        if (id == 45 && size >= 26) {
            out.ht_factor = p[2] & 3;
            out.ht_density = (p[2] >> 2) & 7;
            out.has_ht = true;
        } else if (id == 191 && size >= 12) {
            const uint32_t caps = (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
                                  ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
            out.vht_factor = (caps >> 23) & 7;
            out.has_vht = true;
        }
        pos += size;
    }
    return out;
}

#endif
