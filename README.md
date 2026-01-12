# Report Assambler

Este proyecto contiene una herramienta de ensamblado de informes médicos desarrollada en Python y ejecutable desde Docker. Incluye una aplicación web desarrollada con Streamlit y un entorno de desarrollo con JupyterLab.

## Características

- **Compilador de Informes Médicos**: Ensambla automáticamente estudios médicos por paciente (laboratorio, ECG, RX, EEG, etc.)
- **Clasificador de Laboratorios**: Analiza PDFs de laboratorio para detectar valores fuera de rango de referencia
- **Interfaz Web**: Aplicación Streamlit con selector de herramientas
- **Entorno de Desarrollo**: JupyterLab integrado para análisis y desarrollo

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

* Verifica si el contenedor ya existe y está corriendo (evita reconstrucciones innecesarias)
* Si el contenedor existe pero está detenido, lo inicia automáticamente
* Solo construye la imagen Docker si el contenedor no existe
* Verifica conflictos de puertos antes de crear/iniciar el contenedor
* Mapea los puertos necesarios (8501 para Streamlit, 8889 para JupyterLab)

> **Nota:** El puerto de JupyterLab es 8889 (no 8888) para evitar conflictos con otros contenedores.

#### Uso en Windows

En Windows podés ejecutar `start.bat` haciendo doble click sobre el archivo, o abriendo una terminal (desde PowerShell o CMD) y navegando al directorio del proyecto:

```cmd
start.bat
```

Este script tiene las mismas funcionalidades que `start.sh`:

* Verifica si el contenedor ya existe y está corriendo (evita reconstrucciones innecesarias)
* Si el contenedor existe pero está detenido, lo inicia automáticamente
* Solo construye la imagen Docker si el contenedor no existe
* Verifica conflictos de puertos antes de crear/iniciar el contenedor
* Mapea los puertos necesarios (8501 para Streamlit, 8889 para JupyterLab)

> **Requisito:** asegurate de tener **Docker Desktop para Windows** instalado y funcionando antes de usar este script.
> Podés descargarlo desde: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)

Una vez instalado, Docker debe estar corriendo en segundo plano (verificá que el icono de Docker esté activo en la barra de tareas).

#### Reiniciar el Contenedor en Windows

Si necesitás reiniciar el contenedor sin reconstruir la imagen en Windows:

```cmd
restart.bat
```

O manualmente desde PowerShell o CMD:

```cmd
docker restart reportassambler_container
```

### 3. Iniciar los servicios

Cuando el contenedor se inicia, verás un menú interactivo. El contenedor puede ejecutar **dos servicios**:

- **Streamlit**: Aplicación web con el Compilador de Informes y el Clasificador de Laboratorios
- **JupyterLab**: Entorno de desarrollo interactivo para análisis y notebooks

El menú te permite elegir cómo iniciarlos:

```
==========================================
  Report Assambler - Inicio de Servicios
==========================================

Este contenedor puede ejecutar dos servicios:
  • Streamlit: Aplicación web (Compilador y Clasificador)
  • JupyterLab: Entorno de desarrollo interactivo

¿Qué querés hacer?

1) Iniciar solo Streamlit
2) Iniciar solo JupyterLab
3) Iniciar ambos servicios (Streamlit + JupyterLab)
4) Entrar al shell sin iniciar servicios
```

**Opciones del menú:**

- **Opción 1**: Inicia solo Streamlit
  - Accedé en: `http://localhost:8501`
  - Útil cuando solo necesitás usar la aplicación web
  
- **Opción 2**: Inicia solo JupyterLab
  - Accedé en: `http://localhost:8889`
  - Útil cuando solo necesitás trabajar con notebooks
  - > **Nota:** El puerto externo es 8889, pero dentro del contenedor JupyterLab corre en 8888.

- **Opción 3**: Inicia ambos servicios simultáneamente
  - Streamlit: `http://localhost:8501`
  - JupyterLab: `http://localhost:8889`
  - Presioná `Ctrl+C` para detener ambos servicios
  - Útil cuando querés usar ambos servicios al mismo tiempo

- **Opción 4**: Entra al shell sin iniciar servicios
  - Útil si querés ejecutar comandos manualmente, hacer debugging, o ejecutar tests
  - Podés iniciar los servicios manualmente después si lo necesitás

