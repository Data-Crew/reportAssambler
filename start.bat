@echo off
SET IMAGE_NAME=reportassambler
SET CONTAINER_NAME=reportassambler_container

echo Verificando si Docker está disponible...
docker --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ Docker no está instalado o no está en el PATH.
    pause
    exit /b
)

echo.
echo Construyendo la imagen de Docker...
docker build -t %IMAGE_NAME% .

echo.
echo Eliminando contenedor anterior si existe...
docker rm -f %CONTAINER_NAME% >nul 2>&1

echo.
echo Iniciando contenedor...
docker run -it --name %CONTAINER_NAME% ^
    -v "%cd%:/app" ^
    -p 8501:8501 ^
    -p 8888:8888 ^
    %IMAGE_NAME%
