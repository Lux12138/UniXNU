/* Darwin host compatibility shims for building xnu's SETUP tools on Linux.
 *
 * xnu's host tools assume a few libc functions Darwin provides and glibc does not. Forcing this
 * header in (-include) keeps the fact in one place instead of patching every SETUP makefile.
 *
 * Provided by libhostcompat:
 *   getprogname / setprogname   Darwin's program-name accessors
 *   strlcpy / strlcat           present in glibc >= 2.38, guarded below anyway
 */
#ifndef _HOSTCOMPAT_H_
#define _HOSTCOMPAT_H_

#include <stddef.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Darwin: getprogname() returns the short program name. glibc has
 * program_invocation_short_name, which is the same thing. */
const char *hostcompat_getprogname(void);
void hostcompat_setprogname(const char *name);

#ifndef getprogname
#define getprogname() hostcompat_getprogname()
#endif

#ifndef setprogname
#define setprogname(name) hostcompat_setprogname(name)
#endif

/* glibc 2.38 added strlcpy/strlcat; older ones need ours. */
#if !defined(__GLIBC__) || (__GLIBC__ < 2) || (__GLIBC__ == 2 && __GLIBC_MINOR__ < 38)
size_t hostcompat_strlcpy(char *dst, const char *src, size_t size);
size_t hostcompat_strlcat(char *dst, const char *src, size_t size);
#ifndef strlcpy
#define strlcpy hostcompat_strlcpy
#endif
#ifndef strlcat
#define strlcat hostcompat_strlcat
#endif
#endif

/* Darwin's <sys/cdefs.h> spells these differently from glibc. */
#ifndef __printflike
#define __printflike(fmtarg, firstvararg) __attribute__((__format__(__printf__, fmtarg, firstvararg)))
#endif

#ifndef __unused
#define __unused __attribute__((__unused__))
#endif

#ifndef __dead2
#define __dead2 __attribute__((__noreturn__))
#endif

#ifndef __pure2
#define __pure2 __attribute__((__const__))
#endif

#ifdef __cplusplus
}
#endif

#endif /* _HOSTCOMPAT_H_ */
