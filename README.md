# multica

[![Local changes: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/Local%20changes-PolyForm%20Noncommercial%201.0.0-orange)](LICENSE-LOCAL)

基于 [multica-ai/multica](https://github.com/multica-ai/multica) 的本地部署副本，
用于人与 AI agent 协作管理任务，包含独立运行环境、账号入口、备份、监控和资源预算配置。
Multica 原应用、名称、品牌及原版权声明均保留；本仓库没有重新授权上游代码。

## 本机开发

```bash
git clone https://github.com/liuyishoua/multica.git
cd multica
make up
make status
```

按 [贡献与开发说明](CONTRIBUTING.md) 安装 Docker、Go、Node.js 和 pnpm 等依赖，
通过项目管理的环境和独立工作区数据库开发。`make down` 保留数据。

## 正式部署

本地生产配置保存在 `ops/`，安装步骤见 [ops/DEPLOYMENT.md](ops/DEPLOYMENT.md)。
自行生成部署密钥和机器凭据，不复制现有服务器的 `.local/`。
服务使用 PostgreSQL 与 Docker，智能体由独立 runtime 连接。
自托管、托管服务和分发范围以完整上游 [Multica License](LICENSE) 为准。

## 数据与备份

- `.local/`、`.env*`：账号凭据、部署状态和私有配置，忽略 Git。
- PostgreSQL、上传附件与部署密钥需要配套备份，具体步骤见 `ops/DEPLOYMENT.md`。
- `ops/RESOURCE_BUDGET.md` 是单台小机器的参考配置，部署时按实际资源调整。

## 验证

```bash
pnpm typecheck
pnpm lint
pnpm test
make test
```

只改文档时检查链接和 `git diff --check`，不把文档检查称为应用完整回归。

## 目录

- `server/`：Go 服务；`apps/`：网页、桌面、手机端和文档。
- `packages/`：共享代码；`ops/`：本地部署与维护脚本。
- [原项目 README](docs/upstream-readme.md) 保留上游功能、安装与来源说明。

## 使用许可

**本仓库自有部署和集成代码仅供学习、研究、测试及其他非商业用途，不得用于商业目的。**
版权所有者拥有权利的本地新增内容使用 [PolyForm Noncommercial License 1.0.0](LICENSE-LOCAL)。
Multica 原代码继续使用完整的 [Multica License](LICENSE)，不能用本地许可替代其条款。
原许可证、NOTICE、品牌及版权归属完整保留；详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
