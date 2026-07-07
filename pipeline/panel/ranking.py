"""
pipeline.panel.ranking — Ranking horizontal por ingresos acumulados por centro.

Muestra todos los centros del país ordenados por número de registros con
etapa='ingreso', de mayor a menor. Altura del gráfico se ajusta al número
de centros para mantener legibilidad tanto en países pequeños (8 centros)
como grandes (21 centros de México CIJ).

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import plotly.graph_objects as go

from pipeline.panel.config import ingresos_por_centro


# Paleta del panel (mantener consistencia con app.py)
NAVY  = '#1F3864'
MID   = '#2E75B6'
ACCENT= '#00B0F0'


def render(df, pais, centro_id=None):
    """
    Pinta el ranking horizontal de ingresos por centro.

    Args:
        df: DataFrame del país (columnas 'centro' y 'etapa')
        pais: nombre del país (para título contextual)
        centro_id: si viene con valor, resalta ese centro. Los demás quedan atenuados.
    """
    st.markdown(
        '<div class="sec">🏆 Ranking de ingresos por centro</div>',
        unsafe_allow_html=True
    )

    ranking = ingresos_por_centro(df)

    if ranking.empty:
        st.info('ℹ Aún no hay ingresos registrados para calcular el ranking.')
        return

    # Colores: si hay centro destacado, ese va NAVY y el resto ACCENT atenuado
    if centro_id:
        colores = [
            NAVY if str(c).strip() == str(centro_id).strip() else '#B4C7E7'
            for c in ranking['centro']
        ]
    else:
        colores = [MID] * len(ranking)

    # Plotly con barras horizontales. Para que la barra más alta quede arriba,
    # invertimos el orden (Plotly pinta de abajo hacia arriba).
    ranking_reverso = ranking.iloc[::-1].reset_index(drop=True)
    colores_reverso = colores[::-1]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=ranking_reverso['n_ingresos'],
        y=ranking_reverso['centro'],
        orientation='h',
        marker=dict(color=colores_reverso, line=dict(color='white', width=1)),
        text=ranking_reverso['n_ingresos'],
        textposition='outside',
        textfont=dict(color=NAVY, size=12, family='Arial'),
        hovertemplate='<b>%{y}</b><br>Ingresos: %{x}<extra></extra>',
        cliponaxis=False,
    ))

    # Altura dinámica: 30 px por centro + margen fijo, mínimo 200
    n = len(ranking)
    alto = max(200, n * 30 + 60)

    max_val = int(ranking['n_ingresos'].max()) if not ranking.empty else 0

    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=60, t=10, b=20),
        xaxis=dict(
            title='Registros de ingreso',
            title_font=dict(size=11, color='#666'),
            tickfont=dict(size=10, color='#666'),
            gridcolor='#EEE',
            zerolinecolor='#DDD',
            range=[0, max_val * 1.15 if max_val > 0 else 1],
        ),
        yaxis=dict(
            tickfont=dict(size=11, color=NAVY, family='Arial'),
            automargin=True,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
