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
    locales \
    && rm -rf /var/lib/apt/lists/*

# Generar locale argentino solo para LibreOffice
RUN locale-gen es_AR.UTF-8

# Configurar LibreOffice para usar locale argentino
RUN mkdir -p /root/.config/libreoffice/4/user/
RUN echo '<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/DateFormat/Default"><prop oor:name="DateOrder" oor:op="fuse"><value>1</value></prop></item><item oor:path="/org.openoffice.Office.Common/DateFormat/Default"><prop oor:name="DateSeparator" oor:op="fuse"><value>/</value></prop></item></oor:items>' > /root/.config/libreoffice/4/user/registrymodifications.xcu

# Crear script wrapper para LibreOffice con locale argentino
RUN echo '#!/bin/bash\nLANG=es_AR.UTF-8 LC_TIME=es_AR.UTF-8 libreoffice "$@"' > /usr/local/bin/libreoffice-arg
RUN chmod +x /usr/local/bin/libreoffice-arg

COPY requirements.txt .
RUN pip install -r requirements.txt jupyterlab streamlit

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8501 8888

CMD ["bash"]

