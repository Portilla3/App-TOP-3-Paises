"""
pipeline.panel.continuidad — % de seguimiento por centro (HOMOLOGADO).

Muestra, por centro, el porcentaje de pacientes ELEGIBLES (con 90 o más días
desde su primer TOP) que ya cuentan con un segundo TOP (TOP2).

IMPORTANTE — definición homologada:
  Este gráfico usa la MISMA fuente única que las métricas y los reportes:
  pipeline.panel.seguimiento_core.calcular_seguimiento(). No se recalcula aquí
  para evitar que las cifras se desincronicen entre pantallas.

Diseño:
  - Barras horizontales verdes
  - Línea vertical del promedio nacional del país (referencia)
  - Barra de fondo clara (referencia visual del máximo)
  - Top N visible por defecto, expander con el resto
  - Etiqueta fija que explica sobre qué base se calcula

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion
from pipeline.panel.seguimiento_core import calcular_seguimiento


VERDE_BARRA  = '#1D9E75'   # PALETA_VERDE
VERDE_DESTAC = '#1D9E75'
FONDO        = '#E5E5E5'   # PALETA_SECUNDARIO
TEXTO_OSCURO = '#004AAD'


TOP_N_VISIBLE = 8


def _grafico(ranking, centro_id, promedio_nacional):
    """Construye figura Plotly con barras horizontales verdes + línea de promedio."""
    max_val = ranking['pct_continuidad'].max() if not ranking.empty else 1.0
    if max_val <= 0:
        max_val = 1.0
    # Escala dinámica: máximo del gráfico = max real * 1.5, con piso de 10%
    escala_max = max(max_val * 1.5, 10.0)

    colores = [
        VERDE_DESTAC if centro_id and str(c).strip() == str(centro_id).strip() else VERDE_BARRA
        for c in ranking['centro']
    ]

    # Plotly pinta de abajo hacia arriba en horizontal, invertir
    ranking_rev = ranking.iloc[::-1].reset_index(drop=True)
    colores_rev = colores[::-1]

    fig = go.Figure()

    # Barra de fondo (referencia hasta el máximo del gráfico)
    fig.add_trace(go.Bar(
        x=[escala_max] * len(ranking_rev),
        y=ranking_rev['centro'],
        orientation='h',
        marker=dict(color=FONDO, line=dict(width=0)),
        hoverinfo='skip',
        showlegend=False,
    ))

    # Barra real con el %
    textos = [f'{v:.1f}%'.replace('.', ',') for v in ranking_rev['pct_continuidad']]
    fig.add_trace(go.Bar(
        x=ranking_rev['pct_continuidad'],
        y=ranking_rev['centro'],
        orientation='h',
        marker=dict(color=colores_rev, line=dict(width=0)),
        text=textos,
        textposition='outside',
        textfont=dict(color=TEXTO_OSCURO, size=10, family='Arial'),
        hovertemplate='<b>%{y}</b><br>Seguimiento: %{x:.1f}%<extra></extra>',
        cliponaxis=False,
        showlegend=False,
    ))

    # Línea vertical del promedio nacional (línea discreta)
    if promedio_nacional > 0:
        fig.add_shape(
            type='line',
            x0=promedio_nacional, x1=promedio_nacional,
            y0=-0.5, y1=len(ranking_rev) - 0.5,
            line=dict(color='#6C757D', width=1.5, dash='dot'),
        )

    n = len(ranking)
    alto = max(100, n * 26 + 20)

    fig.update_layout(
        height=alto,
        margin=dict(l=8, r=50, t=2, b=2),
        barmode='overlay',
        bargap=0.40,
        xaxis=dict(
            visible=False,
            range=[0, escala_max],
            fixedrange=True,
        ),
        yaxis=dict(
            tickfont=dict(size=9, color=TEXTO_OSCURO, family='Arial'),
            automargin=True,
            fixedrange=True,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    return fig


def _etiqueta_nota(texto):
    st.markdown(
        f'<div style="font-size:.78rem;color:#888;margin:.4rem 0 .1rem;">&#8505; {texto}</div>',
        unsafe_allow_html=True,
    )


def render(df, pais, centro_id=None):
    """
    Pinta el gráfico de seguimiento por centro, homologado a la base de 90 días.

    Args:
        df: DataFrame del país (columnas 'centro', 'codigo_paciente',
            'fecha_entrevista', 'etapa').
        pais: nombre del país (para el subtítulo).
        centro_id: si viene con valor, resalta ese centro.
    """
    with st.container(border=True):
        seg      = calcular_seguimiento(df)
        prom_nac = seg['pct_cobertura']
        pc       = seg['por_centro']

        st.markdown(
            titulo_seccion(
                '🔄', 'Seguimiento por centro',
                f'% de elegibles (90+ días) con segundo TOP · promedio nacional {prom_nac:.1f}%'.replace('.', ',')
            ),
            unsafe_allow_html=True
        )

        if seg['n_elegibles'] == 0 or pc is None or pc.empty:
            st.info('ℹ Aún no hay pacientes con 90 o más días desde su primer TOP para calcular el seguimiento.')
            _etiqueta_nota(seg['nota'])
            return

        ranking = (
            pc.rename(columns={'pct': 'pct_continuidad'})[['centro', 'pct_continuidad']]
              .sort_values('pct_continuidad', ascending=False)
              .reset_index(drop=True)
        )

        total = len(ranking)
        if total <= TOP_N_VISIBLE:
            st.plotly_chart(
                _grafico(ranking, centro_id, prom_nac),
                use_container_width=True,
                config={'displayModeBar': False}
            )
        else:
            top   = ranking.head(TOP_N_VISIBLE).reset_index(drop=True)
            resto = ranking.iloc[TOP_N_VISIBLE:].reset_index(drop=True)
            st.plotly_chart(
                _grafico(top, centro_id, prom_nac),
                use_container_width=True,
                config={'displayModeBar': False}
            )
            with st.expander(f'▼ Ver otros {len(resto)} centros'):
                st.plotly_chart(
                    _grafico(resto, centro_id, prom_nac),
                    use_container_width=True,
                    config={'displayModeBar': False}
                )

        # Etiqueta homologada: deja explícita la base de cálculo
        _etiqueta_nota(seg['nota'])
