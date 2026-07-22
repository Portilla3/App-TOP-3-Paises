"""
pipeline.panel.semaforo_centro — Semáforo de seguimientos pendientes por paciente.

Distinto de semaforo.py (que mide actividad a nivel de CENTRO: días desde el
último registro de cualquier paciente). Este módulo mide a nivel de PACIENTE:
cuánto tiempo lleva cada paciente desde su última medición (TOP1/TOP2/TOP3),
que es lo que le importa al coordinador de un centro para saber a quién le
falta re-evaluar.

Reutiliza los mismos colores/umbrales de config.py para consistencia visual.

Función expuesta: render(df, centro)
"""
import streamlit as st
import pandas as pd

from pipeline.panel.config import color_semaforo, prioridad_semaforo, titulo_seccion
from pipeline.validacion_top import fecha_nacimiento_valida  # no se usa aquí, pero misma familia


def _tabla_seguimientos(df, centro, hoy=None):
    """
    Para cada paciente del centro, calcula la última medición (etapa+fecha) y
    los días transcurridos desde entonces.

    Args:
        df: DataFrame ya filtrado al centro, columnas 'codigo_paciente',
            'etapa', 'fecha_entrevista'
        centro: nombre del centro (solo para mensajes, df ya debería venir filtrado)
        hoy: opcional pd.Timestamp para tests

    Returns:
        pd.DataFrame: codigo_paciente, ultima_etapa, ultima_fecha, dias, n_mediciones
    """
    cols_necesarias = {'codigo_paciente', 'fecha_entrevista'}
    if df is None or df.empty or not cols_necesarias.issubset(df.columns):
        return pd.DataFrame(columns=['codigo_paciente', 'ultima_etapa', 'ultima_fecha', 'dias', 'n_mediciones'])

    if hoy is None:
        hoy = pd.Timestamp.now()

    d = df.copy()
    d['fecha_entrevista'] = pd.to_datetime(d['fecha_entrevista'], errors='coerce')
    d = d.dropna(subset=['fecha_entrevista', 'codigo_paciente'])

    d = d.sort_values('fecha_entrevista')
    ultimas = d.groupby('codigo_paciente').agg(
        ultima_etapa=('etapa', 'last') if 'etapa' in d.columns else ('fecha_entrevista', 'size'),
        ultima_fecha=('fecha_entrevista', 'last'),
        n_mediciones=('fecha_entrevista', 'count'),
    ).reset_index()

    ultimas['dias'] = (hoy - ultimas['ultima_fecha']).dt.days
    ultimas = ultimas.sort_values('dias', ascending=False)
    return ultimas


def render(df, centro):
    st.markdown(titulo_seccion('🚦', f'Seguimientos — {centro}',
                                'días desde la última medición de cada paciente'), unsafe_allow_html=True)

    tabla = _tabla_seguimientos(df, centro)

    if tabla.empty:
        st.info('No hay pacientes con fecha de entrevista válida para este centro todavía.')
        return

    tabla['Semáforo'] = tabla['dias'].apply(lambda d: '🔴' if d > 89 else ('🟡' if d > 44 else '🟢'))
    tabla['prioridad'] = tabla['dias'].apply(prioridad_semaforo)
    tabla = tabla.sort_values(['prioridad', 'dias'], ascending=[False, False])

    n_rojo = int((tabla['Semáforo'] == '🔴').sum())
    n_amarillo = int((tabla['Semáforo'] == '🟡').sum())
    n_verde = int((tabla['Semáforo'] == '🟢').sum())

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="kpi red"><div class="kpi-lbl">🔴 Muy atrasados</div>'
                f'<div class="kpi-val">{n_rojo}</div><div class="kpi-sub">+90 días</div></div>',
                unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi orange"><div class="kpi-lbl">🟡 Atrasados</div>'
                f'<div class="kpi-val">{n_amarillo}</div><div class="kpi-sub">45-89 días</div></div>',
                unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi green"><div class="kpi-lbl">🟢 Al día</div>'
                f'<div class="kpi-val">{n_verde}</div><div class="kpi-sub">&lt;45 días</div></div>',
                unsafe_allow_html=True)

    st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.dataframe(
            tabla[['codigo_paciente', 'ultima_etapa', 'ultima_fecha', 'dias', 'n_mediciones', 'Semáforo']]
            .rename(columns={
                'codigo_paciente': 'Paciente', 'ultima_etapa': 'Última etapa',
                'ultima_fecha': 'Última medición', 'dias': 'Días desde entonces',
                'n_mediciones': 'N° mediciones totales'
            }),
            use_container_width=True, hide_index=True,
        )
        st.caption('Ordenado por urgencia: más atrasados primero. '
                   'Umbrales: 🟢 0-44 días · 🟡 45-89 días · 🔴 90+ días.')
