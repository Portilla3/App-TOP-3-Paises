"""
pipeline.panel.reportes_centro — Pestaña de Reportes para el panel de centro.

Misma estética que la pestaña "Reportes" del panel de país (clases CSS
rep-quick-card, badges), pero con alcance acotado a la descarga del Excel
propio del centro. No replica el pipeline completo de Word/PPT (procesar_wide),
que está pensado para consolidados de país; si más adelante se necesita un
Word/PPT individual por centro, se construye como extensión de este módulo.

Función expuesta: render(df, centro)
"""
import streamlit as st
import pandas as pd
import tempfile


def render(df, centro):
    st.markdown("""
    <style>
    .rep-quick-card    {background:white;border:1px solid #E5E5E5;border-radius:10px;
                        padding:1rem 1.2rem;display:flex;align-items:center;gap:1rem;margin-bottom:.3rem;}
    .rep-quick-icon    {font-size:2rem;flex-shrink:0;}
    .rep-quick-title   {font-size:.95rem;font-weight:700;color:#1F3864;}
    .rep-quick-desc    {font-size:.75rem;color:#666;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:.8rem;padding:.3rem 0 .8rem 0;">'
        f'  <span style="background:#E8F0FE;color:#004AAD;font-size:.78rem;font-weight:600;'
        f'  padding:.3rem .8rem;border-radius:20px;">&#128452; Datos de {centro}</span>'
        f'  <span style="color:#888;font-size:.8rem;">'
        f'  <b style="color:#1F3864">{len(df) if df is not None else 0:,}</b> registros disponibles</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    if df is None or df.empty:
        st.info('Sin registros todavía para este centro.')
        return

    st.markdown(
        '<div class="rep-quick-card">'
        '  <div class="rep-quick-icon">📊</div>'
        '  <div>'
        '    <div class="rep-quick-title">Excel con todos mis registros</div>'
        '    <div class="rep-quick-desc">Todos los campos del instrumento TOP, sin filtros, para uso interno del centro</div>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True
    )

    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    df.to_excel(tmp.name, index=False)
    tmp.close()

    with open(tmp.name, 'rb') as f:
        st.download_button(
            '⬇️ Descargar Excel',
            data=f.read(),
            file_name=f'QALAT_{centro}_{pd.Timestamp.now().strftime("%Y%m%d")}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True,
            key='btn_descarga_centro',
        )

    st.caption('¿Necesitas un reporte con gráficos en Word o PowerPoint como los que recibe tu país? '
               'Coméntaselo a tu coordinador nacional para evaluarlo en una próxima actualización.')
