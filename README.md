Instrucciones

* Pasos

1. Hacer el script de inicio ejecutable:

```bash
chmod +x start.sh
```

2. Iniciar el contenedor:

```bash
./start.sh
```

3. 


* Iniciar Jupyterlab dentro del contenedor

jupyter lab --ip=0.0.0.0 --port=8888 --allow-root --NotebookApp.token=''

Accedé en el navegador a: http://localhost:8888


* Iniciar Streamlit dentro del contenedor

```bash
streamlit run app/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```
