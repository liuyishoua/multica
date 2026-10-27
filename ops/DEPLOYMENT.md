# Multica 部署说明

- 目录：`/home/ubuntu/leo-project/multica`
- 公网入口：<https://d.58nft.net:9447/>（默认自动登录）
- 版本：官方 Docker 镜像 `v0.6.1`，不自动升级。
- 管理邮箱：`fyhvyhj@gmail.com`，Leo 工作区所有者。
- 当前由 ops-hub 统一账号先校验应用权限，原始管理员默认可用，普通用户申请获批后才进入共享默认账号。获权成员在 Leo 工作区共享该账号的数据和权限。公开注册仍关闭。
- PostgreSQL、后端、前端由 Docker Compose 运行；数据库与上传附件使用独立持久卷。
- 后端及前端仅监听本机 8080、3000；公网通过 Caddy HTTPS 9447 访问。
- 系统重启后自动启动，容器退出自动恢复，每分钟检查应用可用性；连续三次失败后重启应用容器。
- 每天北京时间 04:15 左右备份，保留约 14 天，路径 `/var/backups/multica`，仅 root 可读。备份包括数据库、上传附件和部署密钥。备份目前在本机，不能覆盖整机磁盘丢失。
- 证书由原有 Caddy 服务续期，证书变动触发 Multica 代理重新加载。

## 默认自动登录

按用户要求，网站 `/`、`/login`、`/signup`、`/register` 通过本机自动登录服务签发现有所有者账号的会话，然后跳转 `/leo/issues`。`/leo/*` 页面通过入口的 `forward_auth` 检查会话；已登录请求继续进入前端，缺失或失效的 Cookie 则重新签发共享账号会话，保留原路径和查询参数，避免新机器直接打开工作区或旧会话失效时因 `/api/me` 返回 401 而白屏。仅通过统一应用授权的网页访问者共享该账号，包括其智能体操作权限。所有网页和 API 路径均先校验统一会话及应用权限，已有 Multica Cookie 不能绕过。原机器 API 的有效 Bearer 凭据独立认证，该路由移除 Cookie 后由后端验证；健康接口保留公开只读检查。没有配置 QQ SMTP，也不需要邮件授权码。

- 服务：`multica-default-login.service`，仅监听 `127.0.0.1:8091`，开机自启、退出自动恢复。
- 实现：`ops/default_login.py`，读取 `.env` 中的 JWT 密钥，兼容固定版本官方会话及 CSRF Cookie；每次签发前检查后端用户身份。
- 回归：`python3 -m unittest discover -s ops -p test_default_login.py -v`；浏览器另验全新会话直接打开 `/leo/issues`、无效 Cookie 的自动恢复和已有会话刷新。首页 `/` 可用不能替代深层链接验证。
- 代理配置：`ops/multica.caddy`，安装到 `/etc/caddy/multica.caddy`。
- 入口启用 zstd/gzip 传输压缩，降低首次加载脚本的下载量；修改后先执行 `caddy validate --config ops/multica.caddy --adapter caddyfile`，再安装配置并重启入口代理。验证浏览器工作区实际显示及脚本响应，不能只检查首页 HTTP 状态。
- 官方后端及数据库未修改；原有账户、任务和运行时保留。后端 API 仍校验会话和 CSRF。
- `.env` 含部署密钥，请保留其 0600 权限，不要提交到 Git。

恢复邮箱验证码登录：删除 `ops/multica.caddy` 中的 `@default_login` 及对应 `handle` 块，安装到 `/etc/caddy/multica.caddy`；从代理 unit 的 `After` 和 `Wants` 删除 `multica-default-login.service` 并重新安装 unit。执行 `sudo systemctl daemon-reload`、`sudo systemctl disable --now multica-default-login.service` 和 `sudo systemctl restart multica-proxy.service`。已有会话仍会保持到退出或过期。

恢复后如需真实邮件验证码，配置官方支持的 `SMTP_*` 或 `RESEND_API_KEY`，再重新创建后端容器。目前未配置邮件发送服务。

