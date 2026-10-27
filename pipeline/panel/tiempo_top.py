"""
pipeline.panel.tiempo_top — Tiempo promedio entre TOP1 y TOP2 por centro.

Para cada paciente con TOP2 calcula los días entre su TOP1 y su TOP2. Ambos
vienen de `seguimiento_core.top2_por_paciente()`, la misma fuente de la
cobertura y del semáforo: el primer TOP del paciente y el siguiente con fecha
distinta, sin mirar la etiqueta `etapa`.

Hoy este gráfico no se muestra en la app: ningún módulo lo importa.

Muestra barras horizontales por centro ordenadas de menor a mayor días,
con línea vertical de promedio nacional como referencia.

Columnas Supabase usadas: codigo_paciente, centro, fecha_entrevista

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion
from pipeline.panel.seguimiento_core import top2_por_paciente

COLOR_BARRA  = '#7B68EE'   # morado
COLOR_REF    = '#7B68EE'   # línea promedio nacional
COLOR_FONDO  = '#E5E5E5'
COLOR_TEXTO  = '#534AB7'


def _calcular_tiempo(df, hoy=None):
    """
    Retorna DataFrame con columnas: centro, promedio_dias, n_pacientes.
    Solo incluye centros con al menos 1 paciente con TOP1 y TOP2.
    Centros sin TOP2 se retornan en lista separada.
    """
    per = top2_por_paciente(df, hoy=hoy)
    if per.empty:
        return pd.DataFrame(), []
    per['centro'] = per['centro'].astype(str).str.strip()
    per = per[per['centro'] != '']

    con = per[per['tiene_top2']].copy()
    if con.empty:
        return pd.DataFrame(), _centros_sin_top2(per)

    con['dias'] = (con['segundo'] - con['primer']).dt.days
    resultado = (con.groupby('centro')
                 .agg(promedio_dias=('dias', 'mean'), n_pacientes=('dias', 'count'))
                 .reset_index())
    resultado['promedio_dias'] = resultado['promedio_dias'].round(0).astype(int)
    resultado = resultado.sort_values('promedio_dias').reset_index(drop=True)

    sin_top2 = _centros_sin_top2(per, excluir=set(resultado['centro']))
    return resultado, sin_top2


def _centros_sin_top2(per, excluir=None):
    """Lista de centros que tienen pacientes pero ninguno con TOP2."""
    resultado = []
    for c, grupo in per.groupby('centro'):
        if excluir and c in excluir:
            continue
        if not grupo['tiene_top2'].any():
            resultado.append({'centro': c, 'n_ingresos': int(len(grupo))})
    return resultado


def _figura(resultado, sin_top2, promedio_nacional):
    """Construye la figura Plotly."""
    max_val = max(int(resultado['promedio_dias'].max()), 1) if not resultado.empty else 1
    escala  = max(max_val * 1.3, promedio_nacional * 1.5, 30)

    r = resultado.reset_index(drop=True)   # ya ordenado asc
    n = len(r)
    alto = max(100, n * 26 + (len(sin_top2) * 22) + 30)

    fig = go.Figure()

    # Barra de fondo
    fig.add_trace(go.Bar(
        x=[escala] * n, y=r['centro'], orientation='h',
        marker=dict(color=COLOR_FONDO, line=dict(width=0)),
        hoverinfo='skip', showlegend=False,
    ))

    # Barra de días
    fig.add_trace(go.Bar(
        x=r['promedio_dias'], y=r['centro'], orientation='h',
        marker=dict(color=COLOR_BARRA, line=dict(width=0), opacity=0.85),
        text=[f"{v} días" for v in r['promedio_dias']],
        textposition='outside',
        textfont=dict(color=COLOR_TEXTO, size=10, family='Arial'),
        customdata=r['n_pacientes'],
        hovertemplate='<b>%{y}</b><br>Promedio: %{x} días<br>Pacientes con TOP2: %{customdata}<extra></extra>',
        cliponaxis=False, showlegend=False,
    ))

    # Línea de promedio nacional
    if promedio_nacional > 0:
        fig.add_shape(
            type='line',
            x0=promedio_nacional, x1=promedio_nacional,
            y0=-0.5, y1=n - 0.5,
            line=dict(color=COLOR_REF, width=1.5, dash='dot'),
        )
        fig.add_annotation(
            x=promedio_nacional, y=n - 0.5,
            text=f'prom. nacional<br>{promedio_nacional} días',
            showarrow=False,
            font=dict(size=8, color=COLOR_REF),
            yanchor='bottom', xanchor='center',
        )

    fig.update_layout(
        height=alto,
        margin=dict(l=8, r=80, t=24, b=8),
        barmode='overlay', bargap=0.40,
        xaxis=dict(visible=False, range=[0, escala * 1.05], fixedrange=True),
        yaxis=dict(tickfont=dict(size=9, color=COLOR_TEXTO, family='Arial'),
                   automargin=True, fixedrange=True, autorange='reversed'),
        plot_bgcolor='white', paper_bgcolor='white',
    )
    return fig


def render(df, pais, centro_id=None):
    with st.container(border=True):
        st.markdown(
            titulo_seccion('⏱', 'Tiempo entre TOP1 y TOP2',
                           'promedio de días entre el primer y el segundo TOP'),
            unsafe_allow_html=True
        )

        if centro_id:
            df = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()

        resultado, sin_top2 = _calcular_tiempo(df)

        if resultado.empty:
            st.caption('Sin pacientes con TOP1 y TOP2 registrados.')
            if sin_top2:
                st.markdown(
                    f'<div style="font-size:.72rem;color:#999;margin-top:.3rem;">'
                    f'{len(sin_top2)} centro(s) con ingresos pero sin segunda evaluación registrada.'
                    f'</div>', unsafe_allow_html=True
                )
            return

        # Promedio nacional
        total_dias = resultado['promedio_dias'].mul(resultado['n_pacientes']).sum()
        total_pac  = resultado['n_pacientes'].sum()
        prom_nac   = int(round(total_dias / total_pac)) if total_pac > 0 else 0

        # Badge promedio nacional
        st.markdown(
            f'<div style="display:inline-flex;align-items:center;gap:8px;'
            f'background:#F0EEFF;border-radius:6px;padding:4px 12px;margin:.3rem 0 .6rem 0;">'
            f'  <span style="font-size:.72rem;color:#7B68EE;font-weight:600;">Promedio nacional</span>'
            f'  <span style="font-size:1.1rem;font-weight:600;color:#534AB7;">{prom_nac} días</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.plotly_chart(
            _figura(resultado, sin_top2, prom_nac),
            use_container_width=True,
            config={'displayModeBar': False}
        )

        # Centros sin TOP2
        if sin_top2:
            nombres = ', '.join(c['centro'] for c in sin_top2[:5])
            resto   = f' y {len(sin_top2)-5} más' if len(sin_top2) > 5 else ''
            st.markdown(
                f'<div style="font-size:.68rem;color:#999;margin-top:.3rem;">'
                f'Sin segunda evaluación registrada: {nombres}{resto}'
                f'</div>', unsafe_allow_html=True
            )

        # Nota al pie con explicación de cálculo
        n_total = int(resultado['n_pacientes'].sum())
        with st.expander('ℹ Cómo se calcula este indicador', expanded=False):
            st.markdown(
                '<div style="font-size:.75rem;color:#555;line-height:1.6;">'
                '<b>TOP1</b> = fecha del primer TOP del paciente.<br>'
                '<b>TOP2</b> = fecha del siguiente TOP con fecha distinta, en cualquier etapa.<br>'
                'Se calcula la diferencia en días entre ambas fechas y se promedia por centro.<br>'
                'Los centros sin ningún TOP2 registrado aparecen listados al pie, no en el gráfico.'
                '</div>',
                unsafe_allow_html=True
            )
        st.markdown(
            f'<div style="font-size:.68rem;color:#999;margin-top:.2rem;">'
            f'N = {n_total} pacientes con TOP1 y TOP2 · ordenado de menor a mayor días'
            f'</div>', unsafe_allow_html=True
        )
