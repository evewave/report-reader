@echo off
REM 生产/免前端进程模式：用已构建的 frontend/dist，由后端单端口托管整站 http://127.0.0.1:8000
cd /d "%~dp0"

if not exist "frontend\dist" (
  echo 未发现已构建的前端，正在构建（首次较慢）...
  pushd frontend
  if not exist node_modules call npm install
  call npm run build
  popd
)

echo 启动中：http://127.0.0.1:8000
start http://127.0.0.1:8000
cd backend && python run.py
