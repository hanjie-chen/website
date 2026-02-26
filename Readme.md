# About the website

## contianer introduce

### dozzle
用于监控和检查所有 container 的 log（包括自己的）本质上是 docker logs 命令的 ui 化

### articles-sync container
articles-sync container 用于管理我的 markdown 笔记文章, 使用 alpine:3.19 作为image
因为我的笔记文章存放在一个 github repository 中，并且常常更新，所以它的主要作用是每天定期的 git pull 这个 github repository 到某一个目录中，而这个目录实际上是一个 docker volumes 挂载上去的，它对这个目录有读写的权限
我使用 crond 定期执行一个 shell 脚本来实现定期 git pull, 日志输出到 stdout（容器日志）

日常更新由 `articles-sync` 触发：
  - `articles-sync` 完成 `git pull` 后会调用 web-app 内部接口触发 reindex
  - reindex 会增量更新文章与 HTML（不会清空数据库）
  - 需要在 `.env` 中配置 `REIMPORT_ARTICLES_TOKEN`

### nginx-modsecurity container
使用 owasp/modsecurity-crs:nginx-alpine container 作为反向代理，暴露80端口在外
并且使用其默认的 waf 来拦截一些恶意流量

其中 `.htpasswd` 文件用于接入 dozzle 作为后台 log 的查看，内容可以由下面的代码生成

```
docker run --rm httpd:2.4-alpine htpasswd -nbB <username> <password>
```

未来考虑：
将 rendered-articles 作为一个 volume 挂载在 /usr/share/nginx/html 下面，将其作为 document root
但是在 web-app 中会直接读取 /rendered-articles 中的 html 然后以字符串的方式将 html 传递给 articles_details.html 完成渲染，所以这个地方使用nginx的document root, 需要修改其逻辑以方便 nginx 提供静态服务

以及 flask static 文件夹似乎也可以放到 nginx document root 中去

### web-app container
web-app container 作为我的网站主体，使用 python flask 3.x 开发, 使用 python:3.9 slim 作为image
它同样挂载 docker volumes, 但是对其只有读的权限，他会去这个目录下拿取我的 markdown 文章
首先提取 metadata 插入数据库，然后处理文章的内容，我使用 python-markdown 将其渲染为 html 并且存放在 rendered-articles 目录下
并将这个目录注册为一个staic folder, 这样子 flask 路由函数就可以找到这些 html
为了实现一些特殊的 markdown 渲染效果，我自己写了一些 python-markdown extension, 比如说客制化的 GFM-admonition 等

dev / prod 运行方式

- 生产环境（默认）：`compose.yml`
- 开发环境：`compose.yml` + `compose.dev.yml`

for example
```
# 生产
docker compose -f compose.yml up -d

# 开发
docker compose -f compose.yml -f compose.dev.yml up
```

# prod env settings
生产环境设置步骤
1. `.env` file settings
```
REIMPORT_ARTICLES_TOKEN=change-me
```
2. nginx-modsecurity/ssl settings
3. nginx-modsecurity/.htpasswd settings
4. init database
先执行一次初始化，用于建表并导入所有文章
```
docker compose run --rm -T web-app python scripts/init_db.py
```
- 使用 `run --rm` 不依赖 `web-app` 已经启动；初始化完成后容器会自动删除。
- `compose.yml` 已将 `/app/instance` 持久化到 `webapp_instance` volume，所以 sqlite 数据不会因临时容器删除而丢失。
- 否则使用，gunicorn 开多个实例就会因为同时建表报错了。

## articles introduce
我原本的 markdown 笔记结构如下所示
```
└───python-learn
    ├───python-language
    ├───python-package
    │   ├───Flask
    │   │   └───images
    │   ...
    │   └───standard-library
    │       ├───re
    │       │   └───images
    │       └───shutil
    └───python-practices
```
是多层的树形结构，但是这是为了方便我写文章和分类，但对我的网站来说则不需要多层的树形结构，所以我使用 `-` 代替了路径中的 `/` 将其存放于 rendered-articles 目录下面
```
rendered-articles/
├── PythonLearn-PythonPackage-SQLAlchemy
│   ├── 2.html
│   └── images
│       └── cover_image.png
├── PythonLearn-PythonPackage-flask-sqlalchemy
│   ├── 3.html
│   └── images
│       └── cover_image.webp
└── ToolGuide-GitGuide
    ├── 1.html
    └── images
        └── cover_image.png
```
最多只有2层目录

### database design

为了管理的文章元数据，我针对 category 和 coverimage url 设计如下
```   
   
# 文章封面链接 真实image存储地址 由于特别设计，所以可以由category+相对路径转换而来
# 例如 PythonLearn/PythonPackage/Flask/images/cover-image.png 其 cover_image_url = "redered-articles/PythonLearn-PythonPackage-Flask/images/cover-image.png"
cover_image_url: Mapped[str] = mapped_column(String(100))

# 文章分类 是文章的路径
# 例如 PersonalActicles/PythonLearn/PythonPackage/Flask/Basic.md 其 category = "PythonLearn/PythonPackage/Flask"
# 暂时定义最大长度 1024 个字符
category: Mapped[str] = mapped_column(String(1024))
```

# Web architecture

目前的架构是 cloudflare (free plan) --> gcp linux vm(3 containers)
因为 cloudflare free plan 提供一些最基础的 waf + 在 nginx 上面安装 waf (如果之后遇到了需要 autoscale 的情况，在将 waf container 分离出来,方便 autoscale)

# future consider
2/ try to use bootstrap5 to opt the css effect
1/ connect to sqlite database to show the data in the sqlite
3/ 在 gcp vm firewall rule 上仅允许 cf ip

# ci/cd process

本项目使用 GitHub Actions 实现 CI/CD。

## GitHub Secrets

CD 需要在仓库 Settings -> Secrets and variables -> Actions 中配置：
- `SSH_HOST`
- `SSH_PORT`
- `SSH_USER`
- `SSH_PRIVATE_KEY`

可选：
- `SSH_KNOWN_HOSTS`（固定 host key，避免 MITM）




