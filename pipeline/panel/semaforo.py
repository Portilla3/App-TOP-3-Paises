"""
pipeline.panel.semaforo — Semáforo horizontal de actividad reciente por centro.

Componente estrella del Panel de gestión. Grid de hasta 11 columnas con un
cuadrado por centro, coloreado según los días desde el último registro TOP.

Diseño según mockup aprobado:
  - Cuadros de proporción cuadrada, separados por espacio blanco
  - Colores suaves (verde #8BC34A, amarillo #F0A836, rojo #E15D5D, gris #B4BAC2)
  - Código del centro dentro del cuadro con fuente adaptativa
  - Tooltip con detalle al pasar el mouse
  - Leyenda estilo mockup con conteo por estado

Colores (definidos en config.py):
  - Verde   : 0-14  días → activo
  - Amarillo: 15-44 días → atrasado
  - Rojo    : 45+   días → inactivo
  - Gris    : sin registros

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
    prioridad_semaforo,
    titulo_seccion,
    COLOR_VERDE, COLOR_AMARILLO, COLOR_ROJO, COLOR_GRIS,
)


COLS_POR_FILA = 11


def _tamano_fuente(codigo):
    """Ajusta el tamaño de la fuente al largo del código para que quepa dentro."""
    n = len(str(codigo))
    if n <= 3:  return 15
    if n <= 4:  return 13
    if n <= 5:  return 12
    if n <= 6:  return 11
    if n <= 7:  return 10
    return 9


def render(df, pais, centro_id=None):
    """
    Pinta el semáforo horizontal.

    Args:
        df: DataFrame del país (columnas 'centro' y 'fecha_entrevista')
        pais: nombre del país (usado en título)
        centro_id: si viene con valor, resalta ese centro con borde grueso.
    """
    with st.container(border=True):
        st.markdown(
            titulo_seccion('🚦', 'Actividad reciente por centro',
                           'días desde el último registro TOP aplicado'),
            unsafe_allow_html=True
        )

        actividad = actividad_por_centro(df)

        if actividad.empty:
            st.info('ℹ Aún no hay centros con registros para este país.')
            return

        _pintar_grid_y_leyenda(actividad, centro_id)


def _pintar_grid_y_leyenda(actividad, centro_id):
    """Función interna: pinta el grid Plotly y la leyenda debajo."""

    n_centros = len(actividad)
    n_filas   = math.ceil(n_centros / COLS_POR_FILA)

    # Ordenar por prioridad de color (verde → amarillo → rojo → gris)
    # y dentro de cada grupo, por días ascendente (los más recientes primero).
    actividad = actividad.copy()
    actividad['_prio'] = actividad['dias'].apply(prioridad_semaforo)
    actividad['_dias_orden'] = actividad['dias'].fillna(999999)
    actividad = actividad.sort_values(
        by=['_prio', '_dias_orden', 'centro']
    ).reset_index(drop=True)

    # Cada cuadro ocupa una celda (col, fila). Margen mínimo para que estén casi pegados.
    MARGEN = 0.02

    fig = go.Figure()

    for i, row in actividad.iterrows():
        col  = i % COLS_POR_FILA
        fila = i // COLS_POR_FILA

        color = color_semaforo(row['dias'])
        codigo = str(row['centro'])

        x0 = col + MARGEN
        x1 = col + 1 - MARGEN
        y0 = -fila - 1 + MARGEN
        y1 = -fila - MARGEN

        # Borde: blanco por defecto, navy grueso si es el centro destacado
        borde_color = '#1F3864' if centro_id and codigo == str(centro_id).strip() else 'white'
        borde_ancho = 3 if centro_id and codigo == str(centro_id).strip() else 2

        fig.add_shape(
            type='rect',
            x0=x0, x1=x1, y0=y0, y1=y1,
            fillcolor=color,
            line=dict(color=borde_color, width=borde_ancho),
            layer='below',
        )

        fig.add_annotation(
            x=(x0 + x1) / 2,
            y=(y0 + y1) / 2,
            text=f'<b>{codigo}</b>',
            showarrow=False,
            font=dict(color='#1F1F1F', size=_tamano_fuente(codigo), family='Arial'),
        )

        # Punto invisible para tooltip. Solo muestra el código en grande.
        fig.add_trace(go.Scatter(
            x=[(x0 + x1) / 2],
            y=[(y0 + y1) / 2],
            mode='markers',
            marker=dict(size=45, color='rgba(0,0,0,0)'),
            hovertext=[f'<b>{codigo}</b>'],
            hoverinfo='text',
            hoverlabel=dict(
                bgcolor=color,
                bordercolor='white',
                font=dict(size=20, color='#1F1F1F', family='Arial'),
            ),
            showlegend=False,
        ))

    # Altura más compacta (Rodrigo pidió menos espacio vertical)
    alto = max(120, n_filas * 82 + 12)

    # Usar el número real de columnas ocupadas (no 11 fijo) para que los cuadros
    # ocupen todo el ancho disponible cuando el país tiene pocos centros.
    n_cols_uso = min(n_centros, COLS_POR_FILA)

    fig.update_layout(
        height=alto,
        margin=dict(l=6, r=6, t=6, b=6),
        xaxis=dict(
            visible=False,
            range=[-0.05, n_cols_uso + 0.05],
            fixedrange=True,
        ),
        yaxis=dict(
            visible=False,
            range=[-n_filas - 0.05, 0.05],
            fixedrange=True,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Leyenda tipo mockup: "Al día (0 a 14 días): N"
    colores_actuales = [color_semaforo(d) for d in actividad['dias']]
    verdes    = sum(1 for c in colores_actuales if c == COLOR_VERDE)
    amarillos = sum(1 for c in colores_actuales if c == COLOR_AMARILLO)
    rojos     = sum(1 for c in colores_actuales if c == COLOR_ROJO)
    grises    = sum(1 for c in colores_actuales if c == COLOR_GRIS)

    def _leg_item(color, texto, valor):
        return (
            f'<span style="display:inline-flex;align-items:center;margin-right:1.5rem;font-size:.83rem;">'
            f'<span style="display:inline-block;width:12px;height:12px;background:{color};'
            f'border-radius:3px;margin-right:6px;"></span>'
            f'{texto}: <b style="margin-left:4px;">{valor}</b>'
            f'</span>'
        )

    leyenda_html = _leg_item(COLOR_VERDE, 'Al día (0 a 14 días)', verdes)
    leyenda_html += _leg_item(COLOR_AMARILLO, 'Con rezago (15 a 44)', amarillos)
    leyenda_html += _leg_item(COLOR_ROJO, 'Inactivo (45+)', rojos)
    if grises > 0:
        leyenda_html += _leg_item(COLOR_GRIS, 'Sin datos', grises)

    footer = (
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:.4rem .2rem .2rem .2rem;">'
        f'<div>{leyenda_html}</div>'
        f'<div style="font-size:.75rem;color:#888;">'
        f'{n_centros} centros · días desde el último registro'
        f'</div>'
        f'</div>'
    )
    st.markdown(footer, unsafe_allow_html=True)
