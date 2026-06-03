# 📄 智能简历分析系统

> **Sidereus AI（星使智算）— Python 后端/全栈实习生笔试项目**

AI 赋能的简历解析与岗位匹配度分析系统。上传 PDF 简历，自动提取关键信息，与岗位 JD 进行智能匹配评分。

---

## ✨ 功能

| 模块 | 功能 | 状态 |
|------|------|------|
| 📎 PDF 解析 | 上传 PDF 简历，双引擎提取清洗文本 | ✅ |
| 🤖 AI 信息提取 | 调用大模型提取姓名/电话/邮箱/技能等结构化信息 | ✅ |
| 📊 评分匹配 | AI 分析 JD + 加权规则，计算 0-100 匹配度 | ✅ |
| ⚡ 缓存加速 | Redis + 内存双缓存，避免重复计算 | ✅ |
| 🌐 前端页面 | 简洁交互界面，部署至 GitHub Pages | ✅ |
| ☁️ Serverless | 支持阿里云函数计算 (FC) 一键部署 | ✅ |

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | Python 3.9 + FastAPI |
| **PDF 解析** | pdfplumber（主）+ PyMuPDF（备） |
| **AI 模型** | DeepSeek Chat (OpenAI 兼容接口) |
| **缓存** | Redis + 内存缓存降级 |
| **前端** | 纯 HTML/CSS/JS（零依赖） |
| **部署** | 阿里云 FC (Serverless Devs) / GitHub Pages |

## 📁 项目结构

```
Xingshi/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── main.py            # FastAPI 应用入口
│   │   ├── router.py          # API 路由 (/upload, /match, /history)
│   │   ├── config.py          # 配置管理（环境变量）
│   │   ├── models/
│   │   │   ├── schemas.py     # Pydantic 请求/响应模型
│   │   │   └── enums.py       # 错误码枚举
│   │   ├── services/
│   │   │   ├── pdf_parser.py  # PDF 解析与文本清洗
│   │   │   ├── ai_extractor.py # AI 信息提取 & JD 分析
│   │   │   ├── matcher.py     # 加权评分规则
│   │   │   └── cache.py       # Redis + 内存缓存
│   │   └── utils/
│   │       ├── logger.py      # 日志配置
│   │       └── exceptions.py  # 全局异常处理
│   ├── requirements.txt
│   └── index.py               # 阿里云 FC 入口
├── frontend/
│   └── index.html             # 单页应用（内联 CSS/JS）
├── deploy/
│   ├── s.yaml                 # Serverless Devs 配置
│   └── .env.example           # 环境变量模板
├── .github/workflows/
│   └── deploy.yml             # GitHub Pages 自动部署
└── README.md
```

## 🚀 本地运行

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# Windows PowerShell
$env:AI_API_KEY="sk-xxxxxxxx"
$env:AI_BASE_URL="https://api.deepseek.com"
$env:AI_MODEL="deepseek-v4-flash"
# 如果本地需要通过代理访问 API：
$env:HTTP_PROXY="http://127.0.0.1:7897"
```

或复制 `deploy/.env.example` 并重命名为 `.env`，然后修改配置。

### 3. 启动服务

```bash
cd backend
python -m app.main
```

访问 http://localhost:8000/docs 查看 API 文档。
访问 http://localhost:8000/redoc 查看 ReDoc 文档。

### 4. 打开前端

直接用浏览器打开 `frontend/index.html`（或通过 Live Server 启动），
在页面顶部配置 API 地址为 `http://localhost:8000/api/v1`。

## ☁️ 阿里云 FC 部署

### 前提

1. 安装 [Serverless Devs](https://www.serverless-devs.com/):
   ```bash
   npm install -g @serverless-devs/s
   s config add  # 配置阿里云 AccessKey
   ```

2. 配置环境变量（参考 `deploy/.env.example`）

### 部署

```bash
cd deploy
s deploy
```

### 更新 CORS 配置

部署后，将前端 `index.html` 中的 API 地址改为 FC 的 HTTP 触发器域名。

## 🌐 GitHub Pages 部署

1. 在 GitHub 仓库 Settings → Pages 中，选择 "GitHub Actions" 作为 Source
2. 推送 `main` 分支，`frontend/` 目录变更会自动触发部署
3. 或手动触发：Actions → Deploy Frontend to GitHub Pages → Run workflow

部署完成后访问 `https://<你的用户名>.github.io/resume-analyzer/`

## 📡 API 文档

### `POST /api/v1/upload`
上传 PDF 简历文件。

**请求:** `multipart/form-data`，字段 `file` 为 PDF 文件

**响应:**
```json
{
  "text": "清洗后的简历文本…",
  "extracted": {
    "name": "张三",
    "phone": "13800138000",
    "email": "zhangsan@example.com",
    "address": "北京",
    "skills": ["Python", "FastAPI", "Redis"]
  },
  "cached": false
}
```

### `POST /api/v1/match`
简历评分匹配。

**请求:**
```json
{
  "resume_json": { "...": "从 /upload 返回的 extracted" },
  "jd_text": "岗位需求描述…"
}
```

**响应:**
```json
{
  "score": 85.5,
  "details": [
    { "dimension": "技能匹配", "weight": 0.5, "score": 90.0, "detail": "…" },
    { "dimension": "学历匹配", "weight": 0.2, "score": 100.0, "detail": "…" }
  ],
  "cached": false
}
```

### `GET /api/v1/history`
查询历史记录。

## 📝 Git 提交建议

```
feat: init 项目结构与基础配置
feat: add PDF 上传与解析模块
feat: add AI 简历信息提取模块
feat: add 简历评分与岗位匹配
feat: add Redis 缓存层
feat: add RESTful API 路由
feat: add 前端交互页面
feat: add 部署配置与文档
```

---

**Sidereus AI · 让科学计算触手可及** 🔬
