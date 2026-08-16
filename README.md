# Personal Dashboard

`hanjie-chen.com` 是一个从个人博客持续演进的公开个人信息中枢，用来聚合 Daily Brief、技术知识库、个人项目与介绍。核心技术栈：

Flask + SQLite + Docker Compose + Nginx (ModSecurity) + GitHub Actions + GCP + Cloudflare

文章内容来自独立的知识库仓库 [hanjie-chen/knowledge-base](https://github.com/hanjie-chen/knowledge-base)，通过 push-driven 内容同步、增量导入与静态渲染自动发布到站点，并保留低频定时同步作为兜底。Daily Brief 由独立生成器每天产出，通过认证发布接口更新当前简报与网页历史归档；已成功发布的 payload 暂不设置保留期限，方便直接在网页上复盘和排错。

## Product Direction

这个项目正在从单一的个人博客演进为公开的 Personal Dashboard。当前阶段先用真实模块推动信息架构变化：Daily Brief 是博客之外的第一个模块，首页开始承担每日信息、知识库和个人入口的聚合作用；完整 dashboard UI 会根据实际使用反馈继续迭代，而不是预先为尚不存在的功能设计。

## Overview

这个仓库主要负责以下能力：

- 提供带语言前缀的公开页面：`/zh/...`、`/en/...`，根路径 `/` 会按语言偏好自动跳转
- 提供 Daily Brief 首页入口、历史归档与按日期阅读页；按日期阅读页从已有 `source_url` 显示原文域名，并为 allowlist 中的站点显示官方来源名，简报正文当前仅提供中文
- 提供公开只读的文章 metadata API：`GET /api/articles` 与 `GET /api/articles/<id>`
- 把 Markdown 知识库同步、导入并渲染成可访问的 HTML
- 通过 CI/CD 将镜像部署到 GCP VM，并由 Cloudflare 暴露到公网

## Architecture

network traffic

- 线上流量：`Client -> Cloudflare -> GCP VM -> Nginx(ModSecurity) -> Flask`
- 内容更新：`knowledge-base push -> website content-sync workflow -> articles-sync/update-articles.sh -> POST /internal/reindex -> import/render pipeline`
- 简报发布：`daily-brief cron -> structured JSON -> POST /internal/briefs -> validated JSON volume -> Flask pages`
- 兜底同步：`articles-sync(daily cron) -> update-articles.sh`
- 持久化（Docker volumes）：
  - `source_md_articles`：Markdown 源文与图片
  - `rendered_html_articles`：渲染后的 HTML 与拷贝后的静态资源
  - `webapp_instance`：SQLite 数据文件
  - `daily_brief_data`：当前 Daily Brief 指针、网页归档索引与全部严格校验的按日期 payload

项目运行时的职责分工：

- web-app

  Flask 应用本体，负责页面路由、Daily Brief 校验、当前指针与历史归档存储、文章导入、Markdown 渲染、TOC 与 docs-style navigation

- articles-sync

  维护知识库仓库的本地 shallow mirror，并在检测到新内容后触发 reindex

- nginx-modsecurity

  负责 HTTPS、反向代理、WAF 与 `/web-log/` 的受保护访问

- dozzle

  容器日志 UI，通过 Nginx 以 `/web-log/` 暴露，并由 Cloudflare Access 保护

## Repository Layout

```text
.
├── articles-sync/       # 知识库同步容器与定时同步脚本
├── compose.dev.yml      # 开发环境 compose 覆盖
├── compose.yml          # 基础 compose / 生产运行配置
├── infra/               # Terraform / Ansible / infra workflows
├── nginx-modsecurity/   # Nginx、ModSecurity、证书与 /web-log 访问控制相关配置
├── scripts/deploy/      # 生产部署、健康检查、镜像清理脚本
├── scripts/security/    # 容器安全扫描策略与自动修复辅助工具
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

- [nginx-modsecurity/README.md](./nginx-modsecurity/README.md)

  HTTPS、反向代理、WAF、Dozzle 访问控制与 Nginx 配置意图说明

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
- 公开 HTML 页面目前使用 `preferred_language` cookie、浏览器 `Accept-Language` 和默认语言 `zh` 决定 `/` 的跳转落点

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
- 运行 Ruff lint 与 `ruff format --check .`
- 运行 `pytest`
- 对固定的 Nginx/ModSecurity 与 Dozzle 镜像执行 Trivy 扫描
- 实际启动候选第三方镜像并执行 Nginx config、health 与 smoke checks
- 在 `main` 分支 push 时构建并推送 GHCR 镜像

### CD

文件位置：`.github/workflows/cd.yml`

主要职责：

- 在 CI 成功后 SSH 到目标主机
- 按 `workflow_run.head_sha` 拉取并部署对应镜像
- 显式拉取 Compose 中固定 tag + digest 的第三方镜像
- 执行数据库检查、服务健康检查与 smoke check
- 校验生产容器实际 image reference 与 Git 声明一致
- Nginx/Dozzle 更新失败时恢复上一组运行镜像
- 清理当前项目不再需要的历史镜像，减少 GCP VM 磁盘占用

说明：

- CI 负责构建镜像
- CD 负责在 GCP VM 上按 SHA 部署镜像
- 部署细节请看 [scripts/deploy/README.md](./scripts/deploy/README.md)

## Security Notes

- 公开只读 API：
  - `GET /api/articles`
  - `GET /api/articles/<id>`
- 内部重建接口：`POST /internal/reindex`
- 鉴权头：`X-REIMPORT-ARTICLES-TOKEN`
- Daily Brief 发布接口：`POST /internal/briefs`，使用独立的 `X-DAILY-BRIEF-TOKEN`；未配置 token 时接口返回 404
- Daily Brief payload 限制为 128 KiB，写入前会严格校验 schema v2、条目数量、URL 与 HN item ID 一致性；schema v1 不兼容
- `/internal/briefs` 使用 Nginx exact-match location 关闭通用 WAF 检查，避免把只作为文本存储的技术内容误判为 SQLi/XSS；该例外不影响其他路由，并由 128 KiB edge limit、独立 token、严格 schema 校验与 Jinja escaping 构成补偿控制
- ModSecurity audit log 以不含完整 request header/body 的 `AHZ` 记录进入容器日志，既能定位原始 rule ID，也避免发布 token 被整体写入 audit record；具体 rule message 仍可能包含必要的命中片段
- `nginx-modsecurity` 默认开启 WAF
- Nginx/ModSecurity 与 Dozzle 使用 stable tag + immutable digest；Dependabot 每日检查 Docker Compose 镜像更新并通过 PR 提交变化
- `.github/workflows/container-security.yml` 每日重扫固定镜像；存在未豁免且已有修复的 HIGH/CRITICAL finding 时，会按镜像版本策略扫描较新的候选 tag，只有候选通过相同安全策略才以 immutable digest 创建或更新安全升级 PR，并继续维护 GitHub security issue 直到修复合并
- `scripts/security/trivyignore.yaml` 只接受带原因与到期日的临时风险例外，到期后扫描会重新阻断
- 生产环境的 origin TLS 由 Nginx 挂载 Cloudflare Origin CA 证书；开发环境可使用自签名证书
- Cloudflare 目前已对 `/static/*` 启用 edge cache；`/rendered-articles/*.html` 暂未纳入缓存计划
- `/web-log/` 目前由 Cloudflare Access 在 edge 侧保护，不再依赖 Nginx Basic Auth
- 公开只读 API `/api/articles*` 目前已添加 Cloudflare rate limiting 保护
- 当前已落地的 Cloudflare 优化主要包括：`/static/*` edge cache、`/web-log/` Cloudflare Access、`/api/articles*` rate limiting，以及生产环境 Origin CA + `Full (strict)`

## Roadmap

1. 根据 Daily Brief 的真实使用反馈继续演进 dashboard 首页与统一 UI
2. sqlite database 可视化，方便 debug
3. uv project best practice migrate
4. light mode
5. support website rss 订阅
6. 如果后续增加联系表单、留言或其他写入型交互，再接入 Cloudflare Turnstile
7. seo 优化
