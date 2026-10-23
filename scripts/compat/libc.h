/* Darwin's <libc.h> for building xnu's SETUP host tools on Linux.
 *
 * The host tools include it for malloc/free wrappers and the OSAtomic* helpers. glibc supplies the
 * libc side; the atomic helpers are mapped onto GCC/Clang builtins.
 */
#ifndef _DARWIN_LIBC_H_
#define _DARWIN_LIBC_H_

#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>

/* Darwin's unistd.h declares these; glibc keeps them in <stdlib.h>. */
#ifndef __APPLE__

#include <fcntl.h>

#ifdef __cplusplus
extern "C" {
#endif

/* OSAtomic* increments return the new value; the *Barrier variants are the same on x86. */
static inline int32_t OSAtomicIncrement32(volatile int32_t *v) { return __sync_add_and_fetch(v, 1); }
static inline int32_t OSAtomicDecrement32(volatile int32_t *v) { return __sync_sub_and_fetch(v, 1); }
static inline int32_t OSAtomicAdd32(int32_t d, volatile int32_t *v) { return __sync_add_and_fetch(v, d); }
static inline int32_t OSAtomicIncrement32Barrier(volatile int32_t *v) { return OSAtomicIncrement32(v); }
static inline int32_t OSAtomicDecrement32Barrier(volatile int32_t *v) { return OSAtomicDecrement32(v); }
static inline bool OSAtomicCompareAndSwap32Barrier(int32_t o, int32_t n, volatile int32_t *v)
{
	return __sync_bool_compare_and_swap(v, o, n);
}

#ifdef __cplusplus
}
#endif

#endif /* !__APPLE__ */

#endif /* _DARWIN_LIBC_H_ */
