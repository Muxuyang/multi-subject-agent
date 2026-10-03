@echo off
REM 停止所有服务

echo 正在停止所有服务...

REM 查找并终止Python进程
taskkill /F /IM python.exe /FI "WINDOWTITLE eq subject_agents.py*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq orchestrator.py*" 2>nul

REM 更通用的方法：终止监听8000-8006端口的进程
for /L %%p in (8000,1,8006) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| find ":%%p" ^| find "LISTENING"') do (
        echo 终止端口 %%p 上的进程 %%a
        taskkill /F /PID %%a 2>nul
    )
)

echo 所有服务已停止！
timeout /t 2 /nobreak >nul
