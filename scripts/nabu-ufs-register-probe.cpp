// SPDX-License-Identifier: BSD-2-Clause-Patent
// nabu / SM8150 diagnostic service. Deliberately NOT a block driver.
//
// Only the explicit boot argument enables MMIO reads. No MMIO store, reset, transfer-list setup,
// DMA, SCSI command or block-device publication occurs -- the point is to learn whether the UFS
// clock and power registers read as expected before anything tries to own the controller.
//
// Values and register offsets follow the 1PJL/unixnu-nabu register probe, which derives them from
// the nabu device tree and Linux gcc-sm8150.c.
#include <IOKit/IOService.h>
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IODeviceMemory.h>
#include <IOKit/IOMemoryDescriptor.h>
#include <pexpert/pexpert.h>

extern "C" {
void nabu_mark(int);
void nabu_mark_text(const char *, unsigned int);
volatile unsigned int nabu_ufs_register_probe_phase = 0;
volatile unsigned int nabu_ufs_register_probe_hc_read = 0;
__attribute__((used)) char nabu_ufs_register_probe_signature[] = "nabu-ufs-register-probe-v1";
}

class NativeUfs : public IOService {
  OSDeclareDefaultStructors(NativeUfs)
public:
  IOService *probe(IOService *provider, SInt32 *score) override;
  bool start(IOService *provider) override;
};
OSDefineMetaClassAndStructors(NativeUfs, IOService)

static bool requested(void)
{
  int value = 0;
  return PE_parse_boot_argn("nabu-ufs-register-probe", &value, sizeof(value)) && value == 1;
}

IOService *NativeUfs::probe(IOService *provider, SInt32 *score)
{
  // Reuse only the existing root-provider personality so this diagnostic cannot attach to an
  // unrelated node.
  if (!requested() || !OSDynamicCast(IOPlatformExpertDevice, provider)) {
    return nullptr;
  }
  if (score) {
    *score = 500;
  }
  return this;
}

static uintptr_t mapRegisters(uint64_t physical, uint64_t size, OSSharedPtr<IOMemoryMap> &keep)
{
  IODeviceMemory *memory = IODeviceMemory::withRange(physical, size);
  if (!memory) {
    return 0;
  }
  keep = OSSharedPtr<IOMemoryMap>(
      memory->map(kIOMapAnywhere | kIOMapInhibitCache), OSNoRetain);
  memory->release();
  return keep ? static_cast<uintptr_t>(keep->getVirtualAddress()) : 0;
}

static uint32_t readRegister(uintptr_t base, unsigned int offset)
{
  __asm__ volatile("dsb sy" ::: "memory");
  const uint32_t value = *reinterpret_cast<volatile const uint32_t *>(base + offset);
  __asm__ volatile("dsb sy" ::: "memory");
  return value;
}

static void showHex(const char *label, uint32_t value, unsigned int y)
{
  // The diagnostic painter only accepts addresses inside the kernel image, so the rendered line
  // lives in the image's data rather than on a stack.
  static char line[40];
  static const char hex[] = "0123456789ABCDEF";
  unsigned int n = 0;
  while (n < 20 && label[n]) {
    line[n] = label[n];
    ++n;
  }
  line[n++] = ' ';
  line[n++] = '0';
  line[n++] = 'x';
  for (unsigned int i = 0; i < 8; ++i) {
    line[n++] = hex[(value >> (28 - 4 * i)) & 15];
  }
  line[n] = 0;
  nabu_mark_text(line, y);
}

[[noreturn]] static void finish(const char *reason)
{
  nabu_mark_text(reason, 1460);
  nabu_mark_text("TEST STOPPED - HOLD POWER TO RESTART", 1520);
  nabu_ufs_register_probe_phase = 6;
  nabu_mark(96);
  // A deliberate diagnostic stop, not a panic with variadic arguments.
  __asm__ volatile("msr daifset, #0xf" ::: "memory");
  for (;;) {
    __asm__ volatile("wfe");
  }
}

bool NativeUfs::start(IOService *provider)
{
  if (!requested() || !IOService::start(provider)) {
    return false;
  }
  OSSharedPtr<IOMemoryMap> gccMap, hcMap;
  nabu_ufs_register_probe_phase = 1;
  nabu_mark(92);
  nabu_mark_text("NABU UFS REGISTER PROBE V1", 680);
  nabu_mark_text("MODE: REGISTER READS ONLY", 740);
  nabu_mark_text("STAGE: GCC MAP", 800);

  // SM8150: GCC base 0x00100000, UFS PHY clock page at offset 0x77000. The nabu DT and Linux
  // gcc-sm8150.c describe this controller window.
  const uintptr_t gcc = mapRegisters(0x00177000ULL, 0x1000ULL, gccMap);
  if (!gcc) {
    finish("RESULT: GCC MAP FAILED");
  }
  nabu_ufs_register_probe_phase = 2;
  nabu_mark(93);
  nabu_mark_text("STAGE: GCC REGISTER READS", 800);
  const uint32_t gdsc  = readRegister(gcc, 0x04);
  const uint32_t axi   = readRegister(gcc, 0x10);
  const uint32_t ahb   = readRegister(gcc, 0x14);
  const uint32_t aggre = readRegister(gcc, 0xc0);
  nabu_ufs_register_probe_phase = 3;
  nabu_mark(94);
  showHex("GCC GDSCR", gdsc, 860);
  showHex("GCC AXI", axi, 920);
  showHex("GCC AHB", ahb, 980);
  showHex("GCC AGGRE", aggre, 1040);

  // Conservative gate: do not touch the host unless power is on and both bus clocks report
  // enabled and running. HW-gated idle clocks may fail this gate; the report is still useful and
  // nothing tries to wake them.
  const bool powered = (gdsc & 0x80000000U) != 0;
  const bool busRunning = (axi & 1U) && (ahb & 1U) &&
      !(axi & 0x80000000U) && !(ahb & 0x80000000U);
  if (!powered || !busRunning) {
    finish("RESULT: HC SKIPPED - POWER OR CLOCK GATE");
  }

  nabu_mark_text("STAGE: UFS HC MAP", 1100);
  const uintptr_t hc = mapRegisters(0x01d84000ULL, 0x3000ULL, hcMap);
  if (!hc) {
    finish("RESULT: HC MAP FAILED");
  }
  nabu_ufs_register_probe_phase = 4;
  nabu_mark(95);
  nabu_mark_text("STAGE: UFS HC REGISTER READS", 1100);
  // UFSHCI capability/version/status/enable are passive, read-only observations.
  const uint32_t cap     = readRegister(hc, 0x00);
  const uint32_t version = readRegister(hc, 0x08);
  const uint32_t status  = readRegister(hc, 0x30);
  const uint32_t enable  = readRegister(hc, 0x34);
  nabu_ufs_register_probe_hc_read = 1;
  nabu_ufs_register_probe_phase = 5;
  showHex("HC CAP", cap, 1160);
  showHex("HC VERSION", version, 1220);
  showHex("HC STATUS", status, 1280);
  showHex("HC ENABLE", enable, 1340);
  finish("RESULT: HC REGISTERS READ - NO DISK IO");
}
