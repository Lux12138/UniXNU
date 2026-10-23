/* Darwin's <copyfile.h> for building xnu's SETUP/installfile on Linux.
 *
 * Only the surface installfile.c uses is provided: copyfile() with COPYFILE_ALL, plus the flags it
 * can combine. On Linux this is a plain read/write copy -- the metadata semantics of the Darwin
 * version (ACLs, extended attributes, resource forks) do not apply to a host build tool.
 */
#ifndef _DARWIN_COPYFILE_H_
#define _DARWIN_COPYFILE_H_

#include <stdint.h>
#include <sys/types.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct _copyfile_state *copyfile_state_t;
typedef int (*copyfile_callback_t)(int, int, copyfile_state_t, const char *, const char *, void *);

/* The flag set installfile.c uses. Values are Darwin's, so source that tests individual bits
 * behaves identically. */
#define COPYFILE_ACL       (1 << 0)
#define COPYFILE_STAT      (1 << 1)
#define COPYFILE_XATTR     (1 << 2)
#define COPYFILE_DATA      (1 << 3)

#define COPYFILE_SECURITY  (COPYFILE_STAT | COPYFILE_ACL)
#define COPYFILE_METADATA  (COPYFILE_SECURITY | COPYFILE_XATTR)
#define COPYFILE_ALL       (COPYFILE_METADATA | COPYFILE_DATA)

/* Error codes the caller may compare against. */
#define COPYFILE_RECURSE_ERROR  0
#define COPYFILE_RECURSION      1
#define COPYFILE_COPY_DATA      2
#define COPYFILE_COPY_XATTR     3
#define COPYFILE_START          4
#define COPYFILE_FINISH         5
#define COPYFILE_ERR            6
#define COPYFILE_PROGRESS       7

#define COPYFILE_CONTINUE       0
#define COPYFILE_SKIP           1
#define COPYFILE_QUIT           2

int copyfile(const char *from, const char *to, copyfile_state_t state, uint32_t flags);
int fcopyfile(int from_fd, int to_fd, copyfile_state_t state, uint32_t flags);
const char *copyfile_strerror(int error);

#ifdef __cplusplus
}
#endif

#endif /* _DARWIN_COPYFILE_H_ */
