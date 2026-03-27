# Personal Website

个人网站与知识库发布系统，核心技术栈

Flask + SQLite + Docker Compose + Nginx (ModSecurity) + GitHub Actions + GCP + Cloudflare

文章内容来自独立的知识库仓库 [hanjie-chen/knowledge-base](https://github.com/hanjie-chen/knowledge-base)，通过定时同步、增量导入与静态渲染自动发布到站点。

## Overview

这个仓库主要负责三件事：

- 提供首页、`/articles`、文章详情页与 `About Me` 页面
- 把 Markdown 知识库同步、导入并渲染成可访问的 HTML
- 通过 CI/CD 将镜像部署到 GCP VM，并由 Cloudflare 暴露到公网

## Architecture

network traffic

- 线上流量：`Client -> Cloudflare -> GCP VM -> Nginx(ModSecurity) -> Flask`
- 内容更新：`articles-sync(cron) -> POST /internal/reindex -> import/render pipeline`
- 持久化（Docker volumes）：
  - `source_md_articles`：Markdown 源文与图片
  - `rendered_html_articles`：渲染后的 HTML 与拷贝后的静态资源
  - `webapp_instance`：SQLite 数据文件

项目运行时的职责分工：

- web-app

  Flask 应用本体，负责页面路由、文章导入、Markdown 渲染、TOC 与 docs-style navigation

- articles-sync

  维护知识库仓库的本地 shallow mirror，并在检测到新内容后触发 reindex

- nginx-modsecurity

  负责 HTTPS、反向代理、WAF 与 `/web-log/` 的受保护访问

- dozzle

  容器日志 UI，通过 Nginx 以 `/web-log/` 暴露并附加 Basic Auth

## Repository Layout

```text
.
├── articles-sync/       # 知识库同步容器与定时同步脚本
├── compose.dev.yml      # 开发环境 compose 覆盖
├── compose.yml          # 基础 compose / 生产运行配置
├── infra/               # Terraform / Ansible / infra workflows
├── nginx-modsecurity/   # Nginx、ModSecurity、证书与 Basic Auth 相关配置
├── scripts/deploy/      # 生产部署、健康检查、镜像清理脚本
└── web-app/             # Flask 应用、模板、静态资源、测试
```

## Subsystem Guides

更细的说明已经拆到子目录 README 中，根 README 只保留入口信息：

- [web-app/README.md](./web-app/README.md)

  Flask 路由、Markdown 渲染链路、模板与静态资源地图、测试入口

- [articles-sync/README.md](./articles-sync/README.md)

  knowledge-base shallow mirror 策略、定时同步、reindex 触发机制

- [scripts/deploy/README.md](./scripts/deploy/README.md)

  生产部署脚本说明、执行顺序、健康检查与旧镜像清理

- [infra/terraform/gcp/README.md](./infra/terraform/gcp/README.md)

  GCP 基础设施资源、Terraform 使用方式与 weekly infra sync

## Run Modes

- 生产：`compose.yml`
- 开发：`compose.yml + compose.dev.yml`

```bash
# production
docker compose -f compose.yml up -d

# development
docker compose -f compose.yml -f compose.dev.yml up -d --remove-orphans
```

## Common Commands

### Start Development Stack

```bash
docker compose -f compose.yml -f compose.dev.yml up -d --remove-orphans
```

### Run Tests

```bash
docker compose -f compose.yml -f compose.dev.yml run --rm -T web-app pytest -q
```

### Check Compose Config

```bash
docker compose -f compose.yml -f compose.dev.yml config
```

### Initialize Production App

```bash
./scripts/deploy/prod_init.sh
```

### Deploy a Specific Image Tag

```bash
./scripts/deploy/prod_deploy.sh <deploy_sha>
```

说明：

- 更完整的 deploy flow、health checks、cleanup 策略请看 [scripts/deploy/README.md](./scripts/deploy/README.md)
- 更细的测试文件说明请看 [web-app/README.md](./web-app/README.md)

## Infrastructure

应用部署依赖的基础设施由 `infra/` 管理，当前重点是 GCP VM、Cloudflare 到 origin 的 HTTPS firewall，以及 uptime check。

常见 Terraform 命令：

```bash
cd infra/terraform/gcp
terraform init
terraform plan
```

Host bootstrap 由 `infra/ansible/` 负责，主要用于现有 VM 的基础环境配置，例如 Docker Engine 安装。

详细说明见：[infra/terraform/gcp/README.md](./infra/terraform/gcp/README.md)

## CI/CD

### CI

文件位置：`.github/workflows/ci.yml`

主要职责：

- 校验 Compose 配置
- 运行 `ruff format --check .`
- 运行 `pytest`
- 在 `main` 分支 push 时构建并推送 GHCR 镜像

### CD

文件位置：`.github/workflows/cd.yml`

主要职责：

- 在 CI 成功后 SSH 到目标主机
- 按 `workflow_run.head_sha` 拉取并部署对应镜像
- 执行数据库检查、服务健康检查与 smoke check
- 清理当前项目不再需要的历史镜像，减少 GCP VM 磁盘占用

说明：

- CI 负责构建镜像
- CD 负责在 GCP VM 上按 SHA 部署镜像
- 部署细节请看 [scripts/deploy/README.md](./scripts/deploy/README.md)

## Security Notes

- 内部重建接口：`POST /internal/reindex`
- 鉴权头：`X-REIMPORT-ARTICLES-TOKEN`
- `nginx-modsecurity` 默认开启 WAF
- `/web-log/` 使用 Nginx Basic Auth 保护 Dozzle 日志面板

## Roadmap

1. sqlite database 可视化，方便 debug
2. trivy 的 ci 扫描
3. 从 full-stack 的角度来看还欠缺什么
4. uv project best practice migrate
5. light mode
6. support rss

