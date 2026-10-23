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

/* The parsed set: the bits to clear and the bits to set. */
struct mode_set {
	mode_t clear;
	mode_t set;
};

static mode_t
who_bits(char who, int is_dir)
{
	mode_t bits = 0;

	if (who == 'u' || who == 'a') {
		bits |= S_IRWXU;
	}
	if (who == 'g' || who == 'a') {
		bits |= S_IRWXG;
	}
	if (who == 'o' || who == 'a') {
		bits |= S_IRWXO;
	}
	if (is_dir) {
		if (who == 'u' || who == 'a') {
			bits |= S_ISUID;
		}
		if (who == 'g' || who == 'a') {
			bits |= S_ISGID;
		}
	}
	return bits;
}

static mode_t
perm_bits(char perm)
{
	switch (perm) {
	case 'r': return 4;
	case 'w': return 2;
	case 'x': return 1;
	case 'X': return 1;   /* only meaningful on directories; approximated */
	case 's': return 0;   /* setuid/setgid handled through who_bits */
	case 't': return 0;   /* sticky handled below */
	default:  return 0;
	}
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
			mode_t perms = 0;
			int any = 0;
			while (*cursor != '\0' && *cursor != ',' &&
			       *cursor != '+' && *cursor != '-' && *cursor != '=') {
				perms |= perm_bits(*cursor);
				if (*cursor == 's') {
					perms |= (who == 'u') ? S_ISUID : S_ISGID;
				}
				if (*cursor == 't') {
					perms |= S_ISVTX;
				}
				any = 1;
				cursor++;
			}
			if (!any) {
				perms = 0777;
			}
			mode_t mask = (who != 0) ? who_bits(who, 1) : 07777;
			switch (op) {
			case '+':
				result->set |= perms & mask;
				break;
			case '-':
				result->clear |= perms & mask;
				break;
			case '=':
				result->clear |= mask;
				result->set |= perms & mask;
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
