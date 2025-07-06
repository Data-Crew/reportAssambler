#!/bin/bash
# restart.sh
#
# Reinicia (o crea si no existe) un contenedor Docker llamado "reportassambler_container"
# basado en la imagen "reportassambler", montando el directorio actual como volumen.
#
# Uso:
#   ./restart.sh
#
# Antes de ejecutarlo, asegurate de dar permisos de ejecución con:
#   chmod +x restart.sh

IMAGE_NAME="reportassambler"
CONTAINER_NAME="reportassambler_container"

echo "==============================="
echo "  Verificando Docker"
echo "==============================="
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado o no está en el PATH."
    exit 1
fi

echo
echo "==============================="
echo "  Verificando imagen existente"
echo "==============================="
if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo "❌ La imagen $IMAGE_NAME no existe. Debes ejecutarlo con start.sh al menos una vez."
    exit 1
fi

echo
echo "==============================="
echo "  Verificando contenedor existente"
echo "==============================="
if ! docker container inspect "$CONTAINER_NAME" > /dev/null 2>&1; then
    echo "❗ No hay un contenedor con nombre $CONTAINER_NAME. Se creará uno nuevo."
    docker run -it --name "$CONTAINER_NAME" \
        -v "$(pwd):/app" \
        -p 8501:8501 \
        -p 8888:8888 \
        "$IMAGE_NAME"
    exit 0
fi

# Verificamos si está corriendo
RUNNING=$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME")

if [ "$RUNNING" = "true" ]; then
    echo "✅ El contenedor ya está en ejecución."
    exit 0
else
    echo "🔄 Iniciando contenedor detenido..."
    docker start -ai "$CONTAINER_NAME"
fi

echo
echo "==============================="
echo "  Contenedor detenido"
echo "==============================="
