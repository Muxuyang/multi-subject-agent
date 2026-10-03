@echo off
REM Windows批处理启动脚本

echo 启动多学科智能体协商辅导系统...

REM 检查.env文件
if not exist .env (
    echo 未找到 .env 文件，从 .env.example 复制...
    copy .env.example .env
    echo 请编辑 .env 文件，填写 LLM_API_KEY
    pause
    exit /b 1
)

REM 创建日志目录
if not exist logs mkdir logs

REM 激活虚拟环境
if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

call venv\Scripts\activate.bat

REM 安装依赖
echo 安装依赖...
pip install -q -r requirements.txt

REM 启动智能体（后台）
echo 启动学科智能体...
start /B python subject_agents.py math > logs\math.log 2>&1
timeout /t 2 /nobreak >nul
start /B python subject_agents.py physics > logs\physics.log 2>&1
timeout /t 2 /nobreak >nul
start /B python subject_agents.py chemistry > logs\chemistry.log 2>&1
timeout /t 2 /nobreak >nul
start /B python subject_agents.py biology > logs\biology.log 2>&1
timeout /t 2 /nobreak >nul
start /B python subject_agents.py english > logs\english.log 2>&1
timeout /t 2 /nobreak >nul
start /B python subject_agents.py chinese > logs\chinese.log 2>&1
timeout /t 2 /nobreak >nul

REM 启动调度中心
echo 启动调度中心...
start /B python orchestrator.py > logs\orchestrator.log 2>&1
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo 所有服务已启动！
echo.
echo 服务地址：
echo    调度中心: http://localhost:8000
echo    前端界面: http://localhost:8000/static/index.html
echo    API文档: http://localhost:8000/docs
echo.
echo 查看日志: type logs\*.log
echo 停止服务: stop.bat
echo ========================================
echo.
pause
