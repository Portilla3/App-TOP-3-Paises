"""
pipeline.panel.ranking — Ranking horizontal por ingresos acumulados por centro.

Muestra los centros del país ordenados por número de registros con
etapa='ingreso', de mayor a menor. Diseño según mockup aprobado:
  - Barra de fondo clara al 100% del máximo (referencia visual)
  - Barra sólida color primario con el valor real
  - Nombre del centro a la izquierda, valor al final de la barra
  - Ejes ocultos, sin gridlines
  - Top 10 visible por defecto; si hay más centros, expander con el resto

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import plotly.graph_objects as go

from pipeline.panel.config import ingresos_por_centro, titulo_seccion


NAVY   = '#1F3864'
MID    = '#2E75B6'
FONDO  = '#E8EEF7'   # gris azulado muy claro para barra de referencia
DESTAC = '#00B0F0'   # cyan para centro destacado


TOP_N_VISIBLE = 10


def _grafico(ranking, centro_id):
    """Construye el go.Figure con barras horizontales según diseño mockup."""
    max_val = int(ranking['n_ingresos'].max()) if not ranking.empty else 1
    if max_val == 0:
        max_val = 1

    # Colores de barra: normal MID, destacado DESTAC
    colores = [
        DESTAC if centro_id and str(c).strip() == str(centro_id).strip() else MID
        for c in ranking['centro']
    ]

    # Plotly pinta de abajo hacia arriba en horizontal, así que invertimos
    ranking_rev = ranking.iloc[::-1].reset_index(drop=True)
    colores_rev = colores[::-1]

    fig = go.Figure()

    # Barra de fondo (referencia al máximo)
    fig.add_trace(go.Bar(
        x=[max_val] * len(ranking_rev),
        y=ranking_rev['centro'],
        orientation='h',
        marker=dict(color=FONDO, line=dict(width=0)),
        hoverinfo='skip',
        showlegend=False,
    ))

    # Barra real con el valor
    fig.add_trace(go.Bar(
        x=ranking_rev['n_ingresos'],
        y=ranking_rev['centro'],
        orientation='h',
        marker=dict(color=colores_rev, line=dict(width=0)),
        text=ranking_rev['n_ingresos'],
        textposition='outside',
        textfont=dict(color=NAVY, size=15, family='Arial'),
        hovertemplate='<b>%{y}</b><br>Ingresos: %{x}<extra></extra>',
        cliponaxis=False,
        showlegend=False,
    ))

    # Altura dinámica compacta
    n = len(ranking)
    alto = max(120, n * 20 + 25)

    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=55, t=4, b=4),
        barmode='overlay',
        bargap=0.12,
        xaxis=dict(
            visible=False,
            range=[0, max_val * 1.18],
            fixedrange=True,
        ),
        yaxis=dict(
            tickfont=dict(size=12, color=NAVY, family='Arial'),
            automargin=True,
            fixedrange=True,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    return fig


def render(df, pais, centro_id=None):
    """
    Pinta el ranking horizontal de ingresos por centro.

    Args:
        df: DataFrame del país (columnas 'centro' y 'etapa')
        pais: nombre del país (para título contextual)
        centro_id: si viene con valor, resalta ese centro en cyan.
    """
    with st.container(border=True):
        st.markdown(
            titulo_seccion('🏆', 'Ranking por ingresos acumulados',
                           'pacientes con primera evaluación TOP'),
            unsafe_allow_html=True
        )

        ranking = ingresos_por_centro(df)

        if ranking.empty:
            st.info('ℹ Aún no hay ingresos registrados para calcular el ranking.')
            return

        total = len(ranking)

        if total <= TOP_N_VISIBLE:
            st.plotly_chart(
                _grafico(ranking, centro_id),
                use_container_width=True,
                config={'displayModeBar': False}
            )
        else:
            top     = ranking.head(TOP_N_VISIBLE).reset_index(drop=True)
            resto   = ranking.iloc[TOP_N_VISIBLE:].reset_index(drop=True)

            st.plotly_chart(
                _grafico(top, centro_id),
                use_container_width=True,
                config={'displayModeBar': False}
            )

            with st.expander(f'▼ Ver otros {len(resto)} centros'):
                st.plotly_chart(
                    _grafico(resto, centro_id),
                    use_container_width=True,
                    config={'displayModeBar': False}
                )
