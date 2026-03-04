# Personal Website

个人网站与博客平台，核心技术栈为 `Flask + SQLite + Docker Compose + Nginx(ModSecurity) + GitHub Actions`。

文章内容来自我的笔记 github repo: [hanjie-chen/knowledge-base](https://github.com/hanjie-chen/knowledge-base)，通过定时同步与增量导入自动发布。

## Overview

Repository Layout

```shell
.
├── articles-sync/                # 同步容器脚本与 Dockerfile
├── nginx-modsecurity/            # Nginx/WAF 配置、证书、Basic Auth
├── web-app/                      # Flask 应用
├── compose.yml                   # 生产配置
├── scripts/deploy                # CD用脚本
├── compose.dev.yml               # 开发覆盖配置
└── .github/workflows/            # CI/CD
```

- web-app: Flask 应用，负责页面路由、文章展示、内部重建接口。
- nginx-modsecurity: 反向代理 + WAF，处理 HTTPS 和静态资源。
- dozzle: 容器日志 UI（通过 `/web-log/` 暴露并做 Basic Auth）。

### articles-sync/

定时 `git pull` 文章仓库，发现更新后调用内部 reindex 接口。

```shell
.
├── Dockerfile              # 构建 image
├── cron-heartbeat-sync.sh  # 定时 task 执行 update-articles.sh
├── init.sh                 # 初始化脚本
└── update-articles.sh      # 定时更新脚本
```

`init.sh` 先执行 git clone/git pull，成功之后才会启动 crond

### scripts/deploy/

cd 流程中使用的脚本

```shell
.
├── ensure_db_ready.sh
├── prod_deploy.sh
├── prod_init.sh
├── service_wait.sh
├── smoke_check.sh
└── wait_services_healthy.sh
```

`prod_init.sh`: 首次部署初始化：等待 `articles-sync` healthy 后再初始化 DB，最后启动全部服务并执行 smoke check

`prod_deploy.sh <sha>`: 按指定镜像 tag（通常是 commit SHA）部署生产服务

`ensure_db_ready.sh <sha>`: 检查 `article_meta_data` 表是否存在；缺失时自动执行 `init_db.py` 修复

`wait_services_healthy.sh [services...]`:等待指定服务进入 `healthy`（默认 `web-app` 与 `nginx-modsecurity`）

`smoke_check.sh`: 线上链路检查：`/` 与 `/articles`

## Architecture

- 线上流量：`Client -> Cloudflare -> Nginx(ModSecurity) -> Flask`
- 内容更新：`articles-sync (cron) -> git pull -> POST /internal/reindex`
- 持久化（docker volume）：
  - `source_md_articles`：Markdown 源文
  - `rendered_html_articles`：渲染后的 HTML/图片
  - `webapp_instance`：SQLite 数据文件（`/app/instance`）

## Run Modes

- 生产：`compose.yml`
- 开发：`compose.yml + compose.dev.yml`

```bash
# production
docker compose -f compose.yml up -d

# development
docker compose -f compose.yml -f compose.dev.yml up -d --remove-orphans
```

## Production deploy

首次部署或重建环境时，按顺序执行：

1. 配置 `.env`

```env
REIMPORT_ARTICLES_TOKEN=xxxx
```

2. 准备 HTTPS 证书与密码文件

- 证书路径：`nginx-modsecurity/ssl/`

- Basic Auth 文件：`nginx-modsecurity/.htpasswd`

  ```
  docker run --rm httpd:2.4-alpine htpasswd -nbB <username> <password>
  ```

3. 运行初始化脚本（封装后续步骤）

```bash
./scripts/deploy/prod_init.sh
```

- 首次拉取文章等待超时可通过 `ARTICLES_SYNC_READY_TIMEOUT` 覆盖（`prod_init.sh` 默认 600 秒）。

## Tests

测试框架使用 `pytest`，目录在 `web-app/tests/`。

### Run Tests

```bash
docker compose -f compose.yml -f compose.dev.yml run --rm -T web-app pytest -q
```

### Current Coverage

- `web-app/tests/test_smoke.py`
  - `GET /` 冒烟测试（服务可达）
- `web-app/tests/test_articles_routes.py`
  - `/articles` 返回 200
  - `/articles/<id>` 的 404/200 场景
- `web-app/tests/test_internal_reindex.py`
  - `/internal/reindex` token 鉴权（404/403/200）
- `web-app/tests/conftest.py`
  - 统一 fixture（`app`、`client`）与测试数据清理

## CI/CD

### CI

location: `.github/workflows/ci.yml`

- 触发：
  - `push` 到任意分支
  - `pull_request` 到 `main`
- 执行内容：
  - 校验 `compose.yml` 与 `compose.dev.yml`
  - 构建并推送镜像到 GHCR（仅 push 事件）
    - `ghcr.io/<owner>/website-web-app:<sha|latest>`
    - `ghcr.io/<owner>/website-articles-sync:<sha|latest>`

### CD

location: `.github/workflows/cd.yml`

- 触发：`CI` 在 `main` 成功结束后
- 执行内容：
  - SSH 到目标主机
  - `git pull` 更新代码
  - 使用 `workflow_run.head_sha` 作为部署镜像 tag（不可变版本）
  - `./scripts/deploy/prod_deploy.sh <sha>`
  - `./scripts/deploy/ensure_db_ready.sh <sha>`
  - `./scripts/deploy/wait_services_healthy.sh web-app nginx-modsecurity`
  - `./scripts/deploy/smoke_check.sh`

### Rollback

在 GCP VM 上执行（回滚到 `main` 的上一个提交）：

```bash
ROLLBACK_SHA=$(git rev-parse HEAD~1)

WEB_APP_IMAGE_TAG="$ROLLBACK_SHA" ARTICLES_SYNC_IMAGE_TAG="$ROLLBACK_SHA" docker compose pull web-app articles-sync
WEB_APP_IMAGE_TAG="$ROLLBACK_SHA" ARTICLES_SYNC_IMAGE_TAG="$ROLLBACK_SHA" docker compose up -d web-app articles-sync
```

查看当前容器实际运行的镜像 tag：

```bash
docker inspect web-app --format '{{.Config.Image}}'
docker inspect articles-sync --format '{{.Config.Image}}'
```

说明：

- `SHA` 是 Git 提交 ID。
- CI 在 GitHub runner 上构建镜像并推送到 GHCR，tag 包含该提交 SHA。
- CD 在 VM 上只是按这个 SHA 去 GHCR 拉镜像并运行。

### Required GitHub Secrets

- `SSH_HOST`
- `SSH_PORT`
- `SSH_USER`
- `SSH_PRIVATE_KEY`

## Logging

- 日志 UI：`/web-log/`（Dozzle）
- 认证：Nginx Basic Auth（`.htpasswd`）
- Docker 日志轮转：`max-size=1m`, `max-file=5`

## Security Notes

- 内部重建接口：`POST /internal/reindex`
- 鉴权头：`X-REIMPORT-ARTICLES-TOKEN`
- WAF：`nginx-modsecurity` 默认开启；`/web-log/` 路径按需放行以保证日志流功能

## Roadmap

1. 文章界面的 css/html 调优，目前太难看，或许可以让 gemini 3 参与进来

2. 数据库 sqlite databse 可视化，方便 debug

3. 在 gcp vm 的 firewall rule 中我仅仅允许了 cf 的 ip 但是这些地址有可能会发生变动，每次变动都会需要我手动修改，如何自动化这个过程呢？

   我通过下面的这个命令得到的 cf ipv4 地址

   ```
   curl -s https://www.cloudflare.com/ips-v4 | tr '\n' ','
   ```

4. devops 推荐
   好，我们回到主线。  
   从 DevOps 角度看，你的项目已经“可上线运行”，但还缺下面这些关键项（按优先级）：

5. trivy 的 ci 扫描

**P1（第二阶段）**

3. `依赖更新自动化`  

- 用 Dependabot/Renovate 自动提升级别和安全补丁。

4. `运行手册`  

- 故障排查文档（502、DB 空表、nginx 起不来、证书权限问题）。

**P2（可选增强）**

1. `基础设施即代码`（Terraform）  

- 把 GCP firewall / monitoring / DNS 规则代码化。

2. `集中日志与指标`  

- 如果以后规模变大，再上 Loki/Grafana；当前 Dozzle + Uptime 已够用。

3. `预发环境`  

- 有条件再加 staging，当前单 VM 成本优先可先不做。

5. full-stack 推荐步骤