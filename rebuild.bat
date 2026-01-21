@echo off
SET IMAGE_NAME=reportassambler
SET CONTAINER_NAME=reportassambler_container
SET PORT_STREAMLIT=8501
SET PORT_JUPYTER=8889

echo ================================
echo   REBUILD - Report Assembler
echo ================================
echo.
echo Este script va a:
echo   1. Detener y eliminar el contenedor anterior
echo   2. Eliminar la imagen anterior
echo   3. Reconstruir la imagen con los ultimos cambios
echo   4. Iniciar el contenedor con Streamlit
echo.

echo ================================
echo   Verificando Docker Desktop
echo ================================
docker --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ Docker no esta instalado o no esta en el PATH.
    echo 💡 Asegurate de tener Docker Desktop corriendo.
    pause
    exit /b 1
)

echo ✅ Docker esta disponible
echo.

REM Detener y eliminar contenedor si existe
echo ================================
echo   Limpiando contenedor anterior
echo ================================
docker ps -aq -f name=%CONTAINER_NAME% >nul 2>&1
IF NOT ERRORLEVEL 1 (
    echo 🔄 Deteniendo contenedor %CONTAINER_NAME%...
    docker stop %CONTAINER_NAME% >nul 2>&1
    echo 🗑️  Eliminando contenedor %CONTAINER_NAME%...
    docker rm %CONTAINER_NAME% >nul 2>&1
    echo ✅ Contenedor eliminado
) ELSE (
    echo ℹ️  No hay contenedor existente para eliminar
)
echo.

REM Eliminar imagen si existe
echo ================================
echo   Eliminando imagen anterior
echo ================================
docker image inspect %IMAGE_NAME% >nul 2>&1
IF NOT ERRORLEVEL 1 (
    echo 🗑️  Eliminando imagen %IMAGE_NAME%...
    docker rmi %IMAGE_NAME% >nul 2>&1
    IF ERRORLEVEL 1 (
        echo ⚠️  No se pudo eliminar la imagen (puede estar en uso)
        echo 💡 Continuando de todas formas...
    ) ELSE (
        echo ✅ Imagen eliminada
    )
) ELSE (
    echo ℹ️  No hay imagen existente para eliminar
)
echo.

REM Verificar puertos
echo ================================
echo   Verificando puertos
echo ================================
SET PORT_BUSY=0

netstat -an | findstr ":%PORT_STREAMLIT%" >nul 2>&1
IF NOT ERRORLEVEL 1 (
    SET PORT_BUSY=1
    echo ⚠️  Puerto %PORT_STREAMLIT% esta ocupado.
)

docker ps --format "{{.Ports}}" | findstr ":%PORT_STREAMLIT%" >nul 2>&1
IF NOT ERRORLEVEL 1 (
    SET PORT_BUSY=1
    echo ⚠️  Puerto %PORT_STREAMLIT% esta ocupado por otro contenedor.
)

IF %PORT_BUSY%==1 (
    echo ❌ No se puede iniciar: el puerto %PORT_STREAMLIT% esta en uso.
    echo 💡 Cierra la aplicacion que esta usando el puerto o cambia PORT_STREAMLIT en este script.
    pause
    exit /b 1
)

echo ✅ Puertos disponibles
echo.

REM Construir nueva imagen
echo ================================
echo   Construyendo nueva imagen Docker
echo   (esto puede tomar varios minutos...)
echo ================================
docker build -t %IMAGE_NAME% .

IF ERRORLEVEL 1 (
    echo ❌ Error al construir la imagen Docker.
    echo 💡 Revisa los mensajes de error arriba.
    pause
    exit /b 1
)

echo ✅ Imagen construida exitosamente
echo.

REM Crear y ejecutar contenedor
echo ================================
echo   Iniciando contenedor con Streamlit
echo ================================
echo.
echo 🚀 El contenedor se esta iniciando...
echo 📱 Streamlit estara disponible en: http://localhost:%PORT_STREAMLIT%
echo.
echo 💡 Presiona Ctrl+C para detener el contenedor cuando termines.
echo.

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
