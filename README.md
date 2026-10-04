# Personal Dashboard

[hanjie-chen.com](https://hanjie-chen.com) 是一个公开的个人网站和个人信息中枢，聚合技术知识库、Daily Brief、个人项目与介绍。

文章来自独立的 [knowledge-base](https://github.com/hanjie-chen/knowledge-base) 仓库，由本站提供中英文阅读页面。

每日简报由 [Daily Brief](https://github.com/hanjie-chen/daily-brief) 项目生成，通过本站页面与公开只读 JSON API 提供。
本站按 `Asia/Singapore` 日期滚动保留今天及此前 13 天的简报，过期内容停止提供并自动清理。

核心技术栈：Flask + SQLite + Docker Compose + Nginx (ModSecurity) + GitHub Actions + GCP + Cloudflare

## Architecture

- 站点访问：`Client → Cloudflare → GCP VM 上的 Nginx → Flask`；部分静态资源由 Nginx 直接提供。
- 文章更新：`knowledge-base push → content-sync workflow → articles-sync → web-app 导入与渲染`；每日定时同步作为兜底。
- 简报发布：`独立 Daily Brief 生成器 → 认证发布接口 → JSON 存储 → 页面与公开 API`。

## Repository Layout

| Path | Purpose | Documentation |
| --- | --- | --- |
| `web-app/` | Flask 应用、模板、静态资源与测试 | [README](./web-app/README.md) |
| `articles-sync/` | 知识库同步与文章重建触发 | [README](./articles-sync/README.md) |
| `nginx-modsecurity/` | HTTPS、反向代理、WAF 与日志面板入口 | [README](./nginx-modsecurity/README.md) |
| `scripts/deploy/` | 生产初始化、部署与健康检查 | [README](./scripts/deploy/README.md) |
| `scripts/security/` | 容器安全扫描与自动修复工具 | [README](./scripts/security/README.md) |
| `.github/workflows/` | CI/CD、内容同步与基础设施、安全自动化 | [README](./.github/workflows/README.md) |
| `infra/` | Terraform 与 Ansible 配置 | [GCP Terraform](./infra/terraform/gcp/README.md) |
| `compose.yml`、`compose.dev.yml` | 生产运行配置与本地开发覆盖配置 | — |

## Development & Deployment

项目通过 Docker Compose 运行。生产使用 `compose.yml`；本地开发叠加 `compose.dev.yml`，配置本地构建、源码挂载与 Flask 调试模式。

- 应用构建、测试与代码检查：见 [web-app/README.md](./web-app/README.md#running-and-testing)。
- 生产初始化、版本部署与健康检查：见 [scripts/deploy/README.md](./scripts/deploy/README.md)。

## Infrastructure

基础设施配置位于 `infra/`

- Terraform 管理 GCP VM、允许 Cloudflare 访问 origin 的 HTTPS firewall rule，以及 uptime check。
- Ansible 负责 host bootstrap，例如安装 Docker Engine。

Terraform 的配置范围、authentication 与操作步骤见 [infra/terraform/gcp/README.md](./infra/terraform/gcp/README.md)。

## CI/CD

项目使用 GitHub Actions 执行检查、发布镜像并部署到 GCP VM：

- **CI**：面向 `main` 的 pull request、`main` push 和手动触发会运行配置校验、代码检查、测试、容器安全检查与 runtime smoke checks。
- **Image publishing**：`main` push 通过必要检查后，将应用镜像发布到 GHCR，并以 commit SHA 标记。
- **CD**：仅在 `main` push 对应的 CI 成功后自动部署，使用该 CI run 的 commit SHA 选择镜像，并执行部署验证；pull request 和手动 CI 不会触发部署。

Workflow 职责、触发条件与维护说明见 [.github/workflows/README.md](./.github/workflows/README.md)；部署流程与回滚范围见 [scripts/deploy/README.md](./scripts/deploy/README.md)。

## Security

公开 Daily Brief API 提供只读访问；内容发布与文章重建接口使用独立 token 鉴权，日志面板由 Cloudflare Access 保护。

接口说明见 [web-app/README.md](./web-app/README.md)，TLS、WAF 与日志面板访问控制见 [nginx-modsecurity/README.md](./nginx-modsecurity/README.md)。

容器扫描、自动修复与漏洞例外见 [scripts/security/README.md](./scripts/security/README.md)。

## TODO

1. website ui refactor
    - daily brief page ui improve
    - dark/light mode switch

2. 盘点 Cloudflare 配置并集中记录，评估将适合的配置纳入 Terraform 管理。
