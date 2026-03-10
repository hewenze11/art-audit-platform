# 美术审计平台

一个用于管理美术资产审批流程的全栈平台。

## 功能概览

- 🎨 **CTO 需求发布端** (`/cto.html`) — 管理项目和需求
- ✅ **审批看板** (`/index.html`) — 审批美术提交件
- 🖌 **美术任务端** (`/worker.html`) — 上传美术资产
- 📦 **资产调用端** (`/assets.html`) — 浏览和下载已审批资产

## 快速部署

```bash
curl -sSL https://raw.githubusercontent.com/hewenze11/art-audit-platform/main/deploy/install.sh | sudo bash
```

## 技术栈

- **后端**: Python 3.11 + FastAPI
- **数据库**: SQLite
- **前端**: HTML5 + TailwindCSS CDN + Vanilla JS
- **容器**: Docker (单一镜像)

## 手动部署

1. 安装 Docker

2. 创建目录和 .env 文件：
```bash
mkdir -p ~/art-audit-platform/data/uploads
cd ~/art-audit-platform
cat > .env <<EOF
ADMIN_TOKEN=your-admin-token
WORKER_TOKEN=your-worker-token
DATA_DIR=/data
EOF
```

3. 拉取并启动：
```bash
curl -sSL https://raw.githubusercontent.com/hewenze11/art-audit-platform/main/deploy/docker-compose.yml > docker-compose.yml
docker compose up -d
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `ADMIN_TOKEN` | 管理员访问令牌 |
| `WORKER_TOKEN` | 美术人员访问令牌 |
| `DATA_DIR` | 数据目录路径（默认 `/data`） |
