"""
pipeline.panel.transgresion — Transgresión a la ley al ingreso.

Muestra qué porcentaje de pacientes al ingreso declaró haber cometido
al menos un acto de transgresión a la ley en las últimas 4 semanas,
más un desglose por tipo.

Columnas Supabase usadas: hurto, robo, venta_droga, rina_pelea (valores 'S'/'N').
Solo registros con etapa='ingreso'.

Diseño:
  - Dona central: % con al menos una transgresión vs % sin transgresión
  - Texto central: porcentaje principal
  - Debajo de la dona: 4 íconos con conteo por tipo (hurto, robo, venta, riña)

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion


# Columnas Supabase → etiqueta e ícono
TIPOS_TRANSGRESION = [
    ('hurto',       'Hurto',          '🛍'),
    ('robo',        'Robo',           '⚠️'),
    ('venta_droga', 'Venta de droga', '💊'),
    ('rina_pelea',  'Riña / Pelea',   '👊'),
]

COLOR_CON    = '#D95F5F'   # from config PALETA_ROJO
COLOR_SIN    = '#F2F4F7'   # from config PALETA_FONDO_REF
TEXTO_OSCURO = '#004AAD'


def _calcular_transgresion(df):
    """
    Filtra etapa=ingreso y calcula:
      - n_con: pacientes con al menos una transgresión ('S' en alguna columna)
      - n_sin: pacientes sin ninguna
      - por tipo: n con 'S' en cada columna

    Retorna dict o None si no hay datos suficientes.
    """
    cols_req = {'etapa'}
    if df is None or df.empty or not cols_req.issubset(df.columns):
        return None

    df_ing = df[df['etapa'].astype(str).str.strip() == 'ingreso'].copy()
    if df_ing.empty:
        return None

    # Columnas disponibles (puede que algún país no tenga todas)
    cols_disponibles = [(col, lbl, ico)
                        for col, lbl, ico in TIPOS_TRANSGRESION
                        if col in df_ing.columns]

    if not cols_disponibles:
        return None

    # Normalizar: 'S'/'N'/None → True/False/None
    def _es_s(v):
        if pd.isna(v):
            return False
        return str(v).strip().upper() in ('S', 'SI', 'SÍ', 'YES', '1', 'TRUE')

    n_total = len(df_ing)
    por_tipo = []
    mask_alguna = pd.Series([False] * n_total, index=df_ing.index)

    for col, lbl, ico in cols_disponibles:
        mask = df_ing[col].apply(_es_s)
        mask_alguna = mask_alguna | mask
        por_tipo.append({
            'col': col, 'label': lbl, 'icono': ico,
            'n': int(mask.sum()),
        })

    n_con = int(mask_alguna.sum())
    n_sin = n_total - n_con
    pct_con = round(n_con / n_total * 100, 1) if n_total > 0 else 0

    return {
        'n_total': n_total,
        'n_con':   n_con,
        'n_sin':   n_sin,
        'pct_con': pct_con,
        'por_tipo': por_tipo,
    }


def _figura_dona(datos):
    """Dona central con % transgresión."""
    pct_con = datos['pct_con']
    pct_sin = round(100 - pct_con, 1)

    fig = go.Figure(go.Pie(
        values=[datos['n_con'], datos['n_sin']],
        labels=['Con transgresión', 'Sin transgresión'],
        hole=0.65,
        marker_colors=[COLOR_CON, COLOR_SIN],
        textinfo='none',
        hovertemplate='%{label}: %{value} pacientes (%{percent})<extra></extra>',
        sort=False,
    ))

    # Texto central: porcentaje
    fig.add_annotation(
        text=f"<b>{pct_con}%</b>",
        x=0.5, y=0.55,
        font=dict(size=26, color=COLOR_CON, family='Inter, sans-serif'),
        showarrow=False,
    )
    fig.add_annotation(
        text='con transgresión',
        x=0.5, y=0.38,
        font=dict(size=10, color='#777', family='Inter, sans-serif'),
        showarrow=False,
    )

    fig.update_layout(
        height=200,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        font=dict(family='Inter, sans-serif', color=TEXTO_OSCURO),
    )
    return fig


def render(df, pais, centro_id=None):
    """Renderiza el componente de transgresión a la ley."""
    with st.container(border=True):
        st.markdown(
            titulo_seccion(
                '⚖️', 'Transgresión a la ley',
                'actos declarados en las últimas 4 semanas · solo pacientes al ingreso'
            ),
            unsafe_allow_html=True,
        )

        if centro_id:
            df = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()

        datos = _calcular_transgresion(df)

        if datos is None:
            st.caption('Sin datos de transgresión disponibles para este país.')
            return

        # Dona
        st.plotly_chart(_figura_dona(datos), use_container_width=True,
                        config={'displayModeBar': False})

        # Desglose por tipo: solo % arriba en rojo y label abajo
        if datos['por_tipo']:
            cols = st.columns(len(datos['por_tipo']))
            for i, tipo in enumerate(datos['por_tipo']):
                pct_tipo = round(tipo['n'] / datos['n_total'] * 100, 1) if datos['n_total'] > 0 else 0
                with cols[i]:
                    st.markdown(
                        f'<div style="text-align:center;padding:.3rem 0;">'
                        f'  <div style="font-size:1.1rem;font-weight:700;color:{COLOR_CON};">'
                        f'    {pct_tipo}%'
                        f'  </div>'
                        f'  <div style="font-size:.68rem;color:#777;line-height:1.3;">'
                        f'    {tipo["label"]}'
                        f'  </div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # Nota al pie
        st.markdown(
            f'<div style="font-size:.68rem;color:#999;margin-top:.3rem;">'
            f'  N total: {datos["n_total"]} pacientes al ingreso · '
            f'  {datos["n_con"]} con al menos una transgresión declarada · '
            f'  los % por tipo no suman el total porque un paciente puede declarar más de un acto'
            f'</div>',
            unsafe_allow_html=True,
        )
