@echo off
echo ===================================================
echo      KUBE-AI Infrastructure Boot Sequence
echo ===================================================

echo.
echo [1/3] Waking up Rancher Desktop (The Lightweight Engine)...

set RANCHER_PATH=%LOCALAPPDATA%\Programs\Rancher Desktop\Rancher Desktop.exe
if not exist "%RANCHER_PATH%" set RANCHER_PATH=C:\Program Files\Rancher Desktop\Rancher Desktop.exe

start "" "%RANCHER_PATH%"

:: Add Rancher Desktop binaries to PATH for this session
set PATH=C:\Program Files\Rancher Desktop\resources\resources\win32\bin;%PATH%
set PATH=C:\Program Files\Rancher Desktop\resources\resources\linux\bin;%PATH%

:: Use the correct Docker context (points to docker_engine pipe)
docker context use default

echo ... giving Rancher Desktop a moment to begin startup ...
timeout /t 90 /nobreak > NUL

:wait_for_docker
docker info 2>&1 | findstr /i "Server Version" >nul
if %errorlevel% == 0 goto docker_ready

echo ... engine still waking up, retrying in 5 seconds ...
timeout /t 5 /nobreak > NUL
goto wait_for_docker

:docker_ready
echo.
echo [2/3] Docker is ALIVE. Booting Kubernetes Cluster...
minikube start --driver=docker

echo.
echo [3/3] Igniting Master API...
cd /d "%~dp0backend"
call venv\Scripts\activate
uvicorn main:app --reload

pause