# Flask 订阅代理服务部署指南

## 项目概述

这是一个基于 Flask 的订阅代理服务，用于安全地获取和管理 API 订阅内容。服务支持 Docker 容器化部署和本地环境运行，使用 Gunicorn 作为生产环境 WSGI 服务器。

## 功能特点

- 🔐 安全的凭证管理（支持环境变量和文件两种方式）
- ⚡ 自动 token 刷新机制
- 🔄 订阅内容代理转发
- 📊 完整的日志记录
- 🐳 Docker 容器化部署
- 🔧 Gunicorn 生产级服务器

## 环境变量配置

| 变量名 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| `API_BASE_URL` | 是 | API 基础 URL | `https://api.example.com` |
| `API_EMAIL` | 是* | API 登录邮箱 | `user@example.com` |
| `API_PASSWORD` | 是* | API 登录密码 | `password123` |
| `API_EMAIL_FILE` | 是* | 包含邮箱的文件路径 | `/app/secrets/email` |
| `API_PASSWORD_FILE` | 是* | 包含密码的文件路径 | `/app/secrets/password` |

> *注意：邮箱和密码可以通过环境变量或文件提供，优先使用文件方式以提高安全性。必须至少提供其中一种方式。

## Docker 运行教程

### 1. 构建 Docker 镜像

```bash
docker build -t flask-subscribe-proxy .
```

### 2. 运行容器

#### 方式一：使用环境变量（推荐用于开发）

```bash
docker run -d \
  -p 5000:5000 \
  -e API_BASE_URL=https://api.example.com \
  -e API_EMAIL=your_email@example.com \
  -e API_PASSWORD=your_password \
  --name subscribe-proxy \
  flask-subscribe-proxy
```

#### 方式二：使用安全文件（推荐用于生产）

首先创建凭证文件：

```bash
mkdir -p secrets
echo "your_email@example.com" > secrets/email
echo "your_password" > secrets/password
echo "https://api.example.com" > secrets/api_base_url
chmod 600 secrets/*
```

然后运行容器：

```bash
docker run -d \
  -p 5000:5000 \
  -e API_BASE_URL_FILE=/app/secrets/api_base_url \
  -e API_EMAIL_FILE=/app/secrets/email \
  -e API_PASSWORD_FILE=/app/secrets/password \
  -v $(pwd)/secrets:/app/secrets \
  --name subscribe-proxy \
  flask-subscribe-proxy
```

### 3. 使用 Docker Compose 部署

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  subscribe-proxy:
    build: .
    ports:
      - "5000:5000"
    environment:
      - API_BASE_URL_FILE=/app/secrets/api_base_url
      - API_EMAIL_FILE=/app/secrets/email
      - API_PASSWORD_FILE=/app/secrets/password
    volumes:
      - ./secrets:/app/secrets
    restart: unless-stopped
```

运行服务：

```bash
docker-compose up -d
```

### 4. 验证 Docker 服务

访问测试端点确认服务正常运行：

```bash
curl http://localhost:5000/test
```

### 5. 获取订阅内容

```bash
curl http://localhost:5000/get_subscribe
```

## 本地运行教程

### 前提条件

在开始之前，请确保您的系统已安装：
- Python 3.9 或更高版本
- pip（Python 包管理工具）

### 1. 创建虚拟环境（推荐）

```bash
# 创建项目目录并进入
mkdir flask-subscribe-proxy
cd flask-subscribe-proxy

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

设置必要的环境变量。您可以选择以下任一方式：

#### 方式一：直接设置环境变量

```bash
# Windows:
set API_BASE_URL=https://api.example.com
set API_EMAIL=your_email@example.com
set API_PASSWORD=your_password

# Linux/Mac:
export API_BASE_URL=https://api.example.com
export API_EMAIL=your_email@example.com
export API_PASSWORD=your_password
```

#### 方式二：使用 `.env` 文件（推荐）

创建 `.env` 文件：

```bash
# 创建并编辑 .env 文件
echo "API_BASE_URL=https://api.example.com" > .env
echo "API_EMAIL=your_email@example.com" >> .env
echo "API_PASSWORD=your_password" >> .env
```

> **安全提示**：确保将 `.env` 添加到 `.gitignore` 中，避免将敏感信息提交到版本控制。

### 4. 运行应用程序

#### 开发模式运行（使用 Flask 内置服务器）

```bash
# 设置 Flask 环境变量
export FLASK_APP=app.py
export FLASK_ENV=development

# 运行应用
flask run --host=0.0.0.0 --port=5000
```

或者直接运行 Python 文件：

```bash
python app.py
```

#### 生产模式运行（使用 Gunicorn）

```bash
gunicorn --bind 0.0.0.0:5000 app:app --workers 4 --timeout 120
```

### 5. 验证本地服务

打开浏览器或使用 curl 测试服务：

```bash
curl http://localhost:5000/test
```

如果一切正常，您应该看到响应："服务正常运行!"

## API 端点

### GET /test
测试服务是否正常运行

**响应示例**:
```
服务正常运行! 当前API基础URL: https://api.example.com
```

### GET /get_subscribe
获取订阅内容

**响应**:
返回原始订阅内容

## 生产环境建议

1. **使用 Docker Secrets**：在 Swarm 模式下使用 Docker secrets 管理敏感信息
2. **配置反向代理**：使用 Nginx 作为反向代理，添加 SSL 终止和速率限制
3. **监控和日志**：配置日志轮转和监控告警
4. **资源限制**：为容器设置适当的 CPU 和内存限制
5. **定期更新**：定期更新基础镜像和依赖包

## 故障排除

### 常见问题

1. **无法获取 token**：检查邮箱和密码是否正确
2. **服务启动失败**：查看容器日志 `docker logs subscribe-proxy`
3. **连接超时**：确认上游 API 服务可访问
4. **API_BASE_URL 未设置**：确保已正确设置 API_BASE_URL 环境变量

### 查看日志

```bash
# Docker 容器日志
docker logs -f subscribe-proxy

# 本地运行日志
# 直接查看控制台输出或配置日志文件
```

## 安全注意事项

- 切勿将凭证文件提交到版本控制系统
- 在生产环境使用最小权限原则运行容器
- 定期轮换 API 凭证
- 使用防火墙限制对服务的访问
- 优先使用文件方式存储敏感信息而非环境变量
