@echo off
SET IMAGE_NAME=reportassambler
SET CONTAINER_NAME=reportassambler_container
SET PORT_STREAMLIT=8501
SET PORT_JUPYTER=8889

echo ================================
echo   Verificando Docker Desktop
echo ================================
docker --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ Docker no está instalado o no está en el PATH.
    pause
    exit /b 1
)

echo.
echo ================================
echo   Verificando contenedor existente
echo ================================

REM Verificar si el contenedor ya está corriendo
docker ps -q -f name=%CONTAINER_NAME% >nul 2>&1
IF NOT ERRORLEVEL 1 (
    echo ✅ Container %CONTAINER_NAME% is already running.
    echo 💡 To restart, use: docker restart %CONTAINER_NAME%
    pause
    exit /b 0
)

REM Verificar si el contenedor existe pero está detenido
docker ps -aq -f name=%CONTAINER_NAME% >nul 2>&1
IF NOT ERRORLEVEL 1 (
    echo 🔄 Container %CONTAINER_NAME% exists but is stopped.
    
    REM Verificar si los puertos están ocupados
    SET PORT_BUSY=0
    
    netstat -an | findstr ":%PORT_STREAMLIT%" >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        SET PORT_BUSY=1
        echo ⚠️  Port %PORT_STREAMLIT% is busy.
    )
    
    docker ps --format "{{.Ports}}" | findstr ":%PORT_STREAMLIT%" >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        SET PORT_BUSY=1
        echo ⚠️  Port %PORT_STREAMLIT% is busy.
    )
    
    netstat -an | findstr ":%PORT_JUPYTER%" >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        SET PORT_BUSY=1
        echo ⚠️  Port %PORT_JUPYTER% is busy.
    )
    
    docker ps --format "{{.Ports}}" | findstr ":%PORT_JUPYTER%" >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        SET PORT_BUSY=1
        echo ⚠️  Port %PORT_JUPYTER% is busy.
    )
    
    IF %PORT_BUSY%==1 (
        echo ❌ Cannot start container: ports are in use.
        echo 💡 Options:
        echo    1. Stop the container using the ports: docker stop ^<container_name^>
        echo    2. Remove this container and recreate with different ports: docker rm %CONTAINER_NAME%
        echo    3. Edit start.bat to use different ports
        pause
        exit /b 1
    )
    
    echo 🚀 Starting container...
    docker start -ai %CONTAINER_NAME%
    pause
    exit /b 0
)

REM Verificar puertos antes de construir
echo 🧼 Checking ports...
SET PORT_BUSY=0

netstat -an | findstr ":%PORT_STREAMLIT%" >nul 2>&1
IF NOT ERRORLEVEL 1 (
    SET PORT_BUSY=1
    echo ⚠️  Port %PORT_STREAMLIT% is busy.
)

docker ps --format "{{.Ports}}" | findstr ":%PORT_STREAMLIT%" >nul 2>&1
IF NOT ERRORLEVEL 1 (
    SET PORT_BUSY=1
    echo ⚠️  Port %PORT_STREAMLIT% is busy.
)

netstat -an | findstr ":%PORT_JUPYTER%" >nul 2>&1
IF NOT ERRORLEVEL 1 (
    SET PORT_BUSY=1
    echo ⚠️  Port %PORT_JUPYTER% is busy.
)

docker ps --format "{{.Ports}}" | findstr ":%PORT_JUPYTER%" >nul 2>&1
IF NOT ERRORLEVEL 1 (
    SET PORT_BUSY=1
    echo ⚠️  Port %PORT_JUPYTER% is busy.
)

IF %PORT_BUSY%==1 (
    echo ❌ Cannot create container: ports are in use.
    echo 💡 Options:
    echo    1. Stop containers using the ports
    echo    2. Edit start.bat to use different ports (change PORT_STREAMLIT and PORT_JUPYTER)
    pause
    exit /b 1
)

REM Si no existe, construir imagen y crear contenedor
echo.
echo ================================
echo   Construyendo la imagen Docker
echo   (esto puede tomar unos minutos)
echo ================================
docker build -t %IMAGE_NAME% .

IF ERRORLEVEL 1 (
    echo ❌ Error al construir la imagen Docker.
    pause
    exit /b 1
)

echo.
echo ================================
echo   Iniciando contenedor
echo ================================
docker run -it --name %CONTAINER_NAME% ^
    -v "%cd%:/app" ^
    -p %PORT_STREAMLIT%:8501 ^
    -p %PORT_JUPYTER%:8888 ^
    %IMAGE_NAME%

echo.
echo ================================
echo   Contenedor detenido
echo ================================
pause