## 日常维护

本机执行服务采用 CPU、内存及并发预算，安装、验证、回滚和远端执行节点建议见 [RESOURCE_BUDGET.md](RESOURCE_BUDGET.md)。

```bash
sudo systemctl status multica multica-proxy multica-default-login
sudo docker compose -f /home/ubuntu/leo-project/multica/docker-compose.selfhost.yml ps
curl -fsS https://d.58nft.net:9447/readyz
sudo journalctl -u multica-watchdog -u multica-backup --since today
sudo systemctl start multica-backup.service
sudo systemctl restart multica.service
sudo systemctl restart multica-proxy.service
```

如需主动停服，同时停用 watchdog，防止自动恢复：

```bash
sudo systemctl stop multica-watchdog.timer multica.service multica-proxy.service
```

重新启动：

```bash
sudo systemctl start multica.service multica-proxy.service multica-watchdog.timer
```

## 恢复备份

先停止应用与 watchdog，保留 PostgreSQL 容器运行。将指定备份中的数据库恢复到独立的新数据库或经明确确认可覆盖的空数据库；数据库使用 PostgreSQL 自定义格式（`pg_restore`），附件为 `uploads.tar.gz`。恢复时同时使用该备份的 `deployment.env`，保留 JWT 密钥。不要使用 `docker compose down -v`，该命令会删除持久数据。

## AI Agent 执行

已接入当前服务器上的 Codex CLI，复用 ubuntu 用户现有的 ChatGPT 登录。Multica CLI 固定为与网站一致的 `0.6.1`，关闭自动升级。

- 运行时：`Codex (Leo 本机服务器)`，ID `ed2437c9-fa66-4d96-8f0b-15069f1cd9f5`。
- 智能体：`智能回复助手`，ID `82ce74c8-e570-4f8f-9b07-dc3fa59e567c`。
- 模型：`gpt-6.1-sol`，思考强度 `medium`，智能体与守护进程并发上限均为 2。
- Access：仅创建者可运行。指令默认进行中文问答和回复起草，实际发送外部消息或修改资源需要用户明确要求；此为行为指令，不是操作系统权限隔离。
- CLI 配置及 PAT：`/home/ubuntu/.multica/config.json`，0600 权限；PAT 初始有效期 90 天，守护进程按官方机制自动续期。不将 PAT 或 Codex 登录凭据写入仓库。
- 后台服务：`multica-agent-runtime.service`，以 ubuntu 用户运行，开机启动、退出自动重启。
- 运行时自动检测到了本机 Hermes 与 Qwen CLI；本智能体只绑定 Codex。
- 2026-10-09 已通过平台真实聊天验证：约 7 秒生成中文会议邀约回复，执行成功。

直接聊天：<https://d.58nft.net:9447/leo/chat?agent=82ce74c8-e570-4f8f-9b07-dc3fa59e567c>。
验证记录：<https://d.58nft.net:9447/leo/chat?session=01a120a5-4156-7c1c-8ccc-bf2b4c958713>。

```bash
sudo systemctl status multica-agent-runtime
sudo systemctl restart multica-agent-runtime
sudo systemctl stop multica-agent-runtime
sudo journalctl -u multica-agent-runtime --since today
multica daemon status
multica runtime list
multica agent list
```

服务由 systemd 管理，日常重启使用 `systemctl restart`，避免另行运行 `multica daemon start/restart` 导致重复启动。Codex 登录失效时，以 ubuntu 用户重新完成 `codex login`，再重启该服务。Multica PAT 失效时，以 ubuntu 用户运行 `multica login`（保留自托管地址），再重启该服务。

官方参考：<https://github.com/multica-ai/multica/blob/main/SELF_HOSTING.md>。

## 小红书 Leo 私信回复执行

