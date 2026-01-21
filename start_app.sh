#!/bin/bash
# Script de inicio para el contenedor
# Permite iniciar Streamlit, JupyterLab, o ambos

echo "=========================================="
echo "  Report Assambler - Inicio de Servicios"
echo "=========================================="
echo ""
echo "Este contenedor puede ejecutar dos servicios:"
echo "  • Streamlit: Aplicación web (Compilador y Clasificador)"
echo "  • JupyterLab: Entorno de desarrollo interactivo"
echo ""
echo "¿Qué querés hacer?"
echo ""
echo "1) Iniciar solo Streamlit"
echo "2) Iniciar solo JupyterLab"
echo "3) Iniciar ambos servicios (Streamlit + JupyterLab)"
echo "4) Entrar al shell sin iniciar servicios"
echo ""
read -p "Elegí una opción (1-4): " opcion

case $opcion in
    1)
        echo ""
        echo "🚀 Iniciando Streamlit..."
        echo "📱 Accedé desde tu navegador en: http://localhost:8501"
        echo "⚠️  Presioná Ctrl+C para detener el servicio"
        echo ""
        streamlit run app/streamlit_launcher.py --server.port 8501 --server.address 0.0.0.0
        ;;
    2)
        echo ""
        echo "🚀 Iniciando JupyterLab..."
        echo "📱 Accedé desde tu navegador en: http://localhost:8889"
        echo "⚠️  Presioná Ctrl+C para detener el servicio"
        echo ""
        jupyter lab --ip=0.0.0.0 --port=8888 --allow-root --NotebookApp.token=''
        ;;
    3)
        echo ""
        echo "🚀 Iniciando ambos servicios..."
        echo "📱 Streamlit: http://localhost:8501"
        echo "📱 JupyterLab: http://localhost:8889"
        echo ""
        echo "⚠️  Presioná Ctrl+C para detener ambos servicios"
        echo ""
        # Iniciar Streamlit en background
        streamlit run app/streamlit_launcher.py --server.port 8501 --server.address 0.0.0.0 &
        STREAMLIT_PID=$!
        # Iniciar JupyterLab en foreground
        jupyter lab --ip=0.0.0.0 --port=8888 --allow-root --NotebookApp.token=''
        # Si JupyterLab se detiene, también detener Streamlit
        kill $STREAMLIT_PID 2>/dev/null
        ;;
    4)
        echo ""
        echo "💻 Entrando al shell interactivo..."
        echo ""
        echo "💡 Comandos útiles:"
        echo "   • Iniciar Streamlit:"
        echo "     streamlit run app/streamlit_launcher.py --server.port 8501 --server.address 0.0.0.0"
        echo ""
        echo "   • Iniciar JupyterLab:"
        echo "     jupyter lab --ip=0.0.0.0 --port=8888 --allow-root --NotebookApp.token=''"
        echo ""
        echo "   • Ejecutar tests:"
        echo "     cd tests && pytest -s test_assembler.py"
        echo ""
        exec bash
        ;;
    *)
        echo ""
        echo "❌ Opción inválida. Iniciando shell..."
        exec bash
        ;;
esac

