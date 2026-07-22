"""
pipeline.panel.reportes_centro — Pestaña de Reportes para el panel de centro.

Reutiliza el mismo motor que usa el país (procesar_wide + run_script), con
filtro_centro fijo al centro de la sesión. Misma estética (rep-quick-card,
rep-section-title) que la pestaña de Reportes del país.

Función expuesta: render(df_pais_raw, centro, rename_map)
"""
import streamlit as st
import tempfile, os

from pipeline.wide_top import procesar_wide
from pipeline.runner import run_script

LABELS = {
    'caract_excel': ('📋 Excel de ingreso', 'Excel', '11 tablas: sexo, edad, sustancias, transgresión'),
    'pdf_caract':   ('📄 Word de ingreso', 'Word', '4 secciones · gráficos · tablas'),
    'pptx_caract':  ('📑 PowerPoint de ingreso', 'PowerPoint', '6 slides · perfil al ingreso'),
    'seg_excel':    ('📋 Excel de seguimiento', 'Excel', 'Comparativo TOP1 vs TOP2'),
    'pdf_seg':      ('📄 Word de seguimiento', 'Word', 'Comparativo ingreso vs seguimiento'),
    'pptx_seg':     ('📑 PowerPoint de seguimiento', 'PowerPoint', '6 slides · ingreso vs seguimiento'),
}
_ICONO_FMT = {'Excel': '📋', 'Word': '📄', 'PowerPoint': '📑'}


def _preparar_raw_path(df_pais_raw, rename_map):
    d = df_pais_raw.rename(columns={k: v for k, v in rename_map.items() if k in df_pais_raw.columns})
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    d.to_excel(tmp.name, index=False)
    tmp.close()
    return tmp.name


def _boton_reporte(col, key, centro, raw_path):
    lbl, fmt, desc = LABELS[key]
    with col:
        st.markdown(
            f'<div class="rep-quick-card"><div class="rep-quick-icon">{_ICONO_FMT[fmt]}</div>'
            f'<div><div class="rep-quick-title">{lbl}</div><div class="rep-quick-desc">{desc}</div></div></div>',
            unsafe_allow_html=True,
        )
        if st.button(f'Generar {fmt}', key=f'btn_gen_centro_{key}', use_container_width=True):
            with st.spinner(f'Generando {lbl}...'):
                try:
                    _wr = procesar_wide(raw_path, filtro_centro=centro)
                    _wd = tempfile.mkdtemp(prefix='qalat_centro_')
                    _wp = os.path.join(_wd, 'TOP_Base_Wide.xlsx')
                    with open(_wp, 'wb') as f:
                        f.write(_wr['excel_bytes'].getvalue())
                    _buf, _fn, _mi = run_script(key, _wp, filtro_centro=centro)
                    st.session_state[f'dl_centro_{key}'] = (_buf, _fn, _mi)
                except Exception as e:
                    st.error(f'Error: {str(e)[:200]}')
        if f'dl_centro_{key}' in st.session_state:
            _b, _f2, _m = st.session_state[f'dl_centro_{key}']
            st.download_button(f'⬇️ Descargar {fmt}', data=_b.getvalue(), file_name=_f2, mime=_m,
                                use_container_width=True, key=f'save_centro_{key}')


def render(df_pais_raw, centro, rename_map):
    st.markdown("""
    <style>
    .rep-section-title {font-size:1rem;font-weight:700;color:#004AAD;margin:1rem 0 .15rem 0;}
    .rep-section-sub   {font-size:.75rem;color:#888;margin-bottom:.7rem;}
    .rep-quick-card    {background:white;border:1px solid #E5E5E5;border-radius:10px;
                        padding:1rem 1.2rem;display:flex;align-items:center;gap:1rem;margin-bottom:.5rem;
                        min-height:88px;}
    .rep-quick-icon    {font-size:2rem;flex-shrink:0;}
    .rep-quick-title   {font-size:.9rem;font-weight:700;color:#1F3864;}
    .rep-quick-desc    {font-size:.72rem;color:#666;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f'<span class="badge badge-centro">🏥 Reportes — {centro}</span>', unsafe_allow_html=True)
    st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)

    if df_pais_raw is None or df_pais_raw.empty:
        st.info('Sin registros todavía para este centro.')
        return

    raw_path = _preparar_raw_path(df_pais_raw, rename_map)

    st.markdown(
        '<div class="rep-section-title">Reportes de ingreso</div>'
        '<div class="rep-section-sub">caracterización de tus pacientes al momento del ingreso</div>',
        unsafe_allow_html=True
    )
    c1, c2, c3 = st.columns(3, gap='small')
    _boton_reporte(c1, 'caract_excel', centro, raw_path)
    _boton_reporte(c2, 'pdf_caract', centro, raw_path)
    _boton_reporte(c3, 'pptx_caract', centro, raw_path)

    st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rep-section-title">Reportes de seguimiento</div>'
        '<div class="rep-section-sub">comparativo TOP de ingreso vs. seguimiento</div>',
        unsafe_allow_html=True
    )
    c4, c5, c6 = st.columns(3, gap='small')
    _boton_reporte(c4, 'seg_excel', centro, raw_path)
    _boton_reporte(c5, 'pdf_seg', centro, raw_path)
    _boton_reporte(c6, 'pptx_seg', centro, raw_path)
