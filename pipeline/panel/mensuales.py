"""
pipeline.panel.mensuales — Registros TOP por mes calendario + curva acumulada.

Muestra:
  - Barras verticales azules con el número de registros TOP por mes
    (cualquier etapa: ingreso, en_tratamiento, egreso, seguimiento)
  - Área acumulada verde translúcida de fondo (efecto "cerro creciente")
  - Últimos 12 meses por defecto (o menos si el país tiene poca historia)

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion


COLOR_BARRA     = '#2E75B6'    # azul MID
COLOR_ACUMULADO = '#8BC34A'    # verde suave (mismo que semáforo activo)
TEXTO_OSCURO    = '#1F3864'


MESES_MAX = 12   # ventana móvil de los últimos 12 meses

NOMBRES_MES = {
    1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic',
}


def _calcular_mensual(df, meses=MESES_MAX, hoy=None):
    """
    Calcula el conteo mensual y el acumulado.

    Returns:
        pd.DataFrame con columnas: periodo (Timestamp inicio del mes),
        etiqueta (str "Mes YY"), n (int), acumulado (int).
        Ventana móvil de los últimos `meses` meses hasta hoy.
    """
    if hoy is None:
        hoy = pd.Timestamp.now().normalize()

    if df is None or df.empty or 'fecha_entrevista' not in df.columns:
        return pd.DataFrame(columns=['periodo', 'etiqueta', 'n', 'acumulado'])

    tmp = df.copy()
    tmp['fecha_entrevista'] = pd.to_datetime(tmp['fecha_entrevista'], errors='coerce')
    tmp = tmp[tmp['fecha_entrevista'].notna()]
    if tmp.empty:
        return pd.DataFrame(columns=['periodo', 'etiqueta', 'n', 'acumulado'])

    # Primer día del mes de cada fecha
    tmp['periodo'] = tmp['fecha_entrevista'].dt.to_period('M').dt.to_timestamp()

    # Ventana móvil: desde (hoy - meses) hasta el mes actual
    inicio = (hoy.to_period('M') - (meses - 1)).to_timestamp()
    fin    = hoy.to_period('M').to_timestamp()

    # Conteo por periodo dentro de la ventana
    conteo = tmp.groupby('periodo').size().reset_index(name='n')
    conteo = conteo[(conteo['periodo'] >= inicio) & (conteo['periodo'] <= fin)]

    # Rellenar meses sin registros con 0 para que la barra aparezca vacía
    todos_los_meses = pd.date_range(start=inicio, end=fin, freq='MS')
    completo = pd.DataFrame({'periodo': todos_los_meses})
    completo = completo.merge(conteo, on='periodo', how='left').fillna({'n': 0})
    completo['n'] = completo['n'].astype(int)

    completo = completo.sort_values('periodo').reset_index(drop=True)

    completo['etiqueta'] = completo['periodo'].apply(
        lambda p: f"{NOMBRES_MES[p.month]} {str(p.year)[-2:]}"
    )
    completo['acumulado'] = completo['n'].cumsum()

    return completo


def render(df, pais, centro_id=None):
    """
    Pinta las barras mensuales con la curva acumulada de fondo.
    """
    with st.container(border=True):
        # Filtrado opcional por centro
        if centro_id and 'centro' in df.columns:
            df_local = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()
        else:
            df_local = df

        mensual = _calcular_mensual(df_local)

        # Título con el total acumulado en el subtítulo
        total = int(mensual['n'].sum()) if not mensual.empty else 0
        st.markdown(
            titulo_seccion(
                '📅', 'Registros mensuales',
                f'últimos {MESES_MAX} meses · {total} registros en el período'
            ),
            unsafe_allow_html=True
        )

        if mensual.empty or total == 0:
            st.info('ℹ Aún no hay registros con fecha de entrevista en el período.')
            return

        fig = go.Figure()

        # Área acumulada de fondo (verde translúcido)
        fig.add_trace(go.Scatter(
            x=mensual['etiqueta'],
            y=mensual['acumulado'],
            mode='lines',
            fill='tozeroy',
            fillcolor='rgba(139, 195, 74, 0.20)',
            line=dict(color='rgba(139, 195, 74, 0.65)', width=2, shape='spline'),
            name='Acumulado',
            hovertemplate='<b>%{x}</b><br>Acumulado: %{y}<extra></extra>',
        ))

        # Barras verticales del conteo mensual
        max_n = int(mensual['n'].max()) if not mensual.empty else 1
        textos = [str(v) if v > 0 else '' for v in mensual['n']]
        fig.add_trace(go.Bar(
            x=mensual['etiqueta'],
            y=mensual['n'],
            marker=dict(color=COLOR_BARRA, line=dict(width=0)),
            text=textos,
            textposition='outside',
            textfont=dict(color=TEXTO_OSCURO, size=11, family='Arial'),
            name='Registros del mes',
            hovertemplate='<b>%{x}</b><br>Registros: %{y}<extra></extra>',
            cliponaxis=False,
        ))

        # Escala del eje Y: el máximo entre el pico mensual y el acumulado.
        # El acumulado siempre gana, así que el eje se define por él.
        max_acum = int(mensual['acumulado'].max()) if not mensual.empty else 1
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=10, b=20),
            barmode='overlay',
            bargap=0.25,
            showlegend=False,
            xaxis=dict(
                tickfont=dict(size=11, color=TEXTO_OSCURO, family='Arial'),
                fixedrange=True,
                showgrid=False,
            ),
            yaxis=dict(
                visible=False,
                range=[0, max_acum * 1.12],
                fixedrange=True,
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