#### Iniciar servicios manualmente (si elegiste opción 4)

Si elegiste la opción 4 o necesitás iniciar servicios manualmente:

**Streamlit:**
```bash
streamlit run app/streamlit_launcher.py --server.port 8501 --server.address 0.0.0.0
```

**JupyterLab:**
```bash
jupyter lab --ip=0.0.0.0 --port=8888 --allow-root --NotebookApp.token=''
```

### Uso de las Herramientas

Una vez que accedas a Streamlit, verás un selector de herramientas en el sidebar:

#### Compilador de Informes Médicos
1. Seleccioná la fecha de compilación desde el sidebar
2. Elegí si querés compilar para todos los pacientes o uno solo
3. Hacé click en **"Discriminar estudios por paciente"** para separar los PDFs generales
4. Hacé click en **"Compilar resultados por paciente"** para generar los informes finales

#### Clasificador de Laboratorios
1. Seleccioná "Clasificador de Laboratorios" en el selector de herramientas
2. Elegí la fecha y el paciente desde los dropdowns
3. Hacé click en **"Analizar laboratorio"** para detectar valores fuera de rango
4. Revisá los resultados:
   - Métricas resumen (total parámetros, fuera de rango, porcentajes)
   - Tabla con valores fuera de rango (si los hay)
   - Tabla expandible con todos los parámetros
   - Opción de descargar resultados en CSV

### Reiniciar el Contenedor

Si necesitás reiniciar el contenedor sin reconstruir la imagen:

**En Linux/Mac:**
```bash
./restart.sh
```

**En Windows:**
```cmd
restart.bat
```

**O manualmente (funciona en ambos sistemas):**
```bash
docker restart reportassambler_container
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


## Estructura del Proyecto

```
reportAssambler/
├── app/
│   ├── streamlit_launcher.py    # Aplicación principal Streamlit
│   ├── report_assembler.py       # Lógica del compilador
│   ├── converters.py             # Utilidades de conversión
│   ├── lab_extractor.py          # Extracción de datos de PDFs de laboratorio
│   ├── lab_ranges.py             # Gestión de rangos de referencia
│   └── lab_analyzer.py           # Análisis de valores fuera de rango
├── config/
│   └── lab_ranges.json           # Configuración de rangos de referencia
├── DATA/                         # Datos de entrada (PDFs, Excel)
├── OUTPUT/                       # Informes compilados generados
├── tests/                        # Tests unitarios
├── start.sh                      # Script de inicio (Linux/Mac)
├── start.bat                     # Script de inicio (Windows)
└── restart.sh                    # Script de reinicio rápido
```

## Configuración de Rangos de Laboratorio

Los rangos de referencia para el clasificador de laboratorios se configuran en `config/lab_ranges.json`. 

Para agregar o modificar rangos, editá el archivo JSON con la siguiente estructura:

```json
{
  "NOMBRE_PARAMETRO": {
    "min": 0.0,
    "max": 100.0,
    "unidad": "mg/dL",
    "sinonimos": ["SINONIMO1", "SINONIMO2"]
  }
}
```

Los sinónimos permiten que el sistema reconozca diferentes nombres para el mismo parámetro (ej: "GLUCOSA", "GLUCEMIA", "GLUC").

## Tests

Para ejecutar los tests desde el contenedor, desde el directorio `tests/`:

```bash
pytest -s test_assembler.py
```

## Troubleshooting

### Puerto ocupado
Si recibís un error de puerto ocupado:
- Verificá qué contenedor está usando el puerto: `docker ps`
- Detené el contenedor conflictivo o cambiá los puertos en `start.sh`

### Contenedor no inicia
Si el contenedor no inicia correctamente:
- Verificá que Docker esté corriendo: `docker ps`
- Remové el contenedor viejo: `docker rm reportassambler_container`
- Ejecutá `./start.sh` nuevamente

### No se encuentran parámetros en el PDF
Si el clasificador no encuentra parámetros:
- Verificá que el PDF no esté escaneado (debe tener texto seleccionable)
- El formato del PDF puede requerir ajustes en el parser (`app/lab_extractor.py`)
- Contactá al desarrollador para ajustar los patrones de extracción
