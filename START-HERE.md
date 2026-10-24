# START HERE — 本仓库是 nabu (小米平板5 / SM8150) 的内核 fork

> 新会话接手必读。**不读全就动手 = 重踩今天十个坑。**

## 完整交接在另一个仓库

**主交接在 `Lux12138/unixnu-nabu`**，三份按顺序读：

1. `START-HERE.md` —— 铁律、基线、复现命令、坑速查
2. **`DOCS-INDEX.md`** —— 云端全部 18 份文档的索引（每份讲什么、什么时候读）
3. `HANDOVER-2026-10-24-ROLLBACK.md` → `HANDOVER-exec-fault.md`（689 行主线）

那边还有 `PUSH-GOTCHA.md`（git push 假成功的坑）和 `STATUS.md`（40K 逐轮流水）。

## 必须研读全部文档和全部提交记录

```bash
cd ~/src/unixnu-nabu && git log --oneline -60
cd ~/src/UniXNU      && git log --oneline -60
```

**每条 commit message 都要看** —— 它们是当轮的实测结论，不是套话。
例如 `5488c9e`（PAC 修复机制）、`bcedff4`（vm_page_free_count 是后果不是原因）、
`6373972`（探针弯路的十个流程错误）、`5b095ac`（DWC3 为什么崩，已回滚）。

## 本仓库当前 HEAD

**`aae83c4`** —— 纯探针版（reason creator 探针 RN=/RA=），**无 DWC3、无重启调用**。
刷机后屏幕停在 `unexpected SIGKILL of launchd`，`ESR=2516582469`。

## 本仓库的四条硬规矩

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

4. **验证判据要选"应当存在"的东西**：`count = 0` 恒真，不能当成功证据。
   用 **md5 变化** + **应存在的字符串 count > 0**。

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
| `Lux12138/unixnu-nabu` | 板级配置 + **全部交接文档（18 份）** |
| `Lux12138/NativeDwc3` | USB 驱动（能编译链接，但**缺 GCC 时钟会崩**，别接回 board.toml） |
| `Lux12138/xnu-linux-toolchain` | Linux 构建工具链 fork（含 `docs/NABU-18-PITFALLS.md`） |
