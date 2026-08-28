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
from pipeline.validacion_top import normalizar_sexo_valor


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

    render_comparativo_nacional(d, centro, pais, df_pais)


def _normalizar_sexo(v):
    """Delegado a validacion_top.normalizar_sexo_valor (fuente única)."""
    return normalizar_sexo_valor(v)


def _es_s(v):
    """Copia exacta de transgresion.py:_es_s, para consistencia."""
    if pd.isna(v):
        return False
    return str(v).strip().upper() in ('S', 'SI', 'SÍ', 'YES', '1', 'TRUE')


def _indicadores_ingreso(df):
    """Calcula los mismos indicadores que los graficos individuales, sobre etapa='ingreso'."""
    out = {'pct_hombres': None, 'edad_prom': None, 'sust_top': None,
           'pct_transgresion': None, 'salud_psic': None,
           'salud_fis': None, 'calidad_vida': None, 'n': 0}
    if df is None or df.empty or 'etapa' not in df.columns:
        return out
    d_ing = df[df['etapa'] == 'ingreso'].copy()
    out['n'] = len(d_ing)
    if d_ing.empty:
        return out

    if 'sexo' in d_ing.columns:
        grp = d_ing['sexo'].apply(_normalizar_sexo).value_counts()
        total_valido = grp.sum()
        if total_valido > 0:
            out['pct_hombres'] = round(grp.get('H', 0) / total_valido * 100, 1)

    if 'fecha_nacimiento' in d_ing.columns and 'fecha_entrevista' in d_ing.columns:
        from pipeline.validacion_top import edad_valida
        edades = edad_valida(d_ing['fecha_nacimiento'], d_ing['fecha_entrevista']).dropna()
        if len(edades):
            out['edad_prom'] = round(edades.mean(), 1)

    if 'sustancia_principal' in d_ing.columns:
        vc = d_ing['sustancia_principal'].dropna().astype(str).str.strip()
        vc = vc[vc != '']
        if len(vc):
            out['sust_top'] = vc.value_counts().idxmax()

    cols_trans = [c for c in ('hurto', 'robo', 'venta_droga', 'rina_pelea') if c in d_ing.columns]
    if cols_trans:
        mask_alguna = pd.Series([False] * len(d_ing), index=d_ing.index)
        for c in cols_trans:
            mask_alguna = mask_alguna | d_ing[c].apply(_es_s)
        out['pct_transgresion'] = round(mask_alguna.sum() / len(d_ing) * 100, 1)

    from pipeline.validacion_top import escala_salud_valida
    for campo, key in [('salud_psicologica', 'salud_psic'), ('salud_fisica', 'salud_fis'),
                        ('calidad_vida', 'calidad_vida')]:
        if campo in d_ing.columns:
            vals = escala_salud_valida(d_ing[campo]).dropna()
            if len(vals):
                out[key] = round(vals.mean(), 1)

    return out


def _fila_comparativa(label, val_centro, val_nac, unidad='', decimales=1, mayor_es_mejor=None):
    def _fmt(v):
        if v is None:
            return '—'
        return f'{v:.{decimales}f}{unidad}'
    txt_centro, txt_nac = _fmt(val_centro), _fmt(val_nac)
    color = '#555'
    if val_centro is not None and val_nac is not None and mayor_es_mejor is not None:
        mejor = val_centro >= val_nac if mayor_es_mejor else val_centro <= val_nac
        color = '#1D9E75' if mejor else '#D95F5F'
    return (
        f'<tr>'
        f'<td style="padding:.45rem .6rem;color:#333;">{label}</td>'
        f'<td style="padding:.45rem .6rem;text-align:center;font-weight:700;color:{color};">{txt_centro}</td>'
        f'<td style="padding:.45rem .6rem;text-align:center;color:#888;">{txt_nac}</td>'
        f'</tr>'
    )


def render_comparativo_nacional(d, centro, pais, df_pais):
    """Tabla compacta: centro vs. promedio nacional, sin exponer otros centros individuales."""
    if df_pais is None or df_pais.empty:
        return
    ind_centro = _indicadores_ingreso(d)
    ind_nac = _indicadores_ingreso(df_pais)

    filas = [
        _fila_comparativa('% hombres', ind_centro['pct_hombres'], ind_nac['pct_hombres'], '%'),
        _fila_comparativa('Edad promedio', ind_centro['edad_prom'], ind_nac['edad_prom'], ' años'),
        _fila_comparativa('% con transgresión a la ley', ind_centro['pct_transgresion'],
                           ind_nac['pct_transgresion'], '%', mayor_es_mejor=False),
        _fila_comparativa('Salud psicológica (0-20)', ind_centro['salud_psic'], ind_nac['salud_psic'],
                           '', mayor_es_mejor=True),
        _fila_comparativa('Salud física (0-20)', ind_centro['salud_fis'], ind_nac['salud_fis'],
                           '', mayor_es_mejor=True),
        _fila_comparativa('Calidad de vida (0-20)', ind_centro['calidad_vida'], ind_nac['calidad_vida'],
                           '', mayor_es_mejor=True),
    ]

    sust_centro = ind_centro['sust_top'] or '—'
    sust_nac = ind_nac['sust_top'] or '—'

    st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(titulo_seccion('📍', 'Tu centro frente al promedio nacional',
                                    'pacientes al ingreso · no incluye datos de otros centros individuales'),
                    unsafe_allow_html=True)
        st.markdown(
            f'<table style="width:100%;border-collapse:collapse;font-size:.85rem;">'
            f'<tr style="border-bottom:2px solid #E5E5E5;">'
            f'<th style="text-align:left;padding:.45rem .6rem;color:#888;font-size:.72rem;">INDICADOR</th>'
            f'<th style="text-align:center;padding:.45rem .6rem;color:#004AAD;font-size:.72rem;">{centro}</th>'
            f'<th style="text-align:center;padding:.45rem .6rem;color:#888;font-size:.72rem;">{pais} (nacional)</th>'
            f'</tr>'
            + ''.join(filas) +
            f'<tr><td style="padding:.45rem .6rem;color:#333;">Sustancia principal más frecuente</td>'
            f'<td style="padding:.45rem .6rem;text-align:center;font-weight:700;color:#004AAD;">{sust_centro}</td>'
            f'<td style="padding:.45rem .6rem;text-align:center;color:#888;">{sust_nac}</td></tr>'
            f'</table>',
            unsafe_allow_html=True
        )
        st.caption('Colores: verde = tu centro está mejor que el promedio nacional en ese indicador · '
                   'rojo = está por debajo. Sin comparación con otros centros individuales.')
