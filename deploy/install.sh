#!/usr/bin/env bash
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${YELLOW}🦞 美术审计平台 一键安装脚本${NC}"
echo "================================================"

# 1. 检测 OS 并安装 Docker
install_docker() {
  if command -v docker &>/dev/null; then
    echo -e "${GREEN}✓ Docker 已安装，跳过${NC}"
    return
  fi
  echo "正在安装 Docker..."
  if command -v apt-get &>/dev/null; then
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  elif command -v yum &>/dev/null; then
    yum install -y -q yum-utils
    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    yum install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
  elif command -v dnf &>/dev/null; then
    dnf install -y -q dnf-plugins-core
    dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
    dnf install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
  else
    echo -e "${RED}✗ 不支持的包管理器，请手动安装 Docker${NC}" && exit 1
  fi
  echo -e "${GREEN}✓ Docker 安装完成${NC}"
}

install_docker

# 2. 启动 Docker
systemctl enable docker --now 2>/dev/null || true
echo -e "${GREEN}✓ Docker 服务已启动${NC}"

# 3. 创建工作目录
WORK_DIR="$HOME/art-audit-platform"
mkdir -p "$WORK_DIR/data/uploads"
cd "$WORK_DIR"
echo -e "${GREEN}✓ 工作目录：$WORK_DIR${NC}"

# 4. 生成 .env（已存在则跳过）
if [ ! -f ".env" ]; then
  ADMIN_TOKEN=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 32)
  WORKER_TOKEN=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 32)
  cat > .env <<EOF
ADMIN_TOKEN=${ADMIN_TOKEN}
WORKER_TOKEN=${WORKER_TOKEN}
DATA_DIR=/data
EOF
  echo -e "${GREEN}✓ .env 已生成（Token 已随机生成）${NC}"
else
  echo -e "${YELLOW}⚠ .env 已存在，跳过生成，保留原有数据${NC}"
  ADMIN_TOKEN=$(grep ADMIN_TOKEN .env | cut -d= -f2)
  WORKER_TOKEN=$(grep WORKER_TOKEN .env | cut -d= -f2)
fi

# 5. 写入最新 docker-compose.yml
cat > docker-compose.yml <<'COMPOSE'
services:
  app:
    image: ghcr.io/hewenze11/art-audit-platform:latest
    container_name: art-audit-platform
    restart: unless-stopped
    ports:
      - "80:8000"
    volumes:
      - ./data:/data
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
COMPOSE
echo -e "${GREEN}✓ docker-compose.yml 已更新${NC}"

# 6. 拉取最新镜像
echo "正在拉取镜像..."
docker pull ghcr.io/hewenze11/art-audit-platform:latest
echo -e "${GREEN}✓ 镜像拉取完成${NC}"

# 7. 启动服务
docker compose down 2>/dev/null || true
docker compose up -d
echo -e "${GREEN}✓ 容器已启动${NC}"

# 8. 等待健康检查
echo "等待服务就绪..."
TIMEOUT=30
COUNT=0
while [ $COUNT -lt $TIMEOUT ]; do
  if curl -sf http://localhost/health &>/dev/null; then
    break
  fi
  sleep 1
  COUNT=$((COUNT+1))
done

if [ $COUNT -ge $TIMEOUT ]; then
  echo -e "${RED}✗ 服务启动超时，日志如下：${NC}"
  docker compose logs --tail=50
  exit 1
fi

# 9. 获取本机 IP
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✅ 美术审计平台启动成功！${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "🌐 访问地址:     http://${LOCAL_IP}"
echo -e "📋 主管审批看板: http://${LOCAL_IP}/"
echo -e "🛠  CTO需求发布:  http://${LOCAL_IP}/cto.html"
echo -e "🎨 美术任务端:   http://${LOCAL_IP}/worker.html"
echo -e "📦 资产调用端:   http://${LOCAL_IP}/assets.html"
echo ""
echo -e "🔑 ADMIN_TOKEN:  ${ADMIN_TOKEN}"
echo -e "🔑 WORKER_TOKEN: ${WORKER_TOKEN}"
echo ""
echo -e "💾 数据目录: ${WORK_DIR}/data（备份此目录即可迁移全部数据）"
echo -e "${GREEN}================================================${NC}"
