# Personal Website

个人网站与博客平台，核心技术栈为 `Flask + SQLite + Docker Compose + Nginx(ModSecurity) + GitHub Actions`。

文章内容来自我的笔记 github repo: [hanjie-chen/PersonalArticles](https://github.com/hanjie-chen/PersonalArticles)，通过定时同步与增量导入自动发布。

## Overview

Repository Layout

```text
.
├── articles-sync/                # 同步容器脚本与 Dockerfile
├── nginx-modsecurity/            # Nginx/WAF 配置、证书、Basic Auth
├── web-app/                      # Flask 应用
├── compose.yml                   # 生产配置
├── compose.dev.yml               # 开发覆盖配置
└── .github/workflows/            # CI/CD
```

- web-app: Flask 应用，负责页面路由、文章展示、内部重建接口。
- articles-sync: 定时 `git pull` 文章仓库，发现更新后调用内部 reindex 接口。
- nginx-modsecurity: 反向代理 + WAF，处理 HTTPS 和静态资源。
- dozzle: 容器日志 UI（通过 `/web-log/` 暴露并做 Basic Auth）。

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

3. 启动服务

```bash
docker compose -f compose.yml up -d
```

4. 初始化数据库并导入文章

```bash
docker compose run --rm -T web-app python scripts/init_db.py
```

说明：

- 使用 `run --rm` 不依赖 `web-app` 已先启动。
- SQLite 持久化在 `webapp_instance` volume，容器删除不会丢库。

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
  - `docker compose pull web-app articles-sync`
  - `docker compose up -d --remove-orphans`
  - 基础健康检查

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

4. 其他的 full-stack, devops 推荐