"""
pipeline.panel.reportes_centro — Pestaña de Reportes para el panel de centro.

Reutiliza el mismo motor que usa el país (procesar_wide + run_script), con
filtro_centro fijo al centro de la sesión. Misma estética (rep-card con íconos
SVG de Microsoft) que la pestaña de Reportes del país.

Función expuesta: render(df_pais_raw, centro, rename_map)
"""
import streamlit as st
import tempfile, os

from pipeline.wide_top import procesar_wide
from pipeline.runner import run_script

LABELS = {
    'caract_excel': ('Excel de ingreso', 'Excel', '11 tablas: sexo, edad, sustancias, transgresión'),
    'pdf_caract':   ('Word de ingreso', 'Word', '4 secciones · gráficos · tablas'),
    'pptx_caract':  ('PowerPoint de ingreso', 'PowerPoint', '6 slides · perfil al ingreso'),
    'seg_excel':    ('Excel de seguimiento', 'Excel', 'Comparativo TOP1 vs TOP2'),
    'pdf_seg':      ('Word de seguimiento', 'Word', 'Comparativo ingreso vs seguimiento'),
    'pptx_seg':     ('PowerPoint de seguimiento', 'PowerPoint', '6 slides · ingreso vs seguimiento'),
}

# Íconos SVG con colores clásicos de Microsoft (idénticos al perfil país)
_ICONOS_SVG = {
    'excel': (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1D7C3F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="18" height="18" rx="2"/>'
        '<line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/>'
        '<line x1="9" y1="9" x2="9" y2="21"/><line x1="15" y1="9" x2="15" y2="21"/>'
        '</svg>'
    ),
    'word': (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2B579A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/>'
        '<line x1="8" y1="9" x2="10" y2="9"/>'
        '</svg>'
    ),
    'pptx': (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C43E1C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="2" y="3" width="20" height="14" rx="2"/>'
        '<line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'
        '<polyline points="7 10 10 7 13 10 17 7"/>'
        '</svg>'
    ),
}
_ICON_BG = {'excel': '#E6F4EC', 'word': '#E8EEF8', 'pptx': '#FAEAE6'}
_ACCENT  = {'excel': '#1D7C3F', 'word': '#2B579A', 'pptx': '#C43E1C'}


def _tipo_card(key):
    if 'excel' in key or 'wide' in key: return 'excel'
    if 'word'  in key or 'pdf' in key:  return 'word'
    return 'pptx'


def _preparar_raw_path(df_pais_raw, rename_map):
    d = df_pais_raw.rename(columns={k: v for k, v in rename_map.items() if k in df_pais_raw.columns})
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    d.to_excel(tmp.name, index=False)
    tmp.close()
    return tmp.name


def _boton_reporte(col, key, centro, raw_path):
    lbl, fmt, desc = LABELS[key]
    _tipo = _tipo_card(key)
    _svg  = _ICONOS_SVG[_tipo]
    _ibg  = _ICON_BG[_tipo]
    _acc  = _ACCENT[_tipo]
    with col:
        st.markdown(
            f'<div class="rep-card">'
            f'  <div class="rep-card-accent" style="background:{_acc};"></div>'
            f'  <div class="rep-card-icon" style="background:{_ibg};">{_svg}</div>'
            f'  <div class="rep-card-title">{lbl}</div>'
            f'  <div class="rep-card-desc">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="height:.3rem"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<style>'
            f'.btn-wrap-centro-{key} button{{'
            f'background:{_acc} !important;color:white !important;'
            f'border:none !important;font-weight:600 !important;}}'
            f'.btn-wrap-centro-{key} button:hover{{opacity:.88 !important;'
            f'background:{_acc} !important;}}'
            f'</style>'
            f'<div class="btn-wrap-centro-{key}">',
            unsafe_allow_html=True
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
        st.markdown('</div>', unsafe_allow_html=True)
        if f'dl_centro_{key}' in st.session_state:
            _b, _f2, _m = st.session_state[f'dl_centro_{key}']
            st.download_button(f'⬇️ Descargar {fmt}', data=_b.getvalue(), file_name=_f2, mime=_m,
                                use_container_width=True, key=f'save_centro_{key}')


def render(df_pais_raw, centro, rename_map):
    st.markdown("""
    <style>
    .rep-section-title {font-size:1rem;font-weight:700;color:#004AAD;margin:1rem 0 .15rem 0;}
    .rep-section-sub   {font-size:.75rem;color:#888;margin-bottom:.7rem;}
    .rep-card          {background:white;border:1px solid #E5E5E5;border-radius:10px;
                        padding:0 1.1rem 1.1rem 1.1rem;overflow:hidden;position:relative;}
    .rep-card-accent   {height:4px;margin:0 -1.1rem 1rem -1.1rem;}
    .rep-card-icon     {width:36px;height:36px;border-radius:8px;display:flex;
                        align-items:center;justify-content:center;margin-bottom:.6rem;
                        font-size:1.1rem;}
    .rep-card-title    {font-size:.95rem;font-weight:700;color:#1F3864;margin-bottom:.2rem;}
    .rep-card-desc     {font-size:.78rem;color:#666;min-height:2.5rem;}
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
