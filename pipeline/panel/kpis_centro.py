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

from pipeline.panel.config import titulo_seccion, continuidad_por_centro, actividad_por_centro, color_semaforo
from pipeline.panel import piramide as panel_piramide
from pipeline.panel import mensuales as panel_mensuales
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


def render(df, centro, pais=None, df_pais=None):
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
    if 'etapa' in d.columns and 'codigo_paciente' in d.columns:
        pacientes_unicos = d.loc[d['etapa'] == 'ingreso', 'codigo_paciente'].nunique()
    else:
        pacientes_unicos = d['codigo_paciente'].nunique() if 'codigo_paciente' in d.columns else 0

    if 'codigo_paciente' in d.columns and 'fecha_entrevista' in d.columns and 'etapa' in d.columns:
        ingresos_df = d[d['etapa'] == 'ingreso'].dropna(subset=['fecha_entrevista'])
        ingresos_mes = ingresos_df[
            (ingresos_df['fecha_entrevista'].dt.month == hoy.month) &
            (ingresos_df['fecha_entrevista'].dt.year == hoy.year)
        ].shape[0]
    elif 'codigo_paciente' in d.columns and 'fecha_entrevista' in d.columns:
        # Fallback si no hay columna 'etapa': usar la primera fila cronológica por paciente
        primeras = d.dropna(subset=['fecha_entrevista']).sort_values('fecha_entrevista') \
                     .groupby('codigo_paciente').first().reset_index()
        ingresos_mes = primeras[
            (primeras['fecha_entrevista'].dt.month == hoy.month) &
            (primeras['fecha_entrevista'].dt.year == hoy.year)
        ].shape[0]
    else:
        ingresos_mes = 0

    if 'codigo_paciente' in d.columns and 'etapa' in d.columns and 'centro' in d.columns:
        cont = continuidad_por_centro(d)
        if not cont.empty:
            fila = cont.iloc[0]  # ya viene filtrado a un solo centro
            con_seguimiento = int(fila['n_con_continuidad'])
            base_ingresos   = int(fila['n_ingresos'])
            tasa            = float(fila['pct_continuidad'])
        else:
            con_seguimiento, base_ingresos, tasa = 0, 0, 0.0
    else:
        con_seguimiento, base_ingresos, tasa = 0, 0, 0.0

    tono = 'green' if tasa >= 50 else ('orange' if tasa >= 20 else 'red')

    act = actividad_por_centro(d)
    if not act.empty:
        dias_ultimo = act.iloc[0]['dias']
        dias_lbl = '—' if pd.isna(dias_ultimo) else int(dias_ultimo)
        color_hex = color_semaforo(dias_ultimo)
        tono_dias = 'red' if color_hex == '#E15D5D' else ('orange' if color_hex == '#F0A836' else 'green')
    else:
        dias_lbl, tono_dias = '—', ''

    c1, c2, c3, c4, c5 = st.columns(5)
    _kpi_card(c1, 'Total de registros', total_registros)
    _kpi_card(c2, 'Pacientes ingresados', pacientes_unicos)
    _kpi_card(c3, 'TOP de ingreso (este mes)', ingresos_mes)
    _kpi_card(c4, 'Con al menos un seguimiento', f'{tasa:.1f}%',
               sub=f'{con_seguimiento} de {base_ingresos} con TOP de ingreso', tono=tono)
    _kpi_card(c5, 'Días desde el último registro', dias_lbl, tono=tono_dias)

    if tasa < 20 and base_ingresos > 0:
        st.warning(f'⚠️ Solo {con_seguimiento} de {base_ingresos} pacientes con TOP de ingreso tienen '
                    f'seguimiento registrado ({tasa:.1f}%). Revisa la pestaña de Seguimientos para ver el detalle.')

    # ── Comparación con promedio nacional (sin exponer otros centros) ───────
    if df_pais is not None and not df_pais.empty:
        cont_nac = continuidad_por_centro(df_pais)
        if not cont_nac.empty:
            total_ing_nac  = int(cont_nac['n_ingresos'].sum())
            total_cont_nac = int(cont_nac['n_con_continuidad'].sum())
            prom_nac = (total_cont_nac / total_ing_nac * 100) if total_ing_nac > 0 else 0.0
            diff = tasa - prom_nac
            comp_txt = 'por encima' if diff > 0 else ('por debajo' if diff < 0 else 'igual')
            comp_color = '#1D9E75' if diff >= 0 else '#D95F5F'
            st.markdown(
                f'<div style="background:#F8FAFD;border:1px solid #E5E5E5;border-radius:8px;'
                f'padding:.7rem 1rem;margin:.4rem 0 .8rem 0;font-size:.85rem;">'
                f'📍 Tu centro: <b>{tasa:.1f}%</b> de continuidad &nbsp;·&nbsp; '
                f'Promedio nacional ({pais}): <b>{prom_nac:.1f}%</b> &nbsp;·&nbsp; '
                f'<span style="color:{comp_color};font-weight:600;">{abs(diff):.1f} puntos {comp_txt}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)
    panel_mensuales.render(d, centro, centro_id=None)

    st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)

    # ── Perfil de pacientes al ingreso (mismo título que el panel de país) ──
    st.markdown(
        '<div class="seccion-panel">'
        '  <span class="seccion-panel-titulo">Perfil de pacientes al ingreso</span>'
        '  <span class="seccion-panel-linea"></span>'
        '  <span class="seccion-panel-sub">primera evaluación TOP · no incluye seguimientos</span>'
        '</div>',
        unsafe_allow_html=True
    )

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
