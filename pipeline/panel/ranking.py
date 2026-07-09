"""
pipeline.panel.ranking — Ranking por ingresos + total de registros TOP.

Dos gráficos apilados dentro del mismo container:
  1. Ranking por ingresos (azul #004AAD) — ordenado desc por n_ingresos
  2. Ranking por total de registros TOP (morado #7B68EE) — ordenado desc por total

Ambos con barra de fondo gris, mismo TOP_N_VISIBLE, mismo expander pattern.
bargap aumentado a 0.40 para mayor espaciado entre barras.

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import ingresos_por_centro, titulo_seccion

COLOR_ING   = '#004AAD'   # azul PALETA_PRINCIPAL
COLOR_TOT   = '#7B68EE'   # morado
COLOR_FONDO = '#E5E5E5'   # gris claro
COLOR_TEXTO = '#004AAD'

TOP_N_VISIBLE = 6


def _grafico_ingresos(ranking, centro_id):
    max_val = max(int(ranking['n_ingresos'].max()), 1)
    colores = [
        '#00B0F0' if centro_id and str(c).strip() == str(centro_id).strip() else COLOR_ING
        for c in ranking['centro']
    ]
    r = ranking.iloc[::-1].reset_index(drop=True)
    c = colores[::-1]
    n = len(r)
    alto = max(80, n * 26 + 20)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[max_val] * n, y=r['centro'], orientation='h',
        marker=dict(color=COLOR_FONDO, line=dict(width=0)),
        hoverinfo='skip', showlegend=False,
    ))
    fig.add_trace(go.Bar(
        x=r['n_ingresos'], y=r['centro'], orientation='h',
        marker=dict(color=c, line=dict(width=0)),
        text=r['n_ingresos'], textposition='outside',
        textfont=dict(color=COLOR_TEXTO, size=10, family='Arial'),
        hovertemplate='<b>%{y}</b><br>Ingresos: %{x}<extra></extra>',
        cliponaxis=False, showlegend=False,
    ))
    fig.update_layout(
        height=alto, margin=dict(l=8, r=50, t=4, b=4),
        barmode='overlay', bargap=0.40,
        xaxis=dict(visible=False, range=[0, max_val * 1.20], fixedrange=True),
        yaxis=dict(tickfont=dict(size=9, color=COLOR_TEXTO, family='Arial'),
                   automargin=True, fixedrange=True),
        plot_bgcolor='white', paper_bgcolor='white',
    )
    return fig


def _total_por_centro(df):
    """Cuenta todos los registros TOP por centro, independiente de la etapa."""
    if df is None or df.empty or 'centro' not in df.columns:
        return pd.DataFrame(columns=['centro', 'n_total'])
    tmp = df.copy()
    tmp['centro'] = tmp['centro'].astype(str).str.strip()
    tmp = tmp[tmp['centro'] != '']
    agg = tmp.groupby('centro').size().reset_index(name='n_total')
    return agg.sort_values('n_total', ascending=False).reset_index(drop=True)


def _grafico_total(ranking, centro_id):
    max_val = max(int(ranking['n_total'].max()), 1)
    colores = [
        '#9B8FE8' if centro_id and str(c).strip() == str(centro_id).strip() else COLOR_TOT
        for c in ranking['centro']
    ]
    r = ranking.iloc[::-1].reset_index(drop=True)
    c = colores[::-1]
    n = len(r)
    alto = max(80, n * 26 + 20)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[max_val] * n, y=r['centro'], orientation='h',
        marker=dict(color=COLOR_FONDO, line=dict(width=0)),
        hoverinfo='skip', showlegend=False,
    ))
    fig.add_trace(go.Bar(
        x=r['n_total'], y=r['centro'], orientation='h',
        marker=dict(color=c, line=dict(width=0)),
        text=r['n_total'], textposition='outside',
        textfont=dict(color=COLOR_TOT, size=10, family='Arial'),
        hovertemplate='<b>%{y}</b><br>Total registros TOP: %{x}<extra></extra>',
        cliponaxis=False, showlegend=False,
    ))
    fig.update_layout(
        height=alto, margin=dict(l=8, r=50, t=4, b=4),
        barmode='overlay', bargap=0.40,
        xaxis=dict(visible=False, range=[0, max_val * 1.20], fixedrange=True),
        yaxis=dict(tickfont=dict(size=9, color=COLOR_TOT, family='Arial'),
                   automargin=True, fixedrange=True),
        plot_bgcolor='white', paper_bgcolor='white',
    )
    return fig


def _render_seccion(titulo, subtitulo, ranking_df, col_n, col_label,
                    fn_grafico, centro_id, key_prefix):
    """Renderiza título + gráfico + expander para una sección del ranking."""
    st.markdown(
        f'<div style="font-size:.8rem;font-weight:600;color:var(--text-secondary,#555);'
        f'margin:.5rem 0 .1rem 0;">{titulo}</div>'
        f'<div style="font-size:.68rem;color:#999;margin-bottom:.2rem;">{subtitulo}</div>',
        unsafe_allow_html=True
    )
    total = len(ranking_df)
    if total <= TOP_N_VISIBLE:
        st.plotly_chart(fn_grafico(ranking_df, centro_id),
                        use_container_width=True,
                        config={'displayModeBar': False},
                        key=f'{key_prefix}_main')
    else:
        top   = ranking_df.head(TOP_N_VISIBLE).reset_index(drop=True)
        resto = ranking_df.iloc[TOP_N_VISIBLE:].reset_index(drop=True)
        st.plotly_chart(fn_grafico(top, centro_id),
                        use_container_width=True,
                        config={'displayModeBar': False},
                        key=f'{key_prefix}_top')
        with st.expander(f'▼ Ver otros {len(resto)} centros'):
            st.plotly_chart(fn_grafico(resto, centro_id),
                            use_container_width=True,
                            config={'displayModeBar': False},
                            key=f'{key_prefix}_resto')


def render(df, pais, centro_id=None):
    with st.container(border=True):
        st.markdown(
            titulo_seccion('🏆', 'Ranking por centro',
                           'ingresos acumulados · total de registros TOP'),
            unsafe_allow_html=True
        )

        ranking_ing = ingresos_por_centro(df)
        ranking_tot = _total_por_centro(df)

        if ranking_ing.empty:
            st.info('ℹ Aún no hay ingresos registrados.')
            return

        # Sección 1: total TOP (primero — da visión global)
        _render_seccion(
            '🟣 Por total de registros TOP', 'todas las fases · ingreso + en tratamiento + egreso + seguimiento',
            ranking_tot, 'n_total', 'Total TOP',
            _grafico_total, centro_id, 'rk_tot'
        )

        st.markdown('<div style="height:.4rem;border-top:.5px solid #eee;margin:.5rem 0;"></div>',
                    unsafe_allow_html=True)

        # Sección 2: ingresos
        _render_seccion(
            '🔵 Por ingresos', 'pacientes con primera evaluación TOP',
            ranking_ing, 'n_ingresos', 'Ingresos',
            _grafico_ingresos, centro_id, 'rk_ing'
        )
