#!/bin/bash
# rebuild.sh
#
# Reconstruye la imagen Docker desde cero eliminando contenedor e imagen anteriores.
# Útil después de actualizar el código desde GitHub o cuando necesitás asegurarte
# de que la imagen tenga los últimos cambios.
#
# Uso:
#   ./rebuild.sh
#
# Antes de ejecutarlo, asegurate de dar permisos de ejecución con:
#   chmod +x rebuild.sh

IMAGE_NAME="reportassambler"
CONTAINER_NAME="reportassambler_container"
PORT_STREAMLIT=8501
PORT_JUPYTER=8889

echo "==============================="
echo "  REBUILD - Report Assembler"
echo "==============================="
echo ""
echo "Este script va a:"
echo "  1. Detener y eliminar el contenedor anterior"
echo "  2. Eliminar la imagen anterior"
echo "  3. Reconstruir la imagen con los últimos cambios"
echo "  4. Iniciar el contenedor con Streamlit"
echo ""

echo "==============================="
echo "  Verificando Docker"
echo "==============================="
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado o no está en el PATH."
    exit 1
fi

echo "✅ Docker está disponible"
echo ""

# Detener y eliminar contenedor si existe
echo "==============================="
echo "  Limpiando contenedor anterior"
echo "==============================="
if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
    echo "🔄 Deteniendo contenedor $CONTAINER_NAME..."
    docker stop $CONTAINER_NAME > /dev/null 2>&1
    echo "🗑️  Eliminando contenedor $CONTAINER_NAME..."
    docker rm $CONTAINER_NAME > /dev/null 2>&1
    echo "✅ Contenedor eliminado"
else
    echo "ℹ️  No hay contenedor existente para eliminar"
fi
echo ""

# Eliminar imagen si existe
echo "==============================="
echo "  Eliminando imagen anterior"
echo "==============================="
if docker image inspect $IMAGE_NAME > /dev/null 2>&1; then
    echo "🗑️  Eliminando imagen $IMAGE_NAME..."
    docker rmi $IMAGE_NAME > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "⚠️  No se pudo eliminar la imagen (puede estar en uso)"
        echo "💡 Continuando de todas formas..."
    else
        echo "✅ Imagen eliminada"
    fi
else
    echo "ℹ️  No hay imagen existente para eliminar"
fi
echo ""

# Verificar puertos
echo "==============================="
echo "  Verificando puertos"
echo "==============================="
PORT_BUSY=false

if lsof -i :$PORT_STREAMLIT >/dev/null 2>&1 || docker ps --format "{{.Ports}}" | grep -q ":$PORT_STREAMLIT"; then
    PORT_BUSY=true
    echo "⚠️  Puerto $PORT_STREAMLIT está ocupado."
fi

if [ "$PORT_BUSY" = true ]; then
    echo "❌ No se puede iniciar: el puerto $PORT_STREAMLIT está en uso."
    echo "💡 Cierra la aplicación que está usando el puerto o cambia PORT_STREAMLIT en este script."
    exit 1
fi

echo "✅ Puertos disponibles"
echo ""

# Construir nueva imagen
echo "==============================="
echo "  Construyendo nueva imagen Docker"
echo "  (esto puede tomar varios minutos...)"
echo "==============================="
docker build -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo "❌ Error al construir la imagen Docker."
    echo "💡 Revisa los mensajes de error arriba."
    exit 1
fi

echo "✅ Imagen construida exitosamente"
echo ""

# Crear y ejecutar contenedor
echo "==============================="
echo "  Iniciando contenedor con Streamlit"
echo "==============================="
echo ""
echo "🚀 El contenedor se está iniciando..."
echo "📱 Streamlit estará disponible en: http://localhost:$PORT_STREAMLIT"
echo ""
echo "💡 Presiona Ctrl+C para detener el contenedor cuando termines."
echo ""

docker run -it --name $CONTAINER_NAME \
    -v "$PWD":/app \
    -p $PORT_STREAMLIT:8501 \
    -p $PORT_JUPYTER:8888 \
    $IMAGE_NAME

echo ""
echo "==============================="
echo "  Contenedor detenido"
echo "==============================="
