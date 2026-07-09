"""
pipeline.panel.avance_centros — Reporte de avance por centro (Excel consolidado).

Columnas del Excel (rediseño aprobado por Rodrigo):
  - Código de centro
  - Ingreso (n)
  - En tratamiento (n)
  - Egreso (n)
  - Seguimiento (n)
  - Total registros TOP (suma de fases, en celda azul claro)
  - % Continuidad
  - Último TOP (formato "06 jul 2026")
  - Días sin registro
  - Estado (Verde=Al día / Amarillo=Con rezago / Rojo=Inactivo)

Función expuesta:
  boton_descarga(df, pais, centro_id=None)
  _calcular_avance(df)   — también importada por tab Reportes
  _generar_excel(df_avance, pais)
"""
import io
from datetime import datetime

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from pipeline.panel.config import (
    COLOR_VERDE, COLOR_AMARILLO, COLOR_ROJO, COLOR_GRIS,
    actividad_por_centro, continuidad_por_centro,
    SEMAFORO_UMBRAL_VERDE, SEMAFORO_UMBRAL_AMARILLO,
)

MESES_ES = ['', 'ene', 'feb', 'mar', 'abr', 'may', 'jun',
            'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def _fmt_fecha(ts):
    """Convierte Timestamp a '06 jul 2026' o '—'."""
    if pd.isna(ts):
        return '—'
    try:
        return f"{ts.day:02d} {MESES_ES[ts.month]} {ts.year}"
    except Exception:
        return '—'


def _hex(color_str):
    return 'FF' + color_str.lstrip('#').upper()


def _fill(hex_color):
    return PatternFill('solid', fgColor=_hex(hex_color))


def _font(bold=False, color='1F1F1F', size=10):
    return Font(bold=bold, color=_hex(color), size=size, name='Calibri')


def _border_thin():
    s = Side(style='thin', color='FFDDDDDD')
    return Border(left=s, right=s, top=s, bottom=s)


def _alinear(h='left', v='center', wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)


def _calcular_avance(df):
    """
    Calcula tabla de avance por centro con columnas de fase separadas.
    Retorna DataFrame con columnas:
      Código de centro, Ingreso, En tratamiento, Egreso, Seguimiento,
      Total, % Continuidad, Último TOP, Días sin registro, Estado
    """
    if df is None or df.empty or 'centro' not in df.columns:
        return pd.DataFrame()

    tmp = df.copy()
    tmp['centro'] = tmp['centro'].astype(str).str.strip()
    tmp['etapa']  = tmp['etapa'].fillna('').astype(str).str.strip()
    tmp = tmp[tmp['centro'] != '']

    etapas = ['ingreso', 'en_tratamiento', 'egreso', 'seguimiento']
    conteos = {}
    for etapa in etapas:
        conteos[etapa] = (
            tmp[tmp['etapa'] == etapa]
            .groupby('centro').size().rename(etapa)
        )

    act  = actividad_por_centro(df).set_index('centro')
    cont = continuidad_por_centro(df).set_index('centro')

    centros = sorted(tmp['centro'].unique())
    filas = []
    for c in centros:
        ing  = int(conteos['ingreso'].get(c, 0))
        trat = int(conteos['en_tratamiento'].get(c, 0))
        egr  = int(conteos['egreso'].get(c, 0))
        seg  = int(conteos['seguimiento'].get(c, 0))
        tot  = ing + trat + egr + seg

        pct  = round(cont.loc[c, 'pct_continuidad'], 1) if c in cont.index else 0.0
        ult_f = act.loc[c, 'ultima_fecha'] if c in act.index else pd.NaT
        dias  = act.loc[c, 'dias']         if c in act.index else None

        if dias is None or (isinstance(dias, float) and dias != dias):
            estado = 'Sin datos'
        elif dias <= SEMAFORO_UMBRAL_VERDE:
            estado = 'Al día'
        elif dias <= SEMAFORO_UMBRAL_AMARILLO:
            estado = 'Con rezago'
        else:
            estado = 'Inactivo'

        filas.append({
            'Código de centro':  c,
            'Ingreso':           ing,
            'En tratamiento':    trat,
            'Egreso':            egr,
            'Seguimiento':       seg,
            'Total':             tot,
            '% Continuidad':     f"{pct}%",
            'Último TOP':        _fmt_fecha(ult_f),
            'Días sin registro': int(dias) if dias is not None and dias == dias else '—',
            'Estado':            estado,
        })

    return pd.DataFrame(filas)


# ── Columnas con sus anchos y alineación ──────────────────────────────────────
_COLUMNAS = [
    ('Código de centro',  16, 'left'),
    ('Ingreso',           10, 'center'),
    ('En tratamiento',    14, 'center'),
    ('Egreso',            10, 'center'),
    ('Seguimiento',       13, 'center'),
    ('Total',             10, 'center'),   # celda azul claro
    ('% Continuidad',     13, 'center'),
    ('Último TOP',        14, 'center'),
    ('Días sin registro', 16, 'center'),
    ('Estado',            13, 'center'),
]

_COLOR_ESTADO = {
    'Al día':    '#1D9E75',
    'Con rezago':'#F0A836',
    'Inactivo':  '#E15D5D',
    'Sin datos': '#B4BAC2',
}
_COLOR_TOTAL_BG = '#D6E4F0'   # azul pálido para columna Total


def _generar_excel(df_avance, pais):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Avance por centro'

    ncols = len(_COLUMNAS)

    # Fila 1: título
    ws.merge_cells(f'A1:{get_column_letter(ncols)}1')
    ws['A1'] = f'Reporte de avance por centro · {pais}'
    ws['A1'].font      = _font(bold=True, color='1F3864', size=12)
    ws['A1'].alignment = _alinear('center')
    ws['A1'].fill      = _fill('#D6E4F0')
    ws.row_dimensions[1].height = 22

    # Fila 2: fecha generación
    ws.merge_cells(f'A2:{get_column_letter(ncols)}2')
    ws['A2'] = f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}'
    ws['A2'].font      = _font(color='777777', size=9)
    ws['A2'].alignment = _alinear('center')
    ws.row_dimensions[2].height = 14

    # Fila 3: sub-encabezado de fases
    for col_idx in range(1, ncols + 1):
        ws.cell(3, col_idx).fill      = _fill('#EBF3FB')
        ws.cell(3, col_idx).border    = _border_thin()
    ws.merge_cells('B3:F3')
    ws['B3'] = 'Fase del TOP'
    ws['B3'].font      = _font(bold=True, color='1F3864', size=9)
    ws['B3'].alignment = _alinear('center')
    ws.row_dimensions[3].height = 14

    # Fila 4: encabezados de columnas
    HDR_FILL = _fill('#004AAD')
    HDR_FONT = _font(bold=True, color='FFFFFF', size=10)
    for col_idx, (header, ancho, alin) in enumerate(_COLUMNAS, start=1):
        cell = ws.cell(row=4, column=col_idx, value=header)
        cell.font      = HDR_FONT
        cell.fill      = HDR_FILL
        cell.alignment = _alinear(alin, wrap=True)
        cell.border    = _border_thin()
        ws.column_dimensions[get_column_letter(col_idx)].width = ancho
    ws.row_dimensions[4].height = 28

    # Filas de datos (desde fila 5)
    for row_idx, (_, row) in enumerate(df_avance.iterrows(), start=5):
        alt   = row_idx % 2 == 0
        fondo = '#F7FAFC' if alt else '#FFFFFF'

        valores = [
            row['Código de centro'],
            row['Ingreso'],
            row['En tratamiento'],
            row['Egreso'],
            row['Seguimiento'],
            row['Total'],
            row['% Continuidad'],
            row['Último TOP'],
            row['Días sin registro'],
            row['Estado'],
        ]

        for col_idx, (val, (_, _, alin)) in enumerate(zip(valores, _COLUMNAS), start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font      = _font(size=10)
            cell.alignment = _alinear(alin)
            cell.border    = _border_thin()

            # Columna Total: fondo azul pálido
            if col_idx == 6:
                cell.fill = _fill(_COLOR_TOTAL_BG)
                cell.font = _font(bold=True, color='004AAD', size=10)
            # Columna Estado: fondo de color semáforo
            elif col_idx == 10:
                color_est = _COLOR_ESTADO.get(str(val), '#B4BAC2')
                cell.fill = _fill(color_est)
                cell.font = _font(bold=True, color='FFFFFF', size=10)
            else:
                cell.fill = _fill(fondo)

        ws.row_dimensions[row_idx].height = 18

    # Fila de totales
    fila_tot = len(df_avance) + 5
    for col_idx in range(1, ncols + 1):
        cell        = ws.cell(fila_tot, col_idx)
        cell.fill   = _fill('#D6E4F0')
        cell.border = _border_thin()

    ws.cell(fila_tot, 1, 'TOTAL').font      = _font(bold=True, color='1F3864', size=10)
    ws.cell(fila_tot, 1).alignment           = _alinear('center')

    for col_idx in [2, 3, 4, 5, 6]:   # Ingreso → Total
        letra = get_column_letter(col_idx)
        cell  = ws.cell(fila_tot, col_idx,
                        value=f'=SUM({letra}5:{letra}{fila_tot - 1})')
        cell.font      = _font(bold=True, color='004AAD' if col_idx == 6 else '1F3864', size=10)
        cell.alignment = _alinear('center')

    ws.freeze_panes = 'A5'

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def boton_descarga(df, pais, centro_id=None):
    if df is None or df.empty:
        st.caption('Sin datos disponibles para generar el reporte.')
        return

    df_avance = _calcular_avance(df)
    if df_avance.empty:
        st.caption('No se encontraron centros con datos.')
        return

    fecha_hoy      = datetime.now().strftime('%Y%m%d')
    nombre_archivo = f'avance_{pais.lower().replace(" ", "_")}_{fecha_hoy}.xlsx'

    st.markdown(
        f'<div style="font-size:.78rem;color:#555;margin-bottom:.4rem;">'
        f'  {len(df_avance)} centros · datos al {datetime.now().strftime("%d/%m/%Y")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    excel_bytes = _generar_excel(df_avance, pais)
    st.download_button(
        label='⬇️  Descargar Excel de avance',
        data=excel_bytes,
        file_name=nombre_archivo,
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        use_container_width=True,
    )
