# UO HR 系统部署文档

## 环境要求

### 硬件配置
- **CPU**: 4核心或以上
- **内存**: 8GB RAM（最低），16GB RAM（推荐）
- **存储**: 100GB SSD（最低），考虑数据增长预留空间
- **网络**: 稳定的网络连接，建议千兆网卡

### 软件要求
- **操作系统**: Ubuntu 20.04 LTS / 22.04 LTS 或 Debian 11/12
- **Docker**: 20.10.x 或更高版本
- **Docker Compose**: 2.0.x 或更高版本
- **Git**: 2.x 或更高版本

## 快速部署（Docker 方式）

### 1. 克隆项目
```bash
git clone https://github.com/uo/hrms.git
cd hrms/docker
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
```

关键配置项：
```env
# 站点配置
SITE_NAME=hrms.uo.co.jp
ADMIN_PASSWORD=<设置强密码>

# 数据库配置
DB_ROOT_PASSWORD=<数据库root密码>
MYSQL_ROOT_PASSWORD=<MySQL root密码>

# 邮件配置
MAIL_SERVER=smtp.uo.co.jp
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=hr@uo.co.jp
MAIL_PASSWORD=<邮件密码>
```

### 3. 启动服务
```bash
docker-compose up -d
```

### 4. 等待初始化完成
首次启动需要 5-10 分钟完成初始化，可以查看日志：
```bash
docker-compose logs -f
```

### 5. 访问系统
- URL: http://localhost:8000
- 默认用户名: `Administrator`
- 默认密码: `admin` （首次登录后务必修改）

## 生产环境部署

### 1. 使用 Nginx 反向代理
```nginx
# /etc/nginx/sites-available/uo-hr
server {
    listen 80;
    server_name hrms.uo.co.jp;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name hrms.uo.co.jp;

    # SSL 证书配置
    ssl_certificate /etc/ssl/certs/uo-hr.crt;
    ssl_certificate_key /etc/ssl/private/uo-hr.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 日志
    access_log /var/log/nginx/uo-hr-access.log;
    error_log /var/log/nginx/uo-hr-error.log;

    # 代理配置
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://localhost:8000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 文件上传大小限制
    client_max_body_size 100M;
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/uo-hr /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. SSL 证书配置
使用 Let's Encrypt 免费证书：
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d hrms.uo.co.jp
```

### 3. 防火墙配置
```bash
# 允许 HTTP/HTTPS
sudo ufw allow 'Nginx Full'

# 允许 SSH（如果需要）
sudo ufw allow OpenSSH

# 启用防火墙
sudo ufw enable
```

### 4. 系统服务配置
创建 systemd 服务文件 `/etc/systemd/system/uo-hr.service`：
```ini
[Unit]
Description=UO HR System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/uo/dev/hrms/docker
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable uo-hr.service
sudo systemctl start uo-hr.service
```

## 数据库配置

### 备份策略
```bash
# 创建备份脚本 /opt/scripts/backup-uo-hr.sh
#!/bin/bash
BACKUP_DIR="/backup/uo-hr"
DATE=$(date +%Y%m%d_%H%M%S)
SITE_NAME="hrms.localhost"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
docker exec frappe-bench-frappe-1 bench --site $SITE_NAME backup \
    --with-files \
    --backup-path-db $BACKUP_DIR/db_${DATE}.sql.gz \
    --backup-path-files $BACKUP_DIR/files_${DATE}.tar

# 删除 30 天前的备份
find $BACKUP_DIR -type f -mtime +30 -delete

# 发送备份通知
echo "UO HR 备份完成: $DATE" | mail -s "UO HR Backup" admin@uo.co.jp
```

设置定时任务：
```bash
# 编辑 crontab
sudo crontab -e

# 每天凌晨 2 点执行备份
0 2 * * * /opt/scripts/backup-uo-hr.sh
```

### 数据库优化
```bash
# 进入容器
docker exec -it frappe-bench-mariadb-1 bash

# 连接数据库
mysql -u root -p

# 优化表
USE `_b8d9e1234567890`;
OPTIMIZE TABLE `tabEmployee`;
OPTIMIZE TABLE `tabAttendance`;
OPTIMIZE TABLE `tabSalary Slip`;

# 分析表
ANALYZE TABLE `tabEmployee`;
```

## 性能优化

### 1. Redis 缓存配置
编辑站点配置 `/sites/hrms.localhost/site_config.json`：
```json
{
  "redis_cache": "redis://redis-cache:6379",
  "redis_queue": "redis://redis-queue:6379",
  "redis_socketio": "redis://redis-socketio:6379",
  "cache_ttl": 3600
}
```

### 2. Gunicorn Workers
编辑 `Procfile`：
```
web: gunicorn frappe.app:application --bind 0.0.0.0:8000 --workers 4 --timeout 300 --max-requests 1000
```

### 3. 启用压缩
在 `common_site_config.json` 添加：
```json
{
  "compress_html": true,
  "minify_js": true
}
```

## 监控和日志

### 1. 日志查看
```bash
# 查看应用日志
docker-compose logs -f frappe

# 查看数据库日志
docker-compose logs -f mariadb

# 查看 Nginx 日志
sudo tail -f /var/log/nginx/uo-hr-access.log
```

### 2. 系统监控
安装监控工具：
```bash
# 安装 Prometheus + Grafana
docker run -d --name=prometheus -p 9090:9090 prom/prometheus
docker run -d --name=grafana -p 3000:3000 grafana/grafana
```

### 3. 健康检查
创建健康检查脚本 `/opt/scripts/health-check.sh`：
```bash
#!/bin/bash
SITE_URL="https://hrms.uo.co.jp"

# 检查站点可用性
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $SITE_URL)

if [ $HTTP_CODE -eq 200 ]; then
    echo "UO HR 系统运行正常"
else
    echo "UO HR 系统异常，HTTP 状态码: $HTTP_CODE" | mail -s "UO HR Alert" admin@uo.co.jp
fi
```

## 故障排除

### 常见问题

#### 1. 无法访问系统
```bash
# 检查容器状态
docker-compose ps

# 重启服务
docker-compose restart

# 查看错误日志
docker-compose logs
```

#### 2. 数据库连接失败
```bash
# 检查数据库容器
docker exec -it frappe-bench-mariadb-1 mysql -u root -p -e "SHOW DATABASES;"

# 重新创建站点配置
bench --site hrms.localhost set-config db_name _新数据库名
```

#### 3. 静态资源加载失败
```bash
# 重新构建资源
bench build --app hrms

# 清除缓存
bench clear-cache
bench clear-website-cache
```

## 安全加固

### 1. 更改默认端口
编辑 `docker-compose.yml`，修改端口映射：
```yaml
ports:
  - "18000:8000"  # 使用非标准端口
```

### 2. 启用双因素认证
在系统设置中启用 2FA：
```
设置 → 系统设置 → 启用双因素认证
```

### 3. IP 白名单
在 Nginx 配置中添加：
```nginx
# 仅允许公司内网访问
allow 192.168.1.0/24;
allow 10.0.0.0/8;
deny all;
```

### 4. 定期更新
```bash
# 更新系统
cd /home/uo/dev/hrms
git pull origin main

# 重启服务
docker-compose down
docker-compose up -d

# 执行数据库迁移
docker exec frappe-bench-frappe-1 bench --site hrms.localhost migrate
```

## 技术支持

如遇到部署问题，请联系：
- 邮箱: hr@uo.co.jp
- 紧急联系: +81-XX-XXXX-XXXX

---

© 2025 株式会社UO. All Rights Reserved.

