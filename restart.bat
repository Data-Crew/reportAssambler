@echo off
SET IMAGE_NAME=reportassambler
SET CONTAINER_NAME=reportassambler_container

echo ================================
echo   Verificando Docker Desktop
echo ================================
docker --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ Docker no está instalado o no está en el PATH.
    pause
    exit /b
)

echo.
echo ================================
echo   Verificando imagen existente
echo ================================
docker image inspect %IMAGE_NAME% >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ La imagen %IMAGE_NAME% no existe. Debes ejecutarlo con start.bat al menos una vez.
    pause
    exit /b
)

echo.
echo ================================
echo   Verificando contenedor existente
echo ================================
docker container inspect %CONTAINER_NAME% >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❗ No hay un contenedor con nombre %CONTAINER_NAME%. Se creará uno nuevo.
    docker run -it --name %CONTAINER_NAME% ^
        -v "%cd%:/app" ^
        -p 8501:8501 ^
        -p 8889:8888 ^
        %IMAGE_NAME%
    goto :eof
)

REM Si el contenedor existe, verificamos si está detenido o corriendo
for /f "tokens=*" %%i in ('docker inspect -f "{{.State.Running}}" %CONTAINER_NAME%') do set RUNNING=%%i

if "%RUNNING%"=="true" (
    echo ✅ El contenedor ya está en ejecución.
    pause
    exit /b
) else (
    echo 🔄 Iniciando contenedor detenido...
    docker start -ai %CONTAINER_NAME%
)

echo.
echo ================================
echo   Contenedor detenido
echo ================================
pause
