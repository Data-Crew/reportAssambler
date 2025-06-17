#!/bin/bash

IMAGE_NAME="reportassambler"
CONTAINER_NAME="reportassambler_container"
PORT_STREAMLIT=8501
PORT_JUPYTER=8888

echo "🧼 Checking if port $PORT_STREAMLIT is already in use..."
if lsof -i :$PORT_STREAMLIT >/dev/null; then
  PID=$(lsof -ti :$PORT_STREAMLIT)
  echo "🔌 Port $PORT_STREAMLIT is busy (PID $PID). Killing process..."
  kill -9 $PID
  echo "✅ Freed port $PORT_STREAMLIT."
fi

echo "🐳 Building Docker image..."
docker build -t $IMAGE_NAME .

echo "🗑️ Removing previous container if it exists..."
docker rm -f $CONTAINER_NAME 2>/dev/null

echo "🚀 Running Docker container..."
docker run -it --name $CONTAINER_NAME \
  -v "$PWD":/app \
  -p $PORT_STREAMLIT:8501 \
  -p $PORT_JUPYTER:8888 \
  $IMAGE_NAME

