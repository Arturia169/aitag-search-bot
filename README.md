# AI Tag Search Bot

🎨 一个用于搜索 [aitag.win](https://aitag.win/) AI绘画作品的Telegram机器人

## 功能特性

- 🔍 **关键词搜索**：通过关键词搜索AI绘画作品
- 📄 **分页浏览**：支持上一页/下一页按钮浏览更多结果
- 🌐 **多语言支持**：支持中文和英文关键词
- 🐳 **Docker部署**：使用Docker Compose一键部署

## 快速开始

### 前置要求

- Docker 和 Docker Compose
- Telegram Bot Token（通过 [@BotFather](https://t.me/BotFather) 创建）

### 部署步骤

#### 方式一：使用预构建镜像（推荐）

1. **创建项目目录**
```bash
mkdir aitag-search-bot
cd aitag-search-bot
```

2. **下载配置文件**
```bash
# 下载 docker-compose.yml
curl -O https://raw.githubusercontent.com/Arturia169/aitag-search-bot/main/docker-compose.yml

# 下载环境变量示例
curl -O https://raw.githubusercontent.com/Arturia169/aitag-search-bot/main/.env.example
```

3. **配置环境变量**
```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的Bot Token：
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

4. **修改 docker-compose.yml 使用预构建镜像**
```yaml
version: '3.8'

services:
  telegram-bot:
    image: ghcr.io/arturia169/aitag-search-bot:main
    container_name: aitag-search-bot
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - TZ=Asia/Shanghai
```

5. **启动机器人**
```bash
docker-compose up -d
```

#### 方式二：从源码构建

1. **克隆仓库**
```bash
git clone https://github.com/Arturia169/aitag-search-bot.git
cd aitag-search-bot
```

2. **配置环境变量**
```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的Bot Token：
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

3. **启动机器人**
```bash
docker-compose up -d
```

#### 管理命令

4. **查看日志**
```bash
docker-compose logs -f
```

5. **停止机器人**
```bash
docker-compose down
```

## 使用方法

### 命令列表

- `/start` - 显示欢迎信息和使用说明
- `/search <关键词>` - 搜索AI绘画作品
- `/help` - 显示帮助信息

### 使用示例

1. **使用命令搜索**
```
/search wuwa
/search genshin impact
/search 原神
```

2. **直接发送关键词**
```
wuwa
原神
```

3. **浏览结果**
   - 使用消息下方的"上一页"/"下一页"按钮浏览更多结果

## 配置说明

在 `.env` 文件中可以配置以下选项：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 必填 |
| `BASE_URL` | aitag.win 网站地址 | `https://aitag.win` |
| `RESULTS_PER_PAGE` | 每页显示结果数 | `5` |
| `API_TIMEOUT` | API请求超时时间（秒） | `30` |

## 项目结构

```
aitag-search-bot/
├── bot/
│   ├── __init__.py          # 包初始化
│   ├── main.py              # 主程序入口
│   ├── config.py            # 配置管理
│   ├── api_client.py        # API客户端
│   └── telegram_bot.py      # Telegram机器人逻辑
├── Dockerfile               # Docker镜像配置
├── docker-compose.yml       # Docker Compose配置
├── requirements.txt         # Python依赖
├── .env.example            # 环境变量示例
└── README.md               # 项目说明
```

## 技术栈

- **Python 3.11+**
- **python-telegram-bot** - Telegram Bot API封装
- **aiohttp** - 异步HTTP客户端
- **Docker** - 容器化部署

## 开发

### 本地运行

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **设置环境变量**
```bash
export TELEGRAM_BOT_TOKEN=your_bot_token_here
```

3. **运行机器人**
```bash
python -m bot.main
```

## 常见问题

### 如何获取Bot Token？

1. 在Telegram中找到 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 创建新机器人
3. 按照提示设置机器人名称和用户名
4. 复制获得的Token到 `.env` 文件

### 机器人无响应？

1. 检查Docker容器是否正常运行：`docker-compose ps`
2. 查看日志：`docker-compose logs -f`
3. 确认Bot Token是否正确配置

### 搜索结果为空？

1. 尝试使用不同的关键词
2. 检查网络连接是否正常
3. 确认 aitag.win 网站是否可访问

## 许可证

MIT License

## 数据来源

本项目数据来源于 [aitag.win](https://aitag.win/)，一个AI绘画咒语图库。

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

- GitHub: [@Arturia169](https://github.com/Arturia169)
