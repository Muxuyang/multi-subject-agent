#!/bin/bash
# 启动所有智能体服务和调度中心

echo "🚀 启动多学科智能体协商辅导系统..."

# 检查环境
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，从 .env.example 复制..."
    cp .env.example .env
    echo "❗ 请编辑 .env 文件，填写 LLM_API_KEY"
    exit 1
fi

# 激活虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python -m venv venv
fi

source venv/bin/activate 2>/dev/null || source venv/Scripts/activate

# 安装依赖
echo "📦 安装依赖..."
pip install -q -r requirements.txt

# 启动智能体（后台）
echo "🤖 启动学科智能体..."
python subject_agents.py math > logs/math.log 2>&1 &
sleep 2
python subject_agents.py physics > logs/physics.log 2>&1 &
sleep 2
python subject_agents.py chemistry > logs/chemistry.log 2>&1 &
sleep 2
python subject_agents.py biology > logs/biology.log 2>&1 &
sleep 2
python subject_agents.py english > logs/english.log 2>&1 &
sleep 2
python subject_agents.py chinese > logs/chinese.log 2>&1 &
sleep 2

# 启动调度中心
echo "🎯 启动调度中心..."
python orchestrator.py > logs/orchestrator.log 2>&1 &
sleep 3

echo "✅ 所有服务已启动！"
echo ""
echo "📍 服务地址："
echo "   - 调度中心: http://localhost:8000"
echo "   - 前端界面: http://localhost:8000/static/index.html"
echo "   - API文档: http://localhost:8000/docs"
echo ""
echo "📊 查看日志: tail -f logs/*.log"
echo "🛑 停止服务: ./stop.sh"
