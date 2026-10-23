/* Darwin's <mach/mach_init.h> subset for building xnu's SETUP host tools on Linux.
 *
 * setsegname reaches this through <mach-o/swap.h> -> <architecture/byte_order.h> on some paths.
 * The SETUP tools only need the mach_port_t spelling, not the Mach runtime.
 */
#ifndef _DARWIN_MACH_MACH_INIT_H_
#define _DARWIN_MACH_MACH_INIT_H_

#include <mach/mach_types.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Darwin declares the bootstrap port here. A host build tool never talks to Mach, so the value
 * only has to exist and be comparable. */
extern mach_port_t mach_task_self_;

#ifdef __cplusplus
}
#endif

#endif /* _DARWIN_MACH_MACH_INIT_H_ */
