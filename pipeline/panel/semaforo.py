"""
pipeline.panel.semaforo — Semáforo horizontal de actividad reciente por centro.

Componente estrella del Panel de gestión. Grid de 11 columnas con un cuadrado
por centro, coloreado según los días desde el último registro TOP.

Colores (definidos en config.py):
  - Verde   : 0-14  días → activo
  - Amarillo: 15-44 días → atrasado
  - Rojo    : 45+   días → inactivo
  - Gris    : sin registros (centro configurado pero sin actividad)

Layout:
  - Máximo 11 columnas
  - N centros → ceil(N/11) filas
  - Aspect ratio 1:1 por celda
  - Código del centro visible dentro del cuadro
  - Tooltip con detalle al pasar el mouse

Función expuesta:
  render(df, pais, centro_id=None)
"""
import math
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import (
    actividad_por_centro,
    color_semaforo,
    etiqueta_semaforo,
    COLOR_VERDE, COLOR_AMARILLO, COLOR_ROJO, COLOR_GRIS,
)


COLS_POR_FILA = 11


def render(df, pais, centro_id=None):
    """
    Pinta el semáforo horizontal.

    Args:
        df: DataFrame del país (columnas 'centro' y 'fecha_entrevista')
        pais: nombre del país (usado en título)
        centro_id: si viene con valor, resalta ese centro. Por ahora no filtra.
    """
    st.markdown(
        '<div class="sec">🚦 Actividad reciente por centro</div>',
        unsafe_allow_html=True
    )

    actividad = actividad_por_centro(df)

    if actividad.empty:
        st.info('ℹ Aún no hay centros con registros para este país.')
        return

    # Preparar datos para el grid
    n_centros  = len(actividad)
    n_filas    = math.ceil(n_centros / COLS_POR_FILA)
    n_cols_uso = min(n_centros, COLS_POR_FILA)

    # Coordenadas y estilo por centro
    xs, ys, colores, textos, hovers = [], [], [], [], []
    for i, row in actividad.iterrows():
        col = i % COLS_POR_FILA
        fila = i // COLS_POR_FILA
        xs.append(col)
        ys.append(-fila)   # negativo para que la fila 0 quede arriba
        color = color_semaforo(row['dias'])
        colores.append(color)
        textos.append(row['centro'])

        etiq = etiqueta_semaforo(row['dias'])
        dias_val = row['dias']
        tiene_fecha = pd.notna(row['ultima_fecha']) and pd.notna(dias_val)
        if tiene_fecha:
            fecha_str = row['ultima_fecha'].strftime('%d/%m/%Y')
            dias_str  = f"{int(dias_val)} días"
        else:
            fecha_str = '—'
            dias_str  = 'sin datos'

        hovers.append(
            f"<b>{row['centro']}</b><br>"
            f"Último registro: {fecha_str}<br>"
            f"Días transcurridos: {dias_str}<br>"
            f"Registros totales: {int(row['n_registros'])}<br>"
            f"Estado: <b>{etiq}</b>"
        )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode='markers+text',
        marker=dict(
            symbol='square',
            size=70,
            color=colores,
            line=dict(color='white', width=3),
        ),
        text=textos,
        textposition='middle center',
        textfont=dict(color='white', size=13, family='Arial Black'),
        hovertext=hovers,
        hoverinfo='text',
        showlegend=False,
    ))

    # Altura dinámica: 90 px por fila + márgenes
    alto = max(140, n_filas * 90 + 40)

    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            visible=False,
            range=[-0.5, COLS_POR_FILA - 0.5],
            fixedrange=True,
        ),
        yaxis=dict(
            visible=False,
            range=[-n_filas + 0.5, 0.5],
            scaleanchor='x',
            scaleratio=1,
            fixedrange=True,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Leyenda con conteo por estado
    verdes    = sum(1 for c in colores if c == COLOR_VERDE)
    amarillos = sum(1 for c in colores if c == COLOR_AMARILLO)
    rojos     = sum(1 for c in colores if c == COLOR_ROJO)
    grises    = sum(1 for c in colores if c == COLOR_GRIS)

    lg1, lg2, lg3, lg4, lg5 = st.columns([1, 1, 1, 1, 2])
    with lg1:
        st.markdown(
            f'<div style="text-align:center;font-size:.82rem;">'
            f'<span style="display:inline-block;width:12px;height:12px;background:{COLOR_VERDE};'
            f'border-radius:3px;margin-right:5px;vertical-align:middle;"></span>'
            f'Activos (0-14 días): <b>{verdes}</b></div>',
            unsafe_allow_html=True
        )
    with lg2:
        st.markdown(
            f'<div style="text-align:center;font-size:.82rem;">'
            f'<span style="display:inline-block;width:12px;height:12px;background:{COLOR_AMARILLO};'
            f'border-radius:3px;margin-right:5px;vertical-align:middle;"></span>'
            f'Atrasados (15-44): <b>{amarillos}</b></div>',
            unsafe_allow_html=True
        )
    with lg3:
        st.markdown(
            f'<div style="text-align:center;font-size:.82rem;">'
            f'<span style="display:inline-block;width:12px;height:12px;background:{COLOR_ROJO};'
            f'border-radius:3px;margin-right:5px;vertical-align:middle;"></span>'
            f'Inactivos (45+): <b>{rojos}</b></div>',
            unsafe_allow_html=True
        )
    with lg4:
        if grises > 0:
            st.markdown(
                f'<div style="text-align:center;font-size:.82rem;">'
                f'<span style="display:inline-block;width:12px;height:12px;background:{COLOR_GRIS};'
                f'border-radius:3px;margin-right:5px;vertical-align:middle;"></span>'
                f'Sin datos: <b>{grises}</b></div>',
                unsafe_allow_html=True
            )
    with lg5:
        st.markdown(
            f'<div style="text-align:right;font-size:.75rem;color:#666;">'
            f'Total centros: <b>{n_centros}</b> · Fecha de corte: hoy</div>',
            unsafe_allow_html=True
        )
