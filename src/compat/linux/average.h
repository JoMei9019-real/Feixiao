/* SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause */
#ifndef _RTW88_COMPAT_AVERAGE_H
#define _RTW88_COMPAT_AVERAGE_H

#include "types.h"
#include "kernel.h"

/*
 * Exponentially Weighted Moving Average (EWMA).
 *
 * Match Linux include/linux/average.h semantics exactly:
 * _precision is the number of fractional bits and _weight_rcp is the
 * reciprocal weight (a power of two), not a shift count.  rtw88 declares
 * RSSI as DECLARE_EWMA(rssi, 10, 16), therefore the smoothing shift is
 * ilog2(16) == 4.
 */
#define DECLARE_EWMA(name, _precision, _weight_rcp)                       \
    struct ewma_##name {                                                   \
        unsigned long internal;                                            \
    };                                                                     \
    static inline void ewma_##name##_init(struct ewma_##name *e)          \
    {                                                                      \
        e->internal = 0;                                                   \
    }                                                                      \
    static inline unsigned long ewma_##name##_read(struct ewma_##name *e) \
    {                                                                      \
        return e->internal >> (_precision);                                \
    }                                                                      \
    static inline void ewma_##name##_add(struct ewma_##name *e,           \
                                          unsigned long val)               \
    {                                                                      \
        unsigned long internal = e->internal;                              \
        unsigned long weight = ilog2(_weight_rcp);                         \
        unsigned long precision = (_precision);                            \
        e->internal = internal ?                                           \
            (((internal << weight) - internal) +                           \
             (val << precision)) >> weight :                              \
            (val << precision);                                            \
    }

#endif /* _RTW88_COMPAT_AVERAGE_H */
