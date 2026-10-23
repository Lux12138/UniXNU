/* Darwin host compatibility shims for building xnu's SETUP tools on Linux.
 * See hostcompat.h for what this provides and why. */
#define _GNU_SOURCE
#include "hostcompat.h"

#include <errno.h>
#include <stdlib.h>
#include <string.h>

/* glibc keeps the short name of the running program here. */
extern char *program_invocation_short_name;

const char *hostcompat_getprogname(void)
{
	return program_invocation_short_name ? program_invocation_short_name : "";
}

void hostcompat_setprogname(const char *name)
{
	if (name) {
		program_invocation_short_name = (char *)name;
	}
}

#if !defined(__GLIBC__) || (__GLIBC__ < 2) || (__GLIBC__ == 2 && __GLIBC_MINOR__ < 38)
size_t hostcompat_strlcpy(char *dst, const char *src, size_t size)
{
	size_t len = strlen(src);
	if (size > 0) {
		size_t copy = len >= size ? size - 1 : len;
		memcpy(dst, src, copy);
		dst[copy] = '\0';
	}
	return len;
}

size_t hostcompat_strlcat(char *dst, const char *src, size_t size)
{
	size_t dlen = strnlen(dst, size);
	size_t slen = strlen(src);
	if (dlen == size) {
		return size + slen;
	}
	if (slen < size - dlen) {
		memcpy(dst + dlen, src, slen + 1);
	} else {
		memcpy(dst + dlen, src, size - dlen - 1);
		dst[size - 1] = '\0';
	}
	return dlen + slen;
}
#endif
