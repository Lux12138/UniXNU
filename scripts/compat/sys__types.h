/* Darwin's <sys/_types.h> subset for building xnu's SETUP host tools on Linux.
 *
 * libkern/_OSByteOrder.h includes this for the __darwin_* fixed-width spellings. glibc supplies
 * the types through <stdint.h>; only the names differ, so map them rather than pulling in the
 * whole Darwin sys tree.
 */
#ifndef _DARWIN_SYS__TYPES_H_
#define _DARWIN_SYS__TYPES_H_

#include <stdint.h>
#include <sys/types.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef int8_t    __int8_t;
typedef uint8_t   __uint8_t;
typedef int16_t   __int16_t;
typedef uint16_t  __uint16_t;
typedef int32_t   __int32_t;
typedef uint32_t  __uint32_t;
typedef int64_t   __int64_t;
typedef uint64_t  __uint64_t;

typedef unsigned char      __darwin_uuid_t[16];
typedef char               __darwin_uuid_string_t[37];

typedef unsigned long      __darwin_size_t;
typedef long               __darwin_ssize_t;
typedef long               __darwin_off_t;
typedef int                __darwin_pid_t;
typedef unsigned int       __darwin_uid_t;
typedef unsigned int       __darwin_gid_t;
typedef unsigned int       __darwin_mode_t;
typedef long long          __darwin_time_t;
typedef long               __darwin_suseconds_t;
typedef unsigned char      __darwin_u_char;
typedef unsigned short     __darwin_u_short;
typedef unsigned int       __darwin_u_int;
typedef unsigned long      __darwin_u_long;
typedef unsigned char      __darwin_boolean_t;

/* libkern/_OSByteOrder.h uses these through architecture/byte_order.h */
#ifndef __DARWIN_OSSwapConstInt16
#define __DARWIN_OSSwapConstInt16(x) ((uint16_t)((((uint16_t)(x) & 0xff00) >> 8) | \
                                                 (((uint16_t)(x) & 0x00ff) << 8)))
#endif
#ifndef __DARWIN_OSSwapConstInt32
#define __DARWIN_OSSwapConstInt32(x) ((uint32_t)((((uint32_t)(x) & 0xff000000) >> 24) | \
                                                 (((uint32_t)(x) & 0x00ff0000) >>  8) | \
                                                 (((uint32_t)(x) & 0x0000ff00) <<  8) | \
                                                 (((uint32_t)(x) & 0x000000ff) << 24)))
#endif
#ifndef __DARWIN_OSSwapConstInt64
#define __DARWIN_OSSwapConstInt64(x) ((uint64_t)((((uint64_t)(x) & 0xff00000000000000ULL) >> 56) | \
                                                 (((uint64_t)(x) & 0x00ff000000000000ULL) >> 40) | \
                                                 (((uint64_t)(x) & 0x0000ff0000000000ULL) >> 24) | \
                                                 (((uint64_t)(x) & 0x000000ff00000000ULL) >>  8) | \
                                                 (((uint64_t)(x) & 0x00000000ff000000ULL) <<  8) | \
                                                 (((uint64_t)(x) & 0x0000000000ff0000ULL) << 24) | \
                                                 (((uint64_t)(x) & 0x000000000000ff00ULL) << 40) | \
                                                 (((uint64_t)(x) & 0x00000000000000ffULL) << 56)))
#endif

#ifdef __cplusplus
}
#endif

#endif /* _DARWIN_SYS__TYPES_H_ */
