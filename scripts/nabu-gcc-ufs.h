/*
 * nabu (SM8150) UFS board constants.
 *
 * Extracted from:
 *   - arch/arm64/boot/dts/qcom/sm8150.dtsi   (addresses, interrupts, clock names)
 *   - include/dt-bindings/clock/qcom,gcc-sm8150.h (clock / reset / GDSC ids)
 *
 * These are the SM8150 values. The sheng (SM8550) tree uses a different GccUfs.h;
 * do NOT reuse it on nabu. Physical windows:
 *   UFS HC  0x01d84000 len 0x2500    ICE 0x01d90000 len 0x8000
 *   UFS PHY 0x01d87000 len 0x1000
 *   GCC     0x00100000 len 0x1f0000
 *   UFS interrupt GIC_SPI 265 (hardware irq 297)
 *   lanes-per-direction 2
 */

#ifndef NABU_GCC_UFS_H
#define NABU_GCC_UFS_H

/* --- physical windows --- */
#define NABU_UFS_HC_BASE   0x01d84000u
#define NABU_UFS_HC_SIZE   0x00002500u
#define NABU_UFS_ICE_BASE  0x01d90000u
#define NABU_UFS_ICE_SIZE  0x00008000u
#define NABU_UFS_PHY_BASE  0x01d87000u
#define NABU_UFS_PHY_SIZE  0x00001000u
#define NABU_GCC_BASE      0x00100000u
#define NABU_GCC_SIZE      0x001f0000u

/* UFS HC interrupt: GIC_SPI 265 -> hwirq = 32 + 265 = 297 */
#define NABU_UFS_SPI       265
#define NABU_UFS_HWIRQ     (32 + NABU_UFS_SPI)
#define NABU_UFS_LANES     2

/* --- GCC clock ids (qcom,gcc-sm8150.h) --- */
#define NABU_GCC_UFS_PHY_AXI_CLK            157
#define NABU_GCC_AGGRE_UFS_PHY_AXI_CLK        3
#define NABU_GCC_UFS_PHY_AHB_CLK            156
#define NABU_GCC_UFS_PHY_UNIPRO_CORE_CLK    169
#define NABU_GCC_UFS_PHY_UNIPRO_CORE_CLK_SRC 170
#define NABU_GCC_UFS_PHY_TX_SYMBOL_0_CLK    168
#define NABU_GCC_UFS_PHY_RX_SYMBOL_0_CLK    166
#define NABU_GCC_UFS_PHY_RX_SYMBOL_1_CLK    167
#define NABU_GCC_UFS_PHY_ICE_CORE_CLK       160
#define NABU_GCC_UFS_MEM_CLKREF_CLK         155

/* reset (GCC_UFS_PHY_BCR) */
#define NABU_GCC_UFS_PHY_BCR                25

/* power domain (UFS_PHY_GDSC) */
#define NABU_UFS_PHY_GDSC                    3

/* ref clock from RPMH (RPMH_CXO_CLK) - board-level, not GCC */
#define NABU_RPMH_CXO_CLK                  0x1

#endif /* NABU_GCC_UFS_H */
