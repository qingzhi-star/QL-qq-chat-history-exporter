# 兼容性矩阵

每次真机验证一行。**不记录** uin、完整用户路径、昵称、消息样本；只记录
版本、格式形状、cipher 指纹、WAL 状态与检查结论（修正案 A §13.2）。

| 验证日期 | Windows 版本 / 架构 | Python | QQ 版本 | wrapper 形状 | cipher 指纹 | WAL 状态 | 检查结论 |
|---|---|---|---|---|---|---|---|
| 2026-10-28 | Windows 11 专业版 10.0.26200 / x64 | 3.14.6 | 9.9.36-53644 | 1024 字节自定义头 + 4096 页；`size % 4096 == 1024` | `sha512/sha1/48` | `ok`：45 帧，最后 commit 第 45 帧，commit 后 415 页；13/20 个已提交页与主库不同 | **PASS**：doctor 11/11 ok；`quick_check == ok`；`c2c_msg_table` / `group_msg_table` 可 `SELECT COUNT(*)`（86 / 985）；同一快照两次解密 SHA-256 一致；源目录 identity 三元组未变；页 1 SQLite reserved bytes = 80（≠ 密文尾 reserve 48，R34） |
| 2026-10-30 | 同上 | 3.14.6 | 9.9.36-53644 | 同上；文件 1024 页 / 头声明 698 页（R36） | `sha512/sha1/48` | `ok`：93 帧，最后 commit 93，commit 后 698 页 | **P1 PASS**：`list` 可读标题；真实 c2c+group 导出 643 条（0 降级）；txt BOM、html 零外链、pdf `%PDF-` 34 KB；媒体 78 找到/50 缺失占位；同一快照两次导出字节一致；源库 identity 未变；无 `.partial` |

## 备注

- **P2 候选版（2026-11-06）**：Windows 11 / Python 3.14.6，普通测试 623 通过、
  10 live 排除；未访问 QQ 进程内存。十万条/两万张合成图 GUI、五十万条搜索、五十
  会话队列及真实 Edge PDF/取消见 [P2-performance.md](P2-performance.md)。这些是
  合成集成证据，不延伸到未经验证的 QQ 版本或 Windows 10。
- T09 远端 Python 3.12/3.13/3.14 矩阵全通过：
  [run 42147204106](https://github.com/qingzhi-star/QL-qq-chat-history-exporter/actions/runs/42147204106)。
  最终 P2 构建在最后提交重新跑版本/冻结安装冒烟；不要复用历史正式版真机证据。

- 同日另做一次只读 P1 探测（脱敏）：32 张表；`c2c_msg_table` 86 行、
  `group_msg_table` 991 行；`40800` blob 长度 c2c 中位 103 B / 最大 1522 B，
  group 中位 88 B / 最大 3400 B；解密 1.7 MB 耗时 0.14 s；WAL 61 帧。
  `discuss_msg_table` 等表存在但不在 P0 关键表清单内，留作 P1 输入。
- **fixture 已采集并审查**（2026-10-29）：`nt_msg_header_page1.bin` 5120 字节，
  provenance 只含日期/QQ 版本/页数/字节数/cipher 指纹；页 1 解密后 63/4096
  非零字节、无可打印敏感文本，8 项 fixture 测试 PASS。注意：主库 page 1 的
  schema 尚未 checkpoint（在 WAL 里），fixture 钉的是头/盐/HMAC 与魔数。
- **CI 矩阵**（`.github/workflows/tests.yml`）：windows-latest 上
  Python **3.12 / 3.13 / 3.14** 三腿，跑 `pytest`（live 排除）与只读隐私巡检；
  run `40821758496`、`40821952392` 全绿。CI 不使用真实 QQ 数据/密钥，
  两项口令 fixture 测试按预期 SKIP。
- **Python 3.12**：本机只有 3.14，由 CI 矩阵验证（R35），不再算未验证。
- 出现新版本不兼容时，诊断应说「未验证 / 暂不支持该格式」，不得误导为
  「口令错误」。

## Electron 0.3.0 发行范围

本次正式版的已验证系统是 Windows 11 x64；Windows 10 与其他架构未验证，不标 PASS。
Python/Node 为随包内核与运行库，用户无需另行安装。PDF 使用 Electron 内置打印引擎。
冻结包的归档/搜索/TXT/HTML/PDF、源数据只读、安装/卸载、双栏 GUI 和帧间隔验证
由同提交的 tools/smoke_electron.py 生成；正式包发行门要求该报告与产物清单哈希一致。
旧表及旧性能记录不能替代这份同构建证据。

## Electron 0.4.2rc2 候选版

验证日期为 2026-11-19，分发构建源自 `e7d7d5e`。验收使用同一构建清单核对安装包、便携包及文件哈希。

| 系统或场景 | 证据 | 结论 |
| --- | --- | --- |
| Windows 11 x64 · 26200 | 中文与空格路径完整解压。真实安装器安装、启动、卸载均成功。 | PASS |
| Windows 11 x64 · 离线导出 | 隔离运行环境使用包内冻结内核，合成加密归档、搜索、TXT／HTML／PDF 和源文件哈希对比通过。 | PASS |
| Windows 11 x64 · 界面回归 | 独立桌面离屏运行。五轮合成便携版首条消息中位数 78 ms，随机跳转稳定中位数 53 ms。 | PASS，离屏样本 |
| Windows 10 22H2 x64 | 当前构建尚无来宾环境结果。 | 未验证 |
| 真实 QQ 数据、前台性能 | 当前构建尚无授权真机样本和目标前台环境的结果。 | 未验证 |

当前候选版的发布范围为 Windows 11 x64。普通回归、Windows Python 矩阵和 Electron 验证可查阅 [GitHub Actions](https://github.com/qingzhi-star/QL-qq-chat-history-exporter/actions/runs/44496705350)。

## Electron 0.4.1 正式版

2026-11-20 对源码提交 `304771c` 的发行包验收。Windows 11 x64 通过中文与空格路径启动、安装及卸载、隐私选择和离线 TXT／HTML／PDF 导出。测试限制应用进程的系统运行库搜索路径，验证随包内核与合成源数据只读。Windows 10 和真实 QQ 数据仍待同构建验收。[正式版](https://github.com/qingzhi-star/QL-qq-chat-history-exporter/releases/tag/v0.4.1) · [对应源码 CI](https://github.com/qingzhi-star/QL-qq-chat-history-exporter/actions/runs/44746708500)
