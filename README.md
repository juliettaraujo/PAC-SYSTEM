# Sistema de Administración de Carga (P.A.C.) - CED Barinas

Sistema web diseñado para la gestión, monitoreo y registro histórico de las maniobras operativas de los circuitos eléctricos correspondientes al Centro Estadal de Despacho (CED) Barinas - CORPOELEC. 

El sistema optimiza el flujo de trabajo de los operadores al eliminar cálculos manuales, previniendo errores humanos en el conteo de la carga administrada (MW) y automatizando los reportes de maniobras.

## 🛠️ Tecnologías y Arquitectura

* **Backend:** Python 3 con Flask.
* **Base de Datos:** SQLite3 (Persistencia ligera y rápida sin servidores externos).
* **Frontend:** HTML5, Tailwind CSS (vía CDN) para el diseño responsivo, y JavaScript puro (Vanilla JS) para el filtrado en tiempo real.
* **Exportación de Datos:** Integración con `openpyxl` para la generación automática de reportes en formato `.xlsx`.

## 📂 Estructura del Proyecto

```text
/PAC_SYSTEM
├── app.py                 # Enrutador principal e inicialización del servidor Flask
├── backend.py             # Lógica de negocio, cálculos de tiempo y carga (MW)
├── database.py            # Script de inicialización de tablas y conexión a SQLite
├── models.py              # Definición de clases y constructores (Ej. Circuit)
├── requirements.txt       # Dependencias exactas de Python para el proyecto
├── /data                  # Almacenamiento local de la base de datos (circuits.db)
├── /static                # Archivos estáticos (Hojas de estilo CSS, Scripts JS e Imágenes)
└── /templates             # Vistas de la aplicación (HTML) y componentes modulares


🚀 Guía de Instalación y Despliegue Local
Siga estos pasos para levantar el servidor de desarrollo en un entorno local.

1. Clonar o descargar el repositorio
Asegúrese de ubicar la carpeta del proyecto en su directorio de preferencia y abra una terminal (Símbolo del sistema o PowerShell) dentro de esa ruta.

2. Crear y activar el entorno virtual
Es una buena práctica de ingeniería aislar las dependencias del proyecto.

Crear entorno:

Bash
python -m venv venv
Activar entorno (Windows):

PowerShell
.\venv\Scripts\activate
3. Instalar las dependencias
Con el entorno virtual activo (se indicará con un (venv) al inicio de su consola), ejecute el siguiente comando para instalar Flask y los gestores de Excel:

Bash
pip install -r requirements.txt
4. Ejecutar la aplicación
Inicie el servidor web ejecutando el archivo principal:

Bash
python app.py
La consola indicará que el servidor está corriendo. Abra su navegador web e ingrese a http://127.0.0.1:5000/ para acceder a la interfaz del monitor principal.

⚙️ Funcionalidades Principales
Monitor en Tiempo Real: Visualización y filtrado dinámico de circuitos segmentados por bloques (A, B, C, D) y estados operativos (Activo, PAC, Falla, Mantenimiento).

Cálculo Automático de MW: Cuantificación instantánea de la demanda afectada en base a los amperajes ingresados y los niveles de tensión (13.8kV / 34.5kV).

Gestión de Turnos: Botón de cambio de guardia que archiva parámetros pasados y prepara el entorno para el nuevo equipo de operadores.

Historial y Exportación: Trazabilidad estricta de maniobras con capacidad de exportación a hojas de cálculo para su posterior análisis corporativo.