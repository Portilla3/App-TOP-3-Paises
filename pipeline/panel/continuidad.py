"""
pipeline.panel.continuidad — % de continuidad por centro.

Para cada centro muestra el porcentaje de pacientes con ingreso que tienen
además al menos un segundo registro TOP (cualquier etapa distinta de ingreso:
en_tratamiento, egreso o seguimiento).

Diseño según mockup aprobado:
  - Barras horizontales verdes
  - Línea vertical del promedio nacional del país (referencia)
  - Barra de fondo clara al 100% (referencia visual del máximo)
  - Top 10 visible por defecto, expander con el resto

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import plotly.graph_objects as go

from pipeline.panel.config import continuidad_por_centro, titulo_seccion


VERDE_BARRA  = '#1A6B9A'   # from config PALETA_PRINCIPAL
VERDE_DESTAC = '#1A6B9A'
FONDO        = '#EEF2F5'   # from config PALETA_FONDO_REF   # gris verdoso muy claro para barra de referencia
TEXTO_OSCURO = '#1F3864'


TOP_N_VISIBLE = 10


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
        textfont=dict(color=TEXTO_OSCURO, size=13, family='Arial'),
        hovertemplate='<b>%{y}</b><br>Continuidad: %{x:.1f}%<extra></extra>',
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
    alto = max(100, n * 16 + 18)

    fig.update_layout(
        height=alto,
        margin=dict(l=8, r=50, t=2, b=2),
        barmode='overlay',
        bargap=0.10,
        xaxis=dict(
            visible=False,
            range=[0, escala_max],
            fixedrange=True,
        ),
        yaxis=dict(
            tickfont=dict(size=11, color=TEXTO_OSCURO, family='Arial'),
            automargin=True,
            fixedrange=True,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    return fig


def render(df, pais, centro_id=None):
    """
    Pinta el gráfico de continuidad por centro.

    Args:
        df: DataFrame del país (columnas 'centro', 'etapa', 'codigo_paciente')
        pais: nombre del país (para el subtítulo)
        centro_id: si viene con valor, resalta ese centro.
    """
    with st.container(border=True):
        cont = continuidad_por_centro(df)

        # Promedio nacional: pct de pacientes ingresados del país con
        # continuidad (no promedio de pcts por centro, sino global país).
        if not cont.empty:
            total_ing  = int(cont['n_ingresos'].sum())
            total_cont = int(cont['n_con_continuidad'].sum())
            prom_nac   = (total_cont / total_ing * 100) if total_ing > 0 else 0.0
        else:
            prom_nac = 0.0

        st.markdown(
            titulo_seccion(
                '🔄', 'Continuidad por centro',
                f'% con al menos un segundo registro · promedio nacional {prom_nac:.1f}%'.replace('.', ',')
            ),
            unsafe_allow_html=True
        )

        if cont.empty:
            st.info('ℹ Aún no hay datos suficientes para calcular la continuidad.')
            return

        total = len(cont)
        if total <= TOP_N_VISIBLE:
            st.plotly_chart(
                _grafico(cont, centro_id, prom_nac),
                use_container_width=True,
                config={'displayModeBar': False}
            )
        else:
            top   = cont.head(TOP_N_VISIBLE).reset_index(drop=True)
            resto = cont.iloc[TOP_N_VISIBLE:].reset_index(drop=True)
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
