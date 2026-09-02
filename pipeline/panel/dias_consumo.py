"""
pipeline.panel.dias_consumo — Días de consumo por sustancia principal al ingreso.

Para cada categoría de sustancia principal declarada calcula el promedio de días
consumidos en las últimas 4 semanas (columna _total de Supabase, escala 0-28),
usando SOLO los pacientes que declararon esa sustancia como principal.

Lógica:
  1. Filtrar etapa=ingreso
  2. Clasificar sustancia_principal con la misma taxonomía de panel/sustancia.py
  3. Para cada categoría canónica, tomar la columna _total correspondiente
     y calcular el promedio incluyendo los ceros (ver nota en el codigo)
  4. Excluir categorías sin columna _total disponible (Tusi, Ketamina, etc.)

Mapeo categoría → columna Supabase:
  Alcohol          → alcohol_total
  Marihuana        → marihuana_total
  Cocaína          → cocaina_total
  Crack/Cristal    → crack_total
  Pasta base       → pastabase_total
  Metanfetamina    → metanfetamina_total
  Sedantes         → sedantes_total
  (resto: sin columna _total → no se muestran)

Diseño:
  - Barras horizontales ordenadas desc por promedio
  - Escala fija 0-28, línea de referencia en 14 días
  - Valor del promedio anotado al final de cada barra
  - N pacientes en hover

Función expuesta:
  render(df, pais, centro_id=None)
"""
import re as _re
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline.panel.config import titulo_seccion
from pipeline.validacion_top import (
    SUSTANCIA_A_COLUMNA, categorias_pais, clasificar_sustancia, detectar_pais,
    dias_validos_mes, etiqueta_sustancia, lineas_base,
)

COLOR_BARRA   = '#004AAD'   # PALETA_PRINCIPAL
COLOR_REF     = '#B0B8C1'   # from config PALETA_REF_LINE
TEXTO_OSCURO  = '#1F3864'
ALTO_BARRA_PX = 32


def _calcular_dias(df):
    """
    Filtra etapa=ingreso, clasifica la sustancia principal según la lista del
    país y calcula el promedio de días de consumo de cada categoría.

    Devuelve **todas** las categorías del país, en el orden del formulario y
    aunque alguna no tenga ningún caso. Elegir solo las más frecuentes hacía que
    este gráfico y el de prevalencia mostraran sustancias distintas.
    """
    cols_req = {'etapa', 'sustancia_principal'}
    if df is None or df.empty or not cols_req.issubset(df.columns):
        return []

    # Una fila por episodio: el TOP de ingreso que lo abre. El filtro anterior
    # comparaba la etapa como texto y contaba dos veces los ingresos duplicados.
    df_ing = lineas_base(df).copy()
    if df_ing.empty:
        return []

    pais = detectar_pais(df_ing)
    df_ing['_cat'] = df_ing['sustancia_principal'].apply(
        lambda v: clasificar_sustancia(v, pais)
    )

    resultado = []
    for cat in categorias_pais(pais):
        col = SUSTANCIA_A_COLUMNA.get(cat)
        mask = df_ing['_cat'] == cat
        n_cat = int(mask.sum())

        if col is None or col not in df_ing.columns:
            resultado.append({'sustancia': cat, 'etiqueta': etiqueta_sustancia(cat, pais),
                              'promedio': None, 'n': 0, 'n_cat': n_cat})
            continue

        # Se incluyen los ceros. Aquí solo entran los pacientes que declararon
        # esta sustancia como su principal, de modo que un cero significa que
        # ingresaron sin consumo de su propia sustancia problema, típico de las
        # derivaciones desde desintoxicación. Ese cero es su dato real y
        # excluirlo esconde justamente lo que el indicador quiere mostrar.
        con_valor = dias_validos_mes(df_ing.loc[mask, col]).dropna()
        resultado.append({
            'sustancia': cat,
            'etiqueta':  etiqueta_sustancia(cat, pais),
            'promedio':  round(con_valor.mean(), 1) if len(con_valor) else None,
            'n':         len(con_valor),
            'n_cat':     n_cat,
        })

    # Las que tienen casos van primero, de mayor a menor promedio; las vacías
    # cierran el gráfico sin desaparecer de él.
    resultado.sort(key=lambda x: (x['promedio'] is None, -(x['promedio'] or 0)))
    return resultado


def _figura(datos):
    # El n va bajo cada barra: sin él, siete pacientes se leen con el mismo peso
    # que trescientos, y ahora se muestran todas las categorías del país.
    labels  = [f"{d['etiqueta']}<br><span style='font-size:9px'>n = {d['n']}</span>"
               for d in datos]
    valores = [d['promedio'] or 0 for d in datos]
    textos  = [f"<b>{d['promedio']}</b>" if d['promedio'] is not None else ''
               for d in datos]
    hovers  = [
        f"<b>{d['etiqueta']}</b><br>" + (
            f"Promedio: {d['promedio']} días<br>"
            f"Con dato de días: {d['n']} de {d['n_cat']} que la declararon principal"
            if d['promedio'] is not None else
            f"Sin registro de días<br>"
            f"La declararon principal: {d['n_cat']}"
        )
        for d in datos
    ]

    ancho_barra = 80   # px por barra en modo vertical
    alto = 220

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=valores,
        orientation='v',
        marker_color=COLOR_BARRA,
        text=textos,
        textposition='outside',
        hovertext=hovers,
        hoverinfo='text',
        cliponaxis=False,
    ))

    # Línea de referencia en 14 días
    fig.add_shape(
        type='line',
        x0=-0.5, x1=len(datos) - 0.5, y0=14, y1=14,
        line=dict(color=COLOR_REF, width=1.5, dash='dot'),
        layer='below',
    )
    fig.add_annotation(
        x=len(datos) - 0.5, y=14,
        text='14 días',
        showarrow=False,
        font=dict(size=9, color=COLOR_REF),
        yanchor='bottom',
        xanchor='right',
    )

    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=24, b=8),
        yaxis=dict(
            range=[0, 31],
            tickvals=[0, 7, 14, 21, 28],
            ticktext=['0', '7', '14', '21', '28'],
            title=None,
            gridcolor='#F0F0F0',
            zeroline=False,
        ),
        xaxis=dict(
            title=None,
            tickfont=dict(size=10),
            tickangle=0,
            fixedrange=True,
        ),
        bargap=0.35,
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', color=TEXTO_OSCURO),
        showlegend=False,
    )
    return fig


def render(df, pais, centro_id=None):
    with st.container(border=True):
        st.markdown(
            titulo_seccion(
                '📅', 'Días de consumo · sustancia principal',
                'promedio de días en las últimas 4 semanas · solo pacientes al ingreso'
            ),
            unsafe_allow_html=True,
        )

        if centro_id:
            df = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()

        datos = _calcular_dias(df)

        if not datos:
            st.caption('Sin datos de consumo disponibles para este país.')
            return

        st.plotly_chart(_figura(datos), use_container_width=True,
                        config={'displayModeBar': False})
