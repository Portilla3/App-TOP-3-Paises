"""
pipeline.panel.kpis_centro — Panel de inicio para un centro (vista enchulada).

Reutiliza los mismos componentes visuales del "perfil de ingreso" que ya se
muestran en el Panel de gestión de país (piramide de sexo, edad, sustancia
principal, días de consumo, transgresión, salud), para que el centro vea
exactamente la misma estética que ya conoces, con sus propios datos.

Función expuesta: render(df, centro, pais)
"""
import streamlit as st
import pandas as pd

from pipeline.panel.config import titulo_seccion
from pipeline.panel import piramide as panel_piramide
from pipeline.panel import edad as panel_edad
from pipeline.panel import sustancia as panel_sustancia
from pipeline.panel import dias_consumo as panel_dias_consumo
from pipeline.panel import transgresion as panel_transgresion
from pipeline.panel import salud as panel_salud


def _kpi_card(col, label, valor, sub=None, tono=''):
    """Tarjeta de KPI reutilizando las clases CSS .kpi ya definidas en app.py."""
    clase = f'kpi {tono}'.strip()
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ''
    col.markdown(
        f'<div class="{clase}"><div class="kpi-lbl">{label}</div>'
        f'<div class="kpi-val">{valor}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def render(df, centro, pais=None):
    st.markdown(
        f'<span class="badge badge-centro">🏥 {centro}</span>'
        + (f'<span class="badge badge-periodo">{pais}</span>' if pais else ''),
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)

    if df is None or df.empty:
        st.info('Sin registros todavía para este centro.')
        return

    d = df.copy()
    if 'fecha_entrevista' in d.columns:
        d['fecha_entrevista'] = pd.to_datetime(d['fecha_entrevista'], errors='coerce')

    hoy = pd.Timestamp.now()
    total_registros = len(d)
    pacientes_unicos = d['codigo_paciente'].nunique() if 'codigo_paciente' in d.columns else 0

    if 'codigo_paciente' in d.columns and 'fecha_entrevista' in d.columns:
        primeras = d.dropna(subset=['fecha_entrevista']).sort_values('fecha_entrevista') \
                     .groupby('codigo_paciente').first().reset_index()
        ingresos_mes = primeras[
            (primeras['fecha_entrevista'].dt.month == hoy.month) &
            (primeras['fecha_entrevista'].dt.year == hoy.year)
        ].shape[0]
    else:
        ingresos_mes = 0

    if 'codigo_paciente' in d.columns:
        conteo = d.groupby('codigo_paciente').size()
        con_seguimiento = int((conteo > 1).sum())
        tasa = (con_seguimiento / len(conteo) * 100) if len(conteo) else 0
    else:
        con_seguimiento, tasa = 0, 0

    tono = 'green' if tasa >= 50 else ('orange' if tasa >= 20 else 'red')

    c1, c2, c3, c4 = st.columns(4)
    _kpi_card(c1, 'Total de registros', total_registros)
    _kpi_card(c2, 'Pacientes ingresados', pacientes_unicos)
    _kpi_card(c3, 'TOP de ingreso (este mes)', ingresos_mes)
    _kpi_card(c4, 'Con al menos un seguimiento', f'{tasa:.1f}%',
               sub=f'{con_seguimiento} de {pacientes_unicos} pacientes', tono=tono)

    if tasa < 20 and pacientes_unicos > 0:
        st.warning(f'⚠️ Solo {con_seguimiento} de {pacientes_unicos} pacientes tienen seguimiento '
                    f'registrado ({tasa:.1f}%). Revisa la pestaña de Seguimientos para ver el detalle.')

    st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)

    # ── Perfil del centro, misma estética que el panel de país ──────────────
    st.markdown('<div class="panel-fila-1">', unsafe_allow_html=True)
    col_sexo, col_edad = st.columns(2, gap='small')
    with col_sexo:
        panel_piramide.render(d, centro, centro_id=None)
    with col_edad:
        panel_edad.render(d, centro, centro_id=None)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

    st.markdown('<div class="panel-fila-2">', unsafe_allow_html=True)
    col_sust, col_dias = st.columns(2, gap='small')
    with col_sust:
        panel_sustancia.render(d, centro, centro_id=None)
    with col_dias:
        panel_dias_consumo.render(d, centro, centro_id=None)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

    st.markdown('<div class="panel-fila-3">', unsafe_allow_html=True)
    col_trans, col_salud = st.columns(2, gap='small')
    with col_trans:
        panel_transgresion.render(d, centro, centro_id=None)
    with col_salud:
        panel_salud.render(d, centro, centro_id=None)
    st.markdown('</div>', unsafe_allow_html=True)
