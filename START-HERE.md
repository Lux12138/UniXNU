# START HERE — 本仓库是 nabu (小米平板5 / SM8150) 的内核 fork

> 新会话接手必读。**不读就动手 = 重踩今天十个坑。**

## 完整交接在另一个仓库

**主交接文档在 `Lux12138/unixnu-nabu`**：`START-HERE.md` → `HANDOVER-2026-10-24-ROLLBACK.md`
→ `HANDOVER-exec-fault.md`（689 行主线记录）。

那边还放着 `PUSH-GOTCHA.md`（git push 假成功的坑）。

## 本仓库当前 HEAD

**`aae83c4`** —— 纯探针版（reason creator 探针 RN=/RA=），**无 DWC3、无重启调用**。
刷机后屏幕停在 `unexpected SIGKILL of launchd`，`ESR=2516582469`。

## 本仓库的三条硬规矩

1. **改 `scripts/*.py` 必须 commit + 验证远端**：
   ```bash
   git fetch -q origin main
   git show origin/main:scripts/<file>.py | grep -c '<你的改动>'
   ```
   `build_verify.sh` 每轮 `git reset --hard FETCH_HEAD`，本地未提交的一律被冲掉。
   **`git push` 会返回 exit=0 但不生效** —— 唯一可信的验证是上面的 `git show`。

2. **加新探针挂在 `scripts/nabu-reason-probes.py`**（改 `sys_reason.c`，行 2100/2180）。
   它是**每轮必重编译**的落点（RN/RA 每次都出现在屏幕上）。
   **`osfmk/kern/debug.c` 的对象永不重建**，改它无效 —— 别再浪费轮次。

3. **屏幕探针行号**：已占用 1780/2180/2420/2500（status-rows）、2100/2180（reason 探针）。
   新探针选 ≥80px 间距的空行，避开 <1780（console 带）。
   **"没显示"先查行冲突，不是"没执行"**。

## 构建

```bash
bash /mnt/c/Temp/auto/build_pack_short.sh
```
成功判据：`/tmp/bv2.log` 有 `built kernel at`、**无** `KERNEL NOT REGENERATED`，
且 `out/nabu/kernel/kernel.macho` 的 **md5 变化**。

不产出新内核时：`rm -rf out/nabu/tree/build/xnu/ios-obj` 全量重建。

## 相关仓库

| 仓库 | 用途 |
|---|---|
| `Lux12138/unixnu-nabu` | 板级配置 + **全部交接文档** |
| `Lux12138/NativeDwc3` | USB 驱动（能编译链接，但**缺 GCC 时钟会崩**，别接回 board.toml） |
| `Lux12138/xnu-linux-toolchain` | Linux 构建工具链 fork |
