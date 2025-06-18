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
echo   Construyendo la imagen
echo ================================
docker build -t %IMAGE_NAME% .

echo.
echo ================================
echo   Eliminando contenedor anterior (si existe)
echo ================================
docker rm -f %CONTAINER_NAME% >nul 2>&1

echo.
echo ================================
echo   Iniciando contenedor
echo ================================
docker run -it --name %CONTAINER_NAME% ^
    -v "%cd%:/app" ^
    -p 8501:8501 ^
    -p 8888:8888 ^
    %IMAGE_NAME%

echo.
echo ================================
echo   Contenedor detenido
echo ================================
pause
