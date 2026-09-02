# QALAT · Sistema de Monitoreo de Resultados de Tratamiento
## App de análisis automático TOP / IRT

### Qué formulario corresponde a cada país

**`index.html` es el formulario de Perú.** No se llama `index_peru.html`. Perú
fue el primer país y quedó como página raíz del sitio; los centros peruanos
tienen esa URL guardada por fuera, así que renombrarla los dejaría sin acceso.

| Archivo | País | Tipo |
|---|---|---|
| `index.html` | **Perú** | Ingreso y seguimiento |
| `index_ecuador.html` | Ecuador | Ingreso y seguimiento |
| `index_elsalvador.html` | El Salvador | Ingreso y seguimiento |
| `index_mexico.html` | México | Ingreso y seguimiento |
| `index_mexicocij.html` | México · CIJ | Ingreso y seguimiento |
| `index_montefenix.html` | México · Monte Fénix | Ingreso y seguimiento |
| `index_mahanaim.html` | México · Mahanaim | Ingreso y seguimiento |
| `correccion_top_peru.html` | Perú | Corrección de registros |
| `correccion_top_ecuador.html` | Ecuador | Corrección de registros |
| `correccion_top_elsalvador.html` | El Salvador | Corrección de registros |
| `correccion_top_mexico.html` | México | Corrección de registros |
| `correccion_top_mexicocij.html` | México · CIJ | Corrección de registros |
| `correccion_top_montefenix.html` | México · Monte Fénix | Corrección de registros |
| `correccion_top_mahanaim.html` | México · Mahanaim | Corrección de registros |

Cualquier cambio a un formulario de ingreso son **siete archivos**, y el de
Perú es el que se olvida.

### Cómo instalar y correr (computador local)

#### 1. Instalar Python
Si no tienes Python, descárgalo de https://www.python.org (versión 3.10 o superior)

#### 2. Instalar dependencias
Abre la terminal (o cmd en Windows), navega a esta carpeta y ejecuta:
```
pip install -r requirements.txt
```

#### 3. Correr la app
```
streamlit run app.py
```
Se abre automáticamente en el navegador en http://localhost:8501

---

### Cómo publicar en la web (Streamlit Cloud) — gratis

1. Sube esta carpeta a un repositorio GitHub
2. Ve a https://share.streamlit.io
3. Conecta tu repositorio
4. Selecciona `app.py` como archivo principal
5. Clic en Deploy

La app queda disponible en una URL pública que puedes compartir con los países.

---

### Estructura
```
qalat_app/
├── app.py                  # Interfaz Streamlit
├── pipeline/
│   ├── wide_top.py         # Motor TOP (basado en SCRIPT_TOP_Universal_Wide_v3_6)
│   └── wide_irt.py         # Motor IRT (próxima versión)
├── requirements.txt
└── README.md
```

---

### Qué genera la app

| Output | Formato | Descripción |
|--------|---------|-------------|
| Base Wide | Excel (.xlsx) | 6 hojas: Base Wide · Resumen · Alertas · Calidad · Por Centro · Pendientes |
| Gráficos | PNG | Seguimiento · Semáforo · Sustancia principal |
| Pendientes | CSV | Lista de pacientes con TOP2 urgente o próximo |

---

### Versiones futuras
- [ ] Módulo IRT
- [ ] Reporte PDF automático
- [ ] Presentación PPT automática
- [ ] Tablero comparativo entre países
- [ ] Login por país

---
Desarrollado para Proyecto QALAT · UNODC · 2026
