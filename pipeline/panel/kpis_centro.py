"""
pipeline.panel.kpis_centro — Panel de KPIs de inicio para un centro.

Resumen ejecutivo que ve el coordinador del centro al entrar: pacientes
activos, TOP de ingreso del mes, seguimientos pendientes, tasa de completitud.

No recalcula validez de datos por su cuenta: asume que df ya viene filtrado
al centro y, cuando corresponda, limpio vía validacion_top.py (misma fuente
de verdad que wide_top.py y el resto del panel).

Función expuesta: render(df, centro)
"""
import streamlit as st
import pandas as pd

from pipeline.panel.config import titulo_seccion
from pipeline.validacion_top import dias_validos_mes


def render(df, centro):
    st.markdown(titulo_seccion('🏠', f'Resumen — {centro}'), unsafe_allow_html=True)

    if df is None or df.empty:
        st.info('Sin registros todavía para este centro.')
        return

    d = df.copy()
    if 'fecha_entrevista' in d.columns:
        d['fecha_entrevista'] = pd.to_datetime(d['fecha_entrevista'], errors='coerce')

    hoy = pd.Timestamp.now()
    mes_actual = hoy.month
    anio_actual = hoy.year

    total_registros = len(d)
    pacientes_unicos = d['codigo_paciente'].nunique() if 'codigo_paciente' in d.columns else None

    # TOP de ingreso: primera medición por paciente (la de fecha más antigua)
    if 'codigo_paciente' in d.columns and 'fecha_entrevista' in d.columns:
        primeras = d.dropna(subset=['fecha_entrevista']).sort_values('fecha_entrevista') \
                     .groupby('codigo_paciente').first().reset_index()
        ingresos_mes = primeras[
            (primeras['fecha_entrevista'].dt.month == mes_actual) &
            (primeras['fecha_entrevista'].dt.year == anio_actual)
        ].shape[0]
    else:
        primeras = pd.DataFrame()
        ingresos_mes = 0

    # Con seguimiento: pacientes con más de 1 medición
    if 'codigo_paciente' in d.columns:
        conteo_por_paciente = d.groupby('codigo_paciente').size()
        con_seguimiento = int((conteo_por_paciente > 1).sum())
        tasa_completitud = (con_seguimiento / len(conteo_por_paciente) * 100) if len(conteo_por_paciente) else 0
    else:
        con_seguimiento = 0
        tasa_completitud = 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Total de registros', total_registros)
    c2.metric('Pacientes ingresados', pacientes_unicos if pacientes_unicos is not None else '—')
    c3.metric('TOP de ingreso (este mes)', ingresos_mes)
    c4.metric('Con al menos un seguimiento', f'{tasa_completitud:.1f}%',
              help=f'{con_seguimiento} de {pacientes_unicos or 0} pacientes')

    st.caption('Estos indicadores se calculan sobre los datos ya filtrados a este centro. '
               'Para el detalle de quién tiene seguimiento pendiente, revisa la pestaña de Seguimientos.')
