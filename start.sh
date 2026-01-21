#!/bin/bash

IMAGE_NAME="reportassambler"
CONTAINER_NAME="reportassambler_container"
PORT_STREAMLIT=8501
PORT_JUPYTER=8889  # Cambiado de 8888 a 8889 para evitar conflicto con cropclassifier

# Verificar si el contenedor ya existe y está corriendo
if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
  echo "✅ Container $CONTAINER_NAME is already running."
  echo "💡 To restart, use: docker restart $CONTAINER_NAME"
  exit 0
fi

# Verificar si el contenedor existe pero está detenido
if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
  echo "🔄 Container $CONTAINER_NAME exists but is stopped."
  
  # Verificar si los puertos están ocupados
  PORT_STREAMLIT_BUSY=false
  PORT_JUPYTER_BUSY=false
  
  if lsof -i :$PORT_STREAMLIT >/dev/null 2>&1 || docker ps --format "{{.Ports}}" | grep -q ":$PORT_STREAMLIT"; then
    PORT_STREAMLIT_BUSY=true
    echo "⚠️  Port $PORT_STREAMLIT is busy."
  fi
  
  if lsof -i :$PORT_JUPYTER >/dev/null 2>&1 || docker ps --format "{{.Ports}}" | grep -q ":$PORT_JUPYTER"; then
    PORT_JUPYTER_BUSY=true
    echo "⚠️  Port $PORT_JUPYTER is busy."
  fi
  
  if [ "$PORT_STREAMLIT_BUSY" = true ] || [ "$PORT_JUPYTER_BUSY" = true ]; then
    echo "❌ Cannot start container: ports are in use."
    echo "💡 Options:"
    echo "   1. Stop the container using the ports: docker stop <container_name>"
    echo "   2. Remove this container and recreate with different ports: docker rm $CONTAINER_NAME"
    echo "   3. Edit start.sh to use different ports"
    exit 1
  fi
  
  echo "🚀 Starting container..."
  docker start -ai $CONTAINER_NAME
  exit 0
fi

# Verificar puertos antes de construir
echo "🧼 Checking ports..."
PORT_STREAMLIT_BUSY=false
PORT_JUPYTER_BUSY=false

if lsof -i :$PORT_STREAMLIT >/dev/null 2>&1 || docker ps --format "{{.Ports}}" | grep -q ":$PORT_STREAMLIT"; then
  PORT_STREAMLIT_BUSY=true
  echo "⚠️  Port $PORT_STREAMLIT is busy."
fi

if lsof -i :$PORT_JUPYTER >/dev/null 2>&1 || docker ps --format "{{.Ports}}" | grep -q ":$PORT_JUPYTER"; then
  PORT_JUPYTER_BUSY=true
  echo "⚠️  Port $PORT_JUPYTER is busy."
fi

if [ "$PORT_STREAMLIT_BUSY" = true ] || [ "$PORT_JUPYTER_BUSY" = true ]; then
  echo "❌ Cannot create container: ports are in use."
  echo "💡 Options:"
  echo "   1. Stop containers using the ports"
  echo "   2. Edit start.sh to use different ports (change PORT_STREAMLIT and PORT_JUPYTER)"
  exit 1
fi

# Si no existe, construir imagen y crear contenedor
echo "🐳 Building Docker image (this may take a few minutes)..."
docker build -t $IMAGE_NAME .

echo "🚀 Running Docker container..."
docker run -it --name $CONTAINER_NAME \
  -v "$PWD":/app \
  -p $PORT_STREAMLIT:8501 \
  -p $PORT_JUPYTER:8888 \
  $IMAGE_NAME

