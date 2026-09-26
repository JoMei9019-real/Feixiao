#include "../src/kext/RTW88PeerAmpdu.h"
#include <assert.h>

int main()
{
    uint8_t ies[42] = {};
    ies[0] = 45; ies[1] = 26;
    ies[4] = 2 | (5 << 2);
    ies[28] = 191; ies[29] = 12;
    const uint32_t caps = 6u << 23;
    for (unsigned i = 0; i < 4; ++i) ies[30 + i] = caps >> (8 * i);
    auto p = rtw88ParsePeerAmpdu(ies, sizeof(ies));
    assert(p.has_ht && p.ht_factor == 2 && p.ht_density == 5);
    assert(p.has_vht && p.vht_factor == 6);

    for (size_t n = 0; n < sizeof(ies); ++n) {
        p = rtw88ParsePeerAmpdu(ies, n);
        assert(p.has_ht == (n >= 28));
        assert(!p.has_vht);
    }

    const uint8_t short_ht[] = {45, 3, 0, 0, 31};
    assert(!rtw88ParsePeerAmpdu(short_ht, sizeof(short_ht)).has_ht);

    const uint8_t truncated[] = {1, 255, 0};
    assert(!rtw88ParsePeerAmpdu(truncated, sizeof(truncated)).has_ht);
    assert(!rtw88ParsePeerAmpdu(nullptr, 100).has_ht);

    uint8_t unknown[44] = {222, 0};
    for (size_t i = 0; i < sizeof(ies); ++i) unknown[i + 2] = ies[i];
    p = rtw88ParsePeerAmpdu(unknown, sizeof(unknown));
    assert(p.has_ht && p.has_vht);
}
