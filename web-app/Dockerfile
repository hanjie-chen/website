# 使用Python官方镜像作为基础镜像
FROM python:3.12-slim

# set web app directory
WORKDIR /app

# git reads note dates from the knowledge base history. The mirror is owned by the
# sync service's user, so git must trust it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*'

# 复制requirements.txt
COPY requirements.txt .

# 安装依赖
RUN pip install -r requirements.txt

# product env used, dev env use bind mount, which define in the compose.yml
COPY . .

# 暴露端口（Flask默认使用5000端口）
EXPOSE 5000

# 启动命令 (production)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
