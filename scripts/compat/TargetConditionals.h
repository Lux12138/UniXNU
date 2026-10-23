/* Darwin's <TargetConditionals.h> for building xnu on Linux.
 *
 * It answers "which Apple platform is this" with compile-time macros. A host build is none of
 * them, so the TARGET_OS_* family all resolve to 0 and the code that guards on them takes the
 * neutral path. The _SUPPORT_* macros say whether the compiler can target that platform at all;
 * on Linux it cannot, so they are 0 as well.
 *
 * prepare-storage-headers.py copies the real one out of a macOS SDK when there is one; this file
 * is the fallback for hosts without an SDK.
 */
#ifndef __TARGETCONDITIONALS__
#define __TARGETCONDITIONALS__

#define TARGET_OS_MAC               0
#define TARGET_OS_OSX               0
#define TARGET_OS_IPHONE            0
#define TARGET_OS_IOS               0
#define TARGET_OS_WATCH             0
#define TARGET_OS_TV                0
#define TARGET_OS_VISION            0
#define TARGET_OS_BRIDGE            0
#define TARGET_OS_DRIVERKIT         0
#define TARGET_OS_SIMULATOR         0
#define TARGET_OS_EMBEDDED          0
#define TARGET_OS_MACCATALYST       0
#define TARGET_OS_NANO              0
#define TARGET_OS_WIN32             0
#define TARGET_OS_UNIX              1
#define TARGET_OS_LINUX             1

#define TARGET_OS_UIKITFORMAC       0
#define TARGET_OS_XR                0

/* Which SDKs the toolchain can produce output for. */
#define TARGET_OS_MAC_SUPPORT       0
#define TARGET_OS_OSX_SUPPORT       0
#define TARGET_OS_IPHONE_SUPPORT    0
#define TARGET_OS_IOS_SUPPORT       0
#define TARGET_OS_WATCH_SUPPORT     0
#define TARGET_OS_TV_SUPPORT        0
#define TARGET_OS_VISION_SUPPORT    0
#define TARGET_OS_DRIVERKIT_SUPPORT 0

#define TARGET_CPU_PPC              0
#define TARGET_CPU_PPC64            0
#define TARGET_CPU_68K             0
#define TARGET_CPU_X86              1
#define TARGET_CPU_X86_64           1
#define TARGET_CPU_ARM              0
#define TARGET_CPU_ARM64            0
#define TARGET_CPU_MIPS             0
#define TARGET_CPU_SPARC            0
#define TARGET_CPU_ALPHA            0

#define TARGET_RT_MAC_CFM           0
#define TARGET_RT_MAC_MACHO         0
#define TARGET_RT_LITTLE_ENDIAN     1
#define TARGET_RT_BIG_ENDIAN        0
#define TARGET_RT_64_BIT            1

#endif /* __TARGETCONDITIONALS__ */
