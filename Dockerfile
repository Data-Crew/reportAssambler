FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libreoffice \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt jupyterlab streamlit

COPY . .

ENV PYTHONPATH=/app


EXPOSE 8501 8888

CMD ["bash"]

