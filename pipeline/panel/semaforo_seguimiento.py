"""
pipeline.panel.semaforo_seguimiento — Dona de seguimiento de pacientes.

Para cada paciente clasifica el estado de su segundo TOP:
  - Completado: ya tiene TOP2
  - Al día (<60 días): solo tiene TOP1, lleva menos de 60 días desde él
  - Con rezago (60-89 días): lleva entre 60 y 89 días sin TOP2
  - Urgente (90+ días): lleva 90 o más días sin TOP2

TOP1 y TOP2 vienen de `seguimiento_core.top2_por_paciente()`, la misma fuente
de la tarjeta "Con seguimiento (TOP2)": el primer TOP del paciente y el
siguiente con fecha distinta, sin mirar la etiqueta `etapa`. Por eso los
urgentes son exactamente los elegibles de esa tarjeta que todavía no tienen TOP2.

Fuente: df_panel de Supabase (columnas: codigo_paciente, fecha_entrevista, centro)

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from pipeline.panel.config import titulo_seccion
from pipeline.panel.seguimiento_core import top2_por_paciente, DIAS_UMBRAL_DEFAULT
from pipeline.validacion_top import es_etapa_ingreso

COLOR_COMPLETADO = '#1D9E75'   # verde
COLOR_AL_DIA     = '#8BC34A'   # verde claro
COLOR_REZAGO     = '#F0A836'   # amarillo
COLOR_URGENTE    = '#E15D5D'   # rojo
TEXTO_OSCURO     = '#1F3864'

UMBRAL_ATRASO  = 60
UMBRAL_URGENTE = DIAS_UMBRAL_DEFAULT   # el mismo umbral de la cobertura


def _calcular_semaforo(df, hoy=None):
    """
    Retorna dict con n por categoría y total.
    """
    vacio = {
        'completado': 0, 'al_dia': 0, 'rezago': 0, 'urgente': 0, 'total': 0,
        'sin_ingreso': 0,
    }
    per = top2_por_paciente(df, hoy=hoy)
    if per.empty:
        return vacio

    sin_top2 = per[~per['tiene_top2']]
    completado = int(per['tiene_top2'].sum())
    al_dia  = int((sin_top2['dias_top1'] < UMBRAL_ATRASO).sum())
    rezago  = int(((sin_top2['dias_top1'] >= UMBRAL_ATRASO) &
                   (sin_top2['dias_top1'] < UMBRAL_URGENTE)).sum())
    urgente = int((sin_top2['dias_top1'] >= UMBRAL_URGENTE).sum())

    total = completado + al_dia + rezago + urgente

    # Pacientes sin ningún TOP marcado como ingreso: entran al semáforo porque
    # tienen TOP1, pero no a la tarjeta "Pacientes ingresados". Se informan para
    # que la diferencia entre las dos cifras no parezca un error.
    sin_ingreso = 0
    if 'etapa' in df.columns:
        cod = df['codigo_paciente'].astype(str).str.strip()
        con_ingreso = set(cod[df['etapa'].apply(es_etapa_ingreso)])
        sin_ingreso = int((~per['codigo'].isin(con_ingreso)).sum())

    return {
        'completado':  completado,
        'al_dia':      al_dia,
        'rezago':      rezago,
        'urgente':     urgente,
        'total':       total,
        'sin_ingreso': sin_ingreso,
    }


def _figura(datos):
    total = datos['total']
    if total == 0:
        return None

    segmentos = [
        ('Completados',       datos['completado'], COLOR_COMPLETADO),
        ('Al día (<60 días)', datos['al_dia'],     COLOR_AL_DIA),
        ('Con rezago (60-89d)',datos['rezago'],    COLOR_REZAGO),
        ('Urgentes (90+ d)',  datos['urgente'],    COLOR_URGENTE),
    ]
    seg_vis = [(lbl, n, c) for lbl, n, c in segmentos if n > 0]

    labels = [s[0] for s in seg_vis]
    values = [s[1] for s in seg_vis]
    colors = [s[2] for s in seg_vis]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0,
        marker=dict(colors=colors, line=dict(color='white', width=2)),
        textinfo='percent',
        textfont=dict(size=12, color='white', family='Arial'),
        hovertemplate='%{label}: %{value} pacientes (%{percent})<extra></extra>',
        sort=False,
    ))

    fig.update_layout(
        height=200,
        margin=dict(l=0, r=0, t=8, b=8),
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        font=dict(family='Inter, sans-serif', color=TEXTO_OSCURO),
    )
    return fig


def render(df, pais, centro_id=None):
    with st.container(border=True):
        st.markdown(
            titulo_seccion('🚦', 'Semáforo de seguimiento',
                           'estado de la segunda evaluación TOP por paciente'),
            unsafe_allow_html=True
        )

        if centro_id:
            df = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()

        datos = _calcular_semaforo(df)

        if datos['total'] == 0:
            st.caption('Sin pacientes con TOP1 registrado.')
            return

        fig = _figura(datos)
        if fig:
            st.plotly_chart(fig, use_container_width=True,
                            config={'displayModeBar': False})

        # Leyenda con n y %
        total = datos['total']
        segmentos = [
            ('Completados',        datos['completado'], COLOR_COMPLETADO),
            ('Al día (<60 días)',  datos['al_dia'],     COLOR_AL_DIA),
            ('Con rezago (60-89d)',datos['rezago'],     COLOR_REZAGO),
            ('Urgentes (90+ d)',   datos['urgente'],    COLOR_URGENTE),
        ]
        leyenda_html = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:.3rem;">'
        for lbl, n, color in segmentos:
            if n == 0:
                continue
            pct = round(n / total * 100)
            leyenda_html += (
                f'<div style="display:flex;align-items:center;gap:4px;'
                f'font-size:.7rem;color:#555;">'
                f'<span style="width:10px;height:10px;border-radius:2px;'
                f'background:{color};flex-shrink:0;display:inline-block;"></span>'
                f'{lbl} ({n} · {pct}%)</div>'
            )
        leyenda_html += '</div>'
        st.markdown(leyenda_html, unsafe_allow_html=True)

        st.markdown(
            f'<div style="font-size:.68rem;color:#999;margin-top:.3rem;">'
            f'N total: {total} pacientes con TOP1'
            + (f', de ellos {datos["sin_ingreso"]} sin TOP de ingreso' if datos['sin_ingreso'] else '')
            + ' · días calculados desde el primer TOP hasta hoy'
            f'</div>',
            unsafe_allow_html=True
        )