生产身份为 `小红书-leo`（`da72f33e-cac4-4ff0-a99d-d415219f3efc`），当前绑定 `Codex (Leo 本机服务器)`（`ed2437c9-fa66-4d96-8f0b-15069f1cd9f5`），显式使用 `gpt-6.1-sol`、`low`。工作台仍通过 Channel 接收结构化结果并执行小红书发送；家庭网络出口和账号发送控制由工作台维护，模型执行节点与平台出口分别配置。

工作台独立快照回复任务用 `social-content-kit/scripts/reply_input.py` 一次读取完整 issue、绑定档案及对话/平台技能，直接返回最终 JSON。部署指令入口为 `agent-tools/social-content-kit/scripts/optimize_reply_agents.py`；它不更新模型和 runtime。原 Mac runtime 的 `using-superpowers` 仅对该身份禁用，其他账号和客户端技能保持各自配置。

隔离性能测试：在 `xhs/` 下运行 `PYTHONPATH=. .venv/bin/python -m deploy.smoke_reply_latency`。该命令调用真实模型，须明确授权后执行；使用合成收件人和独立工作台数据库，没有平台发送器。报告在 `xhs/.local/synthetic-reply-latency-*/report.json`，记录 issue/run ID。两次本机普通文字测试均约 18.3 秒返回可用回复，不能作为图片、多轮复杂判断、并发负载或平台送达的时延保证。

诊断依据和对照汇总保存于 `.local/reply-latency-report.json`。模型/思考配置及 runtime 变更前的字段备份分别为 `.local/reply-execution-settings-backup.json`、`.local/leo-runtime-comparison-backup.json`。回滚时通过 agent API 恢复备份字段；不要用恢复数据库或重启所有 runtime 的方式回滚单个 agent 的设置。

## 项目操作智能体

- 智能体：`Leo 项目操作助手`，ID `fc8e609f-8374-4526-b58f-642e5dfc2914`，仅创建者可运行，单智能体并发 1。
- 复用本机 Codex，模型 `gpt-6.1-sol`，思考强度 medium。
- 已绑定平台 Skill `leo-project-ops`，ID `bf9b5f1c-8c4d-45eb-918a-e7e9f9f96044`；接口工具与源说明在 `/home/ubuntu/leo-project/agent-tools/leo-project-ops/`。
- 当前提供抖音演示 API、票务 API、模型 WebUI API、Multica CLI/API、闲鱼 Python SDK/脚本以及 Bifrost 链接文件入口。门户账号表单暂未自动接入；闲鱼未核实 Web 服务。以现有能力落实创意，不补建缺失系统。
- 工具处理本机 HTTP 鉴权、来源校验和输出凭据脱敏，非 GET 需 `--execute`，写请求不自动重试。此助手使用 ubuntu 用户现有系统权限；Skill 中的行为要求不等同于系统隔离。

聊天入口：<https://d.58nft.net:9447/leo/chat?agent=fc8e609f-8374-4526-b58f-642e5dfc2914>。

2026-10-09 平台执行验证：助手读取各项目状态、票务账号/任务列表与模型列表；在抖音 demo 环境创建临时标签、查询核对并删除。验证会话 01a120ac-c2ec-75e6-9c3e-d7e96c739500。

## 首屏静态资源缓存

`multica.caddy` 对 `/srv/multica-assets` 中已存在的 `/_next/static/` 资源提供本地文件服务，优先使用 Brotli/gzip 预压缩文件，保留一年 immutable 缓存。仅缓存框架生成的公开静态资源；页面、API、会话检查和 WebSocket 保持原来的代理与认证规则。缓存缺失时回源 Next 服务。

升级前端后运行 `sudo python3 ops/cache-static-assets.py` 预热当前入口资源。脚本通过现有默认登录读取资源引用，仅在内存保存会话，不输出或缓存页面、Cookie、任务内容。旧文件无需立即删除，以支持已打开的旧页面。配置变更经 `sudo caddy validate --config ops/multica.caddy --adapter caddyfile` 后安装到 `/etc/caddy/multica.caddy`，仅重启 `multica-proxy.service`，无需重启 agent runtime。
