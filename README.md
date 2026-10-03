# 多学科智能体协商辅导系统

## 项目简介
基于AIP协议的多学科智能体协商系统，实现语文、数学、英语、物理、化学、生物六个学科智能体的自主协商与知识融合，为学生提供跨学科综合辅导。

## 技术架构
- **协议层**: AIP (Agent Interaction Protocol) 数据模型
- **智能体层**: 6个学科专家智能体 + 1个调度中心
- **通信模式**: Direct RPC (HTTP/JSON)
- **大模型**: 通义千问 API
- **前端**: 原生HTML/CSS/JavaScript
- **后端**: Python + FastAPI

## 核心创新
1. **多智能体协商机制**: 问题自动路由到相关学科，并行调用多个智能体
2. **知识融合策略**: 基于学科权重和置信度的答案协商融合
3. **符合AIP规范**: 完整实现TaskCommand/TaskResult状态机

## 目录结构
```
multi-subject-agent/
├── aip_models.py          # AIP协议数据模型
├── subject_agents.py      # 6个学科智能体实现
├── orchestrator.py        # 调度中心（协商引擎）
├── requirements.txt       # Python依赖
├── .env.example          # 环境变量模板
├── start.bat / start.sh  # 启动脚本
├── stop.bat              # 停止脚本
└── static/
    └── index.html        # Web前端界面
```

## 快速开始

### 1. 环境准备
```bash
# 克隆或进入项目目录
cd multi-subject-agent

# 创建虚拟环境
python -m venv venv

# Windows激活
venv\Scripts\activate
# Linux/Mac激活
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env，填写通义千问API Key
# LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 3. 启动服务
**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

### 4. 访问系统
- 前端界面: http://localhost:8000/static/index.html
- API文档: http://localhost:8000/docs
- 调度中心健康检查: http://localhost:8000/health

## 服务端口
- 8000: 调度中心 (Orchestrator)
- 8001: 数学智能体
- 8002: 物理智能体
- 8003: 化学智能体
- 8004: 生物智能体
- 8005: 英语智能体
- 8006: 语文智能体

## API使用示例

### 提问接口
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "光合作用的化学方程式中能量转化效率是多少？"}'
```

### 响应示例
```json
{
  "question": "光合作用的化学方程式中能量转化效率是多少？",
  "involved_subjects": ["生物", "化学", "物理"],
  "subject_answers": {
    "生物": "从生物学角度...",
    "化学": "从化学反应角度...",
    "物理": "从能量转化角度..."
  },
  "negotiated_answer": "【综合分析】...",
  "task_id": "task_1696320000000",
  "timestamp": "2026-10-03T12:00:00"
}
```

## 智能体协商流程
1. **问题分析**: 调度中心通过关键词匹配识别涉及学科
2. **并行调用**: 异步调用相关学科智能体（Direct RPC模式）
3. **答案生成**: 各智能体基于专业视角生成答案
4. **协商融合**: 调度中心融合多学科答案，形成综合解答

## AIP协议实现
- ✅ TaskCommand (start/get/continue/complete/cancel)
- ✅ TaskResult (accepted/working/awaiting-completion/completed)
- ✅ Message基础模型
- ✅ Product产出物
- ✅ 状态机完整实现

## 停止服务
**Windows:**
```bash
stop.bat
```

**Linux/Mac:**
```bash
# 查找进程并终止
ps aux | grep "subject_agents\|orchestrator" | grep -v grep | awk '{print $2}' | xargs kill
```

## 日志查看
```bash
# Windows
type logs\*.log

# Linux/Mac
tail -f logs/*.log
```

## 梧桐平台对接说明
1. 在梧桐平台注册7个智能体（6学科+调度中心）
2. 获取AIC和mTLS证书
3. 配置证书到各服务
4. 记录注册/发现/互联/访问全流程截图
5. 统计后台访问量

## 依赖说明
- fastapi: Web框架
- uvicorn: ASGI服务器
- pydantic: 数据验证
- httpx: 异步HTTP客户端
- openai: 大模型API客户端（兼容通义千问）
- jieba: 中文分词（用于问题分析）

## 开发者
2026 AIC·智能体互联算法主题赛作品

## 许可证
MIT License
