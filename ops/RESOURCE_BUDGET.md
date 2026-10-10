# 本机资源预算

适用机器：2 vCPU、约 3.6 GiB RAM。这里的 Codex 执行节点运行 CLI、工具和模型连接；模型推理由上游服务完成，执行过程仍会消耗本机资源。

## 当前设置

- Multica daemon 的现有全局并发为 2，保留不变；该限制在同一 daemon 的运行时之间共享。
- 小红书甜蜜代聊、智能回复助手各限制为单并发；项目操作助手原有单并发不变。
- 执行服务的全部子进程共享一个 CPU 核的配额；CPU/IO 权重为 50。
- 内存达到 640 MiB 后加强回收，硬上限为 1 GiB；Swap 上限为 256 MiB。
- Channel 与 XHS 的 CPU/IO 权重设为 200，争用时优先处理消息和请求。

`MemoryHigh` 会计入文件缓存，触发后可能增加执行延迟；达到 `MemoryMax` 且无法回收时，内核可能终止执行服务内的进程。因此这份预算用于保护整机，不保证大型编译或浏览器任务一定成功。它也不会清空历史 Swap 或凭空释放正在使用的内存。

## 安装和在线应用

```bash
sudo install -d /etc/systemd/system/multica-agent-runtime.service.d
sudo install -m 0644 ops/multica-agent-runtime-resources.conf /etc/systemd/system/multica-agent-runtime.service.d/30-resources.conf
sudo systemctl daemon-reload
sudo systemctl set-property --runtime multica-agent-runtime.service CPUAccounting=yes MemoryAccounting=yes CPUQuota=100% CPUWeight=50 IOWeight=50 MemoryHigh=640M MemoryMax=1G MemorySwapMax=256M
sudo systemctl set-property channel.service CPUWeight=200 IOWeight=200
sudo systemctl set-property xhs-web.service CPUWeight=200 IOWeight=200
```

无需重启服务。Agent 并发通过 `PUT /api/agents/{id}` 的 `max_concurrent_tasks` 字段单独设置，原始值保存在 `.local/resource-optimization-report.json`。

## 检查和回滚

检查 `systemctl show multica-agent-runtime.service` 的 `CPUQuotaPerSecUSec`、`MemoryHigh`、`MemoryMax`、`MemorySwapMax`，以及 cgroup 的 `memory.events`、`cpu.stat` 和 `/proc/pressure/{cpu,memory,io}`。本次部署前后指标与健康检查保存在 `.local/resource-optimization-report.json`。不要通过停止 Swap 或清空页缓存验证效果。

回滚本次设置时，删除 `/etc/systemd/system/multica-agent-runtime.service.d/30-resources.conf`，执行 `systemctl daemon-reload`，再使用 `systemctl set-property --runtime` 将执行服务的 `CPUQuota`、`MemoryHigh`、`MemoryMax`、`MemorySwapMax` 恢复为 `infinity`，CPU/IO 权重恢复为 100。Channel 与 XHS 的 CPU/IO 权重也用 `systemctl set-property` 恢复为 100。Agent 并发按报告中的原值恢复；不改变它们的模型、指令、Skill 或路由。

## 后续部署

本机承担入口、Multica 调度和数据库、Channel、各平台连接及 Session 存储。长期将代聊与通用工具执行迁到独立 worker，通过 Multica runtime 绑定接入；只需要本机接口的操作 Agent 可继续以低并发留在本机。迁移前必须验证新节点的认证、Skill、附件处理和队列恢复，现有平台登录凭据继续留在连接器侧。

需要浏览器、编译或多任务执行时，根据实际峰值为独立 worker 配置内存，不照搬这份小机器预算。没有就绪的远端 runtime 时保持现有绑定，不能直接停掉唯一可用的执行服务。
