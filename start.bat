@echo off
REM 开发模式：一条命令同时启动后端(FastAPI:8000)与前端(Vite:5173)
cd /d "%~dp0"

echo [1/2] 启动后端 http://127.0.0.1:8000 ...
start "report-reader-backend" cmd /k "cd backend && python run.py"

echo 等待后端就绪...
timeout /t 3 >nul

echo [2/2] 启动前端 http://127.0.0.1:5173 ...
start "report-reader-frontend" cmd /k "cd frontend && (if not exist node_modules (npm install) ) && npm run dev"

timeout /t 4 >nul
start http://127.0.0.1:5173
echo 完成。浏览器应已打开 http://127.0.0.1:5173 （前端 dev 页面，/api 自动代理到后端）
