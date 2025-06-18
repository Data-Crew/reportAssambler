# Report Assambler

Este proyecto contiene una herramienta de ensamblado de informes médicos desarrollada en Python y ejecutable desde Docker. Incluye una aplicación web desarrollada con Streamlit y un entorno de desarrollo con JupyterLab.

---

## Instrucciones de uso

### 1. Hacer ejecutable el script de inicio (solo necesario en sistemas Unix)

```bash
chmod +x start.sh
```

### 2. Ejecutar el contenedor Docker

```bash
./start.sh
```

Este script:

* Libera el puerto 8501 (Streamlit) si está en uso.
* Construye la imagen Docker.
* Elimina un contenedor anterior si existe.
* Levanta un nuevo contenedor con los puertos necesarios mapeados.

#### Uso en Windows

En Windows podés ejecutar `start.bat` haciendo doble click sobre el archivo, o abriendo una terminal (desde PowerShell o CMD) y navegando al directorio del proyecto:


<pre lang="markdown"> ```cmd start.bat ``` </pre>

**Requisito:** debes de tener Docker Desktop para Windows instalado y funcionando antes de usar este script.
Podés descargarlo desde: https://www.docker.com/products/docker-desktop/

### 3. Acceder a los entornos dentro del contenedor

#### JupyterLab

```bash
jupyter lab --ip=0.0.0.0 --port=8888 --allow-root --NotebookApp.token=''
```

Accedé desde tu navegador a:

```
http://localhost:8888
```

#### Streamlit

```bash
streamlit run app/streamlit_launcher.py --server.port 8501 --server.address 0.0.0.0
```

Accedé desde tu navegador a:

```
http://localhost:8501
```

---

## Estructura esperada del directorio `DATA/`

La estructura de `DATA/` debe organizarse por fecha de procesamiento. Por ejemplo:

```
DATA/
└── 20-05-2025/
    ├── AUDIOMETRIA 20.05.25.pdf
    ├── ECG 20-05-2025.pdf
    ├── EEG 20-5-25.pdf
    ├── ESPIROMETRIA 20-5-25.pdf
    ├── LABORATORIO 20-5-25.pdf
    ├── PSICOS 20-5-25.pdf
    ├── RX 20-05-2025.pdf
    └── 20-05-2025/  ← subdirectorio con el mismo nombre de la fecha
        ├── control.xlsx        ← tokens de estudios por paciente
        ├── paciente_01_RX.pdf ← pdfs individuales por paciente
        ├── paciente_01_LAB.pdf
        └── ...
```

* Los archivos PDF principales (RX, laboratorio, etc.) deben estar nombrados según el tipo de estudio y la fecha.
* El subdirectorio con el mismo nombre de la fecha **debe existir**, y es donde se almacenan:

  * las portadas de los reportes generados
  * el archivo de control (`control.xlsx`)
  * los resultados parciales de estudios fraccionados por paciente


## Tests

Para ejecutar los tests desde el contenedor, desde el directorio `tests/`:

```bash
pytest -s test_assembler.py
```