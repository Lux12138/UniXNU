/* BSD's setmode(3) / getmode(3) for building xnu's SETUP tools on Linux.
 *
 * setmode parses a chmod-style symbolic mode string ("u+x", "go-w", "a=rw") plus octal forms, and
 * getmode applies the parsed set to a base mode. installfile.c uses the pair to honour the -m flag
 * of install(1). glibc has no equivalent.
 */
#define _GNU_SOURCE
#include <libc.h>

#include <ctype.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

/* The parsed set: the bits to clear and the bits to set, already shifted into place. */
struct mode_set {
	mode_t clear;
	mode_t set;
};

/* Shift for a who-class: owner lives at bit 6, group at 3, other at 0. */
static int
who_shift(char who)
{
	switch (who) {
	case 'u': return 6;
	case 'g': return 3;
	case 'o': return 0;
	default:  return -1;   /* 'a' or unset: all three */
	}
}

/* r/w/x as a 3-bit value, applied at the who shift above. */
static mode_t
perm_bits(char perm, int shift)
{
	mode_t value = 0;

	switch (perm) {
	case 'r': value = 4; break;
	case 'w': value = 2; break;
	case 'x': value = 1; break;
	case 'X': value = 1; break;   /* approximated: treated as x */
	case 's': return (shift == 6) ? S_ISUID : (shift == 3) ? S_ISGID : 0;
	case 't': return S_ISVTX;
	default:  return 0;
	}
	return (mode_t)(value << shift);
}

void *
setmode(const char *mode_string)
{
	if (mode_string == NULL) {
		errno = EINVAL;
		return NULL;
	}

	/* Pure octal form. */
	if (isdigit((unsigned char)mode_string[0])) {
		char *end = NULL;
		unsigned long value = strtoul(mode_string, &end, 8);
		if (end != NULL && *end == '\0') {
			struct mode_set *octal = calloc(1, sizeof(*octal));
			if (octal == NULL) {
				return NULL;
			}
			octal->set = (mode_t)value;
			octal->clear = 07777;
			return octal;
		}
	}

	struct mode_set *result = calloc(1, sizeof(*result));
	if (result == NULL) {
		return NULL;
	}

	const char *cursor = mode_string;
	while (*cursor != '\0') {
		/* who */
		char who = 0;
		if (*cursor == 'u' || *cursor == 'g' || *cursor == 'o') {
			who = *cursor++;
		} else if (*cursor == 'a') {
			who = 'a';
			cursor++;
		} else if (*cursor != '+' && *cursor != '-' && *cursor != '=') {
			free(result);
			errno = EINVAL;
			return NULL;
		}

		while (*cursor == '+' || *cursor == '-' || *cursor == '=') {
			char op = *cursor++;
			int shift = (who != 0) ? who_shift(who) : -1;
			mode_t perms = 0;
			int any = 0;

			while (*cursor != '\0' && *cursor != ',' &&
			       *cursor != '+' && *cursor != '-' && *cursor != '=') {
				if (shift >= 0) {
					perms |= perm_bits(*cursor, shift);
				} else {
					/* 'a' or no who: apply at all three shifts */
					perms |= perm_bits(*cursor, 6);
					perms |= perm_bits(*cursor, 3);
					perms |= perm_bits(*cursor, 0);
				}
				any = 1;
				cursor++;
			}
			if (!any) {
				perms = (shift >= 0) ? ((mode_t)07 << shift) : 0777;
			}

			mode_t mask = (shift >= 0) ? ((mode_t)07777 & ~((mode_t)077 << shift))
			                           : 07777;
			switch (op) {
			case '+':
				result->set = (mode_t)((result->set & ~mask) | (perms & mask));
				break;
			case '-':
				result->clear |= (mode_t)(perms & mask);
				break;
			case '=':
				result->clear |= mask;
				result->set = (mode_t)((result->set & ~mask) | (perms & mask));
				break;
			}
		}
		if (*cursor == ',') {
			cursor++;
		}
	}
	return result;
}

mode_t
getmode(const void *set, mode_t base)
{
	const struct mode_set *parsed = set;
	if (parsed == NULL) {
		return base;
	}
	return (mode_t)((base & ~parsed->clear) | parsed->set);
}
