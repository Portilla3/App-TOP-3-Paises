"""
app.py — QALAT · Sistema de Monitoreo de Resultados de Tratamiento
v5.2 — login por país · Perú / Ecuador / México / México CIJ / El Salvador / UNODC
       + pestaña Corrección de registros (editar / eliminar en Supabase)
"""
import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import tempfile, os, sys
from io import BytesIO
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline.wide_top import procesar_wide
from pipeline.runner   import run_script, run_paquetes_centros
from pipeline.panel.data import cargar_datos_pais, invalidar_cache_pais
from pipeline.panel     import metricas    as panel_metricas
from pipeline.panel     import semaforo    as panel_semaforo
from pipeline.panel     import mensuales   as panel_mensuales
from pipeline.panel     import ranking     as panel_ranking
from pipeline.panel     import continuidad as panel_continuidad
from pipeline.panel     import piramide       as panel_piramide
from pipeline.panel     import sustancia      as panel_sustancia
from pipeline.panel     import dias_consumo   as panel_dias_consumo
from pipeline.panel     import transgresion   as panel_transgresion
from pipeline.panel     import avance_centros as panel_avance_centros
from pipeline.panel     import edad           as panel_edad
from pipeline.panel     import salud          as panel_salud

NAVY='#1F3864'; MID='#2E75B6'; ACCENT='#00B0F0'
ORANGE='#C8590A'; RED='#C00000'; GREEN='#538135'; WHITE='#FFFFFF'

st.set_page_config(
    page_title='QALAT · TOP · Sistema de Monitoreo de Resultados de Tratamiento',
    page_icon='📊', layout='wide', initial_sidebar_state='collapsed'
)

st.markdown(f"""<style>
html,body,[class*="css"]{{font-family:'Calibri',sans-serif;}}
.main{{background:#F8FAFD;}}
/* Reducir padding lateral del contenedor principal para aprovechar el ancho */
.main .block-container{{padding-left:1.6rem;padding-right:1.6rem;padding-top:1rem;max-width:none;}}
/* Container border compacto (para st.container(border=True)) */
div[data-testid="stVerticalBlockBorderWrapper"]{{padding:.5rem .7rem !important;}}
/* ── Altura uniforme de cards por fila de perfil ── */
/* Altura uniforme por fila: fuerza el wrapper a altura fija */
.panel-fila-1 div[data-testid="stVerticalBlockBorderWrapper"] {{
    min-height:300px !important;
    display:flex !important;
    flex-direction:column !important;
}}
.panel-fila-2 div[data-testid="stVerticalBlockBorderWrapper"] {{
    min-height:360px !important;
    display:flex !important;
    flex-direction:column !important;
}}
.panel-fila-3 div[data-testid="stVerticalBlockBorderWrapper"] {{
    min-height:390px !important;
    display:flex !important;
    flex-direction:column !important;
}}
/* ── Separador de sección ── */
.seccion-panel {{
    display:flex;align-items:center;gap:.6rem;
    margin:.4rem 0 .5rem 0;
}}
.seccion-panel-titulo {{
    font-size:1rem;font-weight:700;color:#004AAD;
    white-space:nowrap;letter-spacing:.01em;
}}
.seccion-panel-linea {{
    flex:1;height:1px;background:#004AAD;opacity:.2;
}}
.seccion-panel-sub {{
    font-size:.7rem;color:#9AA5B4;white-space:nowrap;
}}

/* ── Pestañas estilo botones pill ────────────────────────────────────────── */
/* Contenedor de tabs: fondo gris claro, borde redondeado */
div[data-baseweb="tab-list"] {{
    background:#F0F4F8 !important;
    border-radius:10px !important;
    padding:4px !important;
    gap:4px !important;
    border:none !important;
    box-shadow:none !important;
}}
/* Línea inferior del tab-list (quitarla) */
div[data-baseweb="tab-highlight"] {{
    display:none !important;
}}
div[data-baseweb="tab-border"] {{
    display:none !important;
}}
/* Cada pestaña inactiva */
button[data-baseweb="tab"] {{
    border-radius:8px !important;
    padding:.4rem 1.1rem !important;
    font-size:.88rem !important;
    font-weight:600 !important;
    color:#6B7A90 !important;
    background:transparent !important;
    border:none !important;
    transition:all .15s ease !important;
}}
button[data-baseweb="tab"]:hover {{
    background:#E0E8F4 !important;
    color:#004AAD !important;
}}
/* Pestaña activa */
button[data-baseweb="tab"][aria-selected="true"] {{
    background:white !important;
    color:#004AAD !important;
    box-shadow:0 1px 4px rgba(0,74,173,.15) !important;
    border-radius:8px !important;
}}
/* Icono/emoji dentro de la pestaña */
button[data-baseweb="tab"] p {{
    font-size:.88rem !important;
    font-weight:600 !important;
    margin:0 !important;
}}
.qalat-hdr{{background:{NAVY};color:white;padding:1.2rem 2rem;border-radius:8px;margin-bottom:1.5rem;border-left:8px solid {MID};}}
.qalat-hdr h1{{color:white;font-size:1.6rem;margin:0;}}
.qalat-hdr h1 .instrumento{{font-size:2.2rem;font-weight:900;color:#9DC3E6;margin-left:.2rem;}}
.qalat-hdr p{{color:#BDD7EE;font-size:.9rem;margin:.3rem 0 0 0;}}
.kpi{{background:white;border-radius:8px;padding:1rem 1.2rem;border-left:4px solid {MID};
      box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:.5rem;}}
.kpi.red{{border-left-color:{RED};}}.kpi.orange{{border-left-color:{ORANGE};}}.kpi.green{{border-left-color:{GREEN};}}
.kpi-lbl{{font-size:.78rem;color:#666;margin-bottom:.2rem;}}
.kpi-val{{font-size:1.8rem;font-weight:700;color:{NAVY};}}
.kpi-sub{{font-size:.75rem;color:#888;}}
.sec{{background:{MID};color:white;padding:.5rem 1rem;border-radius:6px;
      font-weight:600;font-size:1rem;margin:1.2rem 0 .8rem 0;}}
.filter-box{{background:white;border:1px solid #D0DFF0;border-radius:8px;padding:1rem 1.2rem;margin-bottom:1rem;}}
.filter-box h4{{color:{NAVY};margin:0 0 .6rem 0;font-size:.95rem;}}
.outcard{{background:white;border-radius:8px;padding:1rem;border:1px solid #D0DFF0;margin-bottom:.5rem;}}
.outcard h4{{color:{NAVY};margin:0 0 .3rem 0;font-size:.95rem;}}
.outcard p{{color:#666;font-size:.8rem;margin:0;}}
.badge{{display:inline-block;padding:3px 10px;border-radius:12px;font-size:.78rem;font-weight:600;margin-right:4px;}}
.badge-centro{{background:#E8F0FE;color:{NAVY};}}
.badge-periodo{{background:#E8F5E9;color:#1B5E20;}}
.login-box{{max-width:420px;margin:3rem auto;background:white;border-radius:12px;
            padding:2rem 2.5rem;box-shadow:0 4px 20px rgba(31,56,100,.12);
            border-top:5px solid {MID};}}
div.stButton>button{{background:#1E7E34;color:white;border:none;
    padding:.6rem 2rem;border-radius:6px;font-size:1rem;font-weight:600;width:100%;
    box-shadow:0 2px 6px rgba(30,126,52,.35);letter-spacing:.3px;}}
div.stButton>button:hover{{background:#145222;box-shadow:0 3px 10px rgba(30,126,52,.5);}}
#MainMenu,footer,header{{visibility:hidden;}}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PAÍSES
# Para agregar México u otro país: solo añadir entrada aquí y PASSWORD_X en Secrets
# ══════════════════════════════════════════════════════════════════════════════
PAISES_CONFIG = {
    'Perú':         {'flag': '🇵🇪', 'color': MID},
    'Ecuador':      {'flag': '🇪🇨', 'color': '#007A5E'},
    'México':       {'flag': '🇲🇽', 'color': '#006847'},
    'México CIJ':   {'flag': '🇲🇽', 'color': '#004A97'},
    'El Salvador':  {'flag': '🇸🇻', 'color': '#0F47AF'},
    'UNODC':        {'flag': '🌐', 'color': NAVY},
}
PAISES_ACTIVOS = ['Perú', 'Ecuador', 'México', 'México CIJ', 'El Salvador']   # ← agregar aquí para sumar países

SECRET_KEY_MAP = {
    'Perú':        'PASSWORD_PERU',
    'Ecuador':     'PASSWORD_ECUADOR',
    'México':      'PASSWORD_MEXICO',
    'México CIJ':  'PASSWORD_MEXICOCIJ',
    'El Salvador': 'PASSWORD_ELSALVADOR',
    'UNODC':       'PASSWORD_UNODC',
}

LABELS = {
    'caract_excel': ('📋 Tablas caracterización', 'Excel',      '11 tablas al ingreso: sexo, edad, sustancias, transgresión'),
    'seg_excel':    ('📋 Tablas seguimiento',      'Excel',      'Comparativo TOP1 vs TOP2'),
    'pdf_caract':   ('📄 Word caracterización',    'Word',       '4 secciones · gráficos · tablas'),
    'pdf_seg':      ('📄 Word seguimiento',        'Word',       'Comparativo ingreso vs seguimiento'),
    'pptx_caract':  ('📑 PPT caracterización',     'PowerPoint', '6 slides · perfil al ingreso'),
    'pptx_seg':     ('📑 PPT seguimiento',         'PowerPoint', '6 slides · ingreso vs seguimiento'),
}

RENAME_MAP = {
    'codigo_paciente':     'Código de identificación del paciente',
    'fecha_entrevista':    'Fecha entrevista TOP',
    'fecha_nacimiento':    'Fecha de nacimiento',
    'centro':              'Código del centro de tratamiento',
    'etapa':               'Etapa',
    'sexo':                'Sexo',
    'nombre_entrevistador':'Nombre entrevistador',
    'sustancia_principal': '¿Cuál considera que es la sustancia principal que genera más problemas?',
    'alcohol_s4':          'Alcohol Última Semana (0-7)',
    'alcohol_s3':          'Alcohol Semana 3 (0-7)',
    'alcohol_s2':          'Alcohol Semana 2 (0-7)',
    'alcohol_s1':          'Alcohol Semana 1 (0-7)',
    'alcohol_total':       'Alcohol Total (0-28)',
    'alcohol_prom':        'Alcohol Promedio/día',
    'marihuana_s4':        'Marihuana Última Semana (0-7)',
    'marihuana_s3':        'Marihuana Semana 3 (0-7)',
    'marihuana_s2':        'Marihuana Semana 2 (0-7)',
    'marihuana_s1':        'Marihuana Semana 1 (0-7)',
    'marihuana_total':     'Marihuana Total (0-28)',
    'marihuana_prom':      'Marihuana Promedio/día',
    'pastabase_s4':        'Pasta Base Última Semana (0-7)',
    'pastabase_s3':        'Pasta Base Semana 3 (0-7)',
    'pastabase_s2':        'Pasta Base Semana 2 (0-7)',
    'pastabase_s1':        'Pasta Base Semana 1 (0-7)',
    'pastabase_total':     'Pasta Base Total (0-28)',
    'pastabase_prom':      'Pasta Base Promedio/día',
    'cocaina_s4':          'Cocaína Última Semana (0-7)',
    'cocaina_s3':          'Cocaína Semana 3 (0-7)',
    'cocaina_s2':          'Cocaína Semana 2 (0-7)',
    'cocaina_s1':          'Cocaína Semana 1 (0-7)',
    'cocaina_total':       'Cocaína Total (0-28)',
    'cocaina_prom':        'Cocaína Promedio/día',
    'sedantes_s4':         'Sedantes Última Semana (0-7)',
    'sedantes_s3':         'Sedantes Semana 3 (0-7)',
    'sedantes_s2':         'Sedantes Semana 2 (0-7)',
    'sedantes_s1':         'Sedantes Semana 1 (0-7)',
    'sedantes_total':      'Sedantes Total (0-28)',
    'sedantes_prom':       'Sedantes Promedio/día',
    'hurto':               'Hurto',
    'robo':                'Robo',
    'venta_droga':         'Venta de droga',
    'rina_pelea':          'Riña/Pelea',
    'vif_s4':              'VIF Última Semana (0-7)',
    'vif_s3':              'VIF Semana 3 (0-7)',
    'vif_s2':              'VIF Semana 2 (0-7)',
    'vif_s1':              'VIF Semana 1 (0-7)',
    'vif_total':           'VIF Total (0-28)',
    'salud_psicologica':   'Salud Psicológica (0-20)',
    'salud_fisica':        'Salud Física (0-20)',
    'calidad_vida':        'Calidad de Vida (0-20)',
    'dias_trabajo_s4':     'Trabajo Última Semana (0-7)',
    'dias_trabajo_s3':     'Trabajo Semana 3 (0-7)',
    'dias_trabajo_s2':     'Trabajo Semana 2 (0-7)',
    'dias_trabajo_s1':     'Trabajo Semana 1 (0-7)',
    'dias_trabajo_total':  'Trabajo Total (0-28)',
    'dias_educacion_s4':   'Educación Última Semana (0-7)',
    'dias_educacion_s3':   'Educación Semana 3 (0-7)',
    'dias_educacion_s2':   'Educación Semana 2 (0-7)',
    'dias_educacion_s1':   'Educación Semana 1 (0-7)',
    'dias_educacion_total':'Educación Total (0-28)',
    'vivienda_estable':    'Vivienda estable',
    'vivienda_basica':     'Vivienda básica',
}


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS SUPABASE
# ══════════════════════════════════════════════════════════════════════════════
def _sb_headers():
    return {
        'apikey':        st.secrets['SUPABASE_KEY'],
        'Authorization': f"Bearer {st.secrets['SUPABASE_KEY']}",
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
    }

def _sb_url(tabla='top_registros'):
    return f"{st.secrets['SUPABASE_URL']}/rest/v1/{tabla}"

def _cargar_supabase(pais=None):
    import urllib.request, urllib.parse, json
    url = _sb_url() + '?select=*&order=fecha_entrevista.asc'
    if pais and pais != 'Todos':
        url += f"&pais=eq.{urllib.parse.quote(pais)}"
    req = urllib.request.Request(url, headers=_sb_headers())
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

def _actualizar_registro(registro_id, campos):
    import urllib.request, json
    url  = _sb_url() + f'?id=eq.{registro_id}'
    data = json.dumps(campos).encode('utf-8')
    req  = urllib.request.Request(url, data=data, method='PATCH', headers=_sb_headers())
    with urllib.request.urlopen(req) as r:
        return r.status

def _eliminar_registro(registro_id):
    import urllib.request
    url = _sb_url() + f'?id=eq.{registro_id}'
    req = urllib.request.Request(url, method='DELETE', headers=_sb_headers())
    with urllib.request.urlopen(req) as r:
        return r.status

def _insertar_lote_supabase(registros):
    import urllib.request, urllib.error, json
    url  = _sb_url()
    hdrs = _sb_headers()
    hdrs['Prefer'] = 'return=minimal'
    data = json.dumps(registros).encode('utf-8')
    req  = urllib.request.Request(url, data=data, method='POST', headers=hdrs)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        detalle = e.read().decode('utf-8')
        raise Exception(f'HTTP {e.code}: {detalle}')

def _eliminar_por_pais(pais):
    import urllib.request, urllib.parse
    url  = _sb_url() + f'?pais=eq.{urllib.parse.quote(pais)}'
    hdrs = _sb_headers()
    req  = urllib.request.Request(url, method='DELETE', headers=hdrs)
    with urllib.request.urlopen(req) as r:
        return r.status

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO DE RESPALDOS · funciones helper
# ══════════════════════════════════════════════════════════════════════════════

RETENCION_SEMANAS_BACKUP = 12  # Snapshots más viejos que esto se eliminan al rotar

def _leer_todos_registros_full():
    """Descarga todos los registros de top_registros sin filtro de país."""
    import urllib.request, json
    url = _sb_url() + '?select=*&order=id.asc'
    req = urllib.request.Request(url, headers=_sb_headers())
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))


def _registrar_backup_log(tipo, num_registros, snapshot_id=None, notas=None):
    """Inserta una fila en backup_log. Silencioso si falla."""
    import urllib.request, urllib.error, json
    try:
        url = _sb_url(tabla='backup_log')
        hdrs = _sb_headers()
        hdrs['Prefer'] = 'return=minimal'
        payload = {
            'tipo': tipo,
            'num_registros': num_registros,
            'snapshot_id': snapshot_id,
            'notas': notas,
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST', headers=hdrs)
        with urllib.request.urlopen(req) as r:
            return r.status
    except Exception:
        return None


def _crear_snapshot_supabase():
    """Crea snapshot completo en top_registros_backup y elimina los antiguos."""
    import urllib.request, urllib.error, urllib.parse, json
    from datetime import datetime, timedelta

    registros = _leer_todos_registros_full()
    if not registros:
        raise Exception('No hay registros en top_registros para respaldar.')

    snapshot_id = datetime.now().strftime('%Y-%m-%d_%H%M%S')

    filas_backup = []
    for reg in registros:
        filas_backup.append({
            'snapshot_id': snapshot_id,
            'id_original': reg.get('id'),
            'pais': reg.get('pais'),
            'registro': reg,
        })

    LOTE = 100
    url_ins = _sb_url(tabla='top_registros_backup')
    hdrs = _sb_headers()
    hdrs['Prefer'] = 'return=minimal'
    for i in range(0, len(filas_backup), LOTE):
        lote = filas_backup[i:i+LOTE]
        data = json.dumps(lote).encode('utf-8')
        req = urllib.request.Request(url_ins, data=data, method='POST', headers=hdrs)
        try:
            with urllib.request.urlopen(req) as r:
                pass
        except urllib.error.HTTPError as e:
            detalle = e.read().decode('utf-8')
            raise Exception(f'Error insertando snapshot: HTTP {e.code}: {detalle}')

    fecha_limite = (datetime.now() - timedelta(weeks=RETENCION_SEMANAS_BACKUP)).isoformat()
    url_del = _sb_url(tabla='top_registros_backup') + f'?fecha_backup=lt.{urllib.parse.quote(fecha_limite)}'
    hdrs_del = _sb_headers()
    hdrs_del['Prefer'] = 'return=representation'
    req_del = urllib.request.Request(url_del, method='DELETE', headers=hdrs_del)
    num_borrados = 0
    try:
        with urllib.request.urlopen(req_del) as r:
            borrados = json.loads(r.read().decode('utf-8'))
            num_borrados = len(borrados) if isinstance(borrados, list) else 0
    except Exception:
        pass

    _registrar_backup_log(
        tipo='snapshot_supabase',
        num_registros=len(registros),
        snapshot_id=snapshot_id,
        notas=f'Rotación eliminó {num_borrados} filas viejas' if num_borrados else None
    )

    return {
        'snapshot_id': snapshot_id,
        'num_registros': len(registros),
        'num_borrados': num_borrados,
    }


def _generar_excel_backup(registros):
    """Genera archivo Excel (BytesIO) con todos los registros."""
    import pandas as pd
    from io import BytesIO
    df = pd.DataFrame(registros)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='top_registros', index=False)
    buf.seek(0)
    return buf


def _stats_backup():
    """Consulta metadata para el panel de estado del módulo de respaldos."""
    import urllib.request, json
    stats = {
        'num_registros_vivos': None,
        'ultimo_snapshot': None,
        'num_snapshots_vivos': None,
        'ultimo_excel': None,
    }

    try:
        url = _sb_url() + '?select=id'
        hdrs = _sb_headers()
        hdrs['Prefer'] = 'count=exact'
        hdrs['Range'] = '0-0'
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req) as r:
            content_range = r.headers.get('Content-Range', '')
            if '/' in content_range:
                stats['num_registros_vivos'] = int(content_range.split('/')[-1])
    except Exception:
        pass

    try:
        url = _sb_url(tabla='top_registros_backup') + '?select=snapshot_id,fecha_backup&order=fecha_backup.desc&limit=1'
        req = urllib.request.Request(url, headers=_sb_headers())
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
            if data:
                snap_id = data[0]['snapshot_id']
                url_c = _sb_url(tabla='top_registros_backup') + f'?snapshot_id=eq.{snap_id}&select=backup_id'
                hdrs_c = _sb_headers()
                hdrs_c['Prefer'] = 'count=exact'
                hdrs_c['Range'] = '0-0'
                req_c = urllib.request.Request(url_c, headers=hdrs_c)
                with urllib.request.urlopen(req_c) as rc:
                    cr = rc.headers.get('Content-Range', '')
                    num = int(cr.split('/')[-1]) if '/' in cr else None
                stats['ultimo_snapshot'] = {
                    'fecha': data[0]['fecha_backup'],
                    'snapshot_id': snap_id,
                    'num_registros': num,
                }
    except Exception:
        pass

    try:
        url = _sb_url(tabla='top_registros_backup') + '?select=snapshot_id'
        req = urllib.request.Request(url, headers=_sb_headers())
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
            stats['num_snapshots_vivos'] = len(set(d['snapshot_id'] for d in data))
    except Exception:
        pass

    try:
        url = _sb_url(tabla='backup_log') + '?tipo=eq.excel_export&select=fecha,num_registros&order=fecha.desc&limit=1'
        req = urllib.request.Request(url, headers=_sb_headers())
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
            if data:
                stats['ultimo_excel'] = data[0]
    except Exception:
        pass

    return stats


def _migrar_excel_jotform(df, pais):
    """Mapea columnas JotForm → campos Supabase y retorna lista de registros"""
    import unicodedata

    def _col(df, fragmentos, excluir=None):
        excluir = excluir or []
        for c in df.columns:
            cn = unicodedata.normalize('NFD', str(c).lower()).encode('ascii','ignore').decode()
            if all(f in cn for f in fragmentos) and not any(e in cn for e in excluir):
                return c
        return None

    def _limpiar_fecha(val):
        if pd.isna(val): return None
        # Número serial de Excel (ej: 26904)
        try:
            num = float(val)
            if num > 1000:
                fecha = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(num))
                return fecha.strftime('%Y-%m-%d')
        except: pass
        val = str(val).strip()
        meses = {'ene':'01','feb':'02','mar':'03','abr':'04','may':'05','jun':'06',
                 'jul':'07','ago':'08','sep':'09','oct':'10','nov':'11','dic':'12'}
        parts = val.replace(',','').split()
        if len(parts) == 3:
            try:
                mes = meses.get(parts[0].lower(), parts[0])
                return f"{parts[2]}-{mes}-{parts[1].zfill(2)}"
            except: pass
        # Intentar parseo directo
        try:
            return pd.to_datetime(val).strftime('%Y-%m-%d')
        except: pass
        return None

    def _bool(val):
        if pd.isna(val): return None
        return str(val).strip().lower() in ['sí','si','yes','true','1']

    def _etapa(val):
        if pd.isna(val): return None
        v = str(val).strip().lower()
        if 'ingreso' in v or 'top1' in v: return 'TOP1'
        if 'seguimiento' in v or 'top2' in v: return 'TOP2'
        return str(val).strip()

    def _num(val, max_val=9999):
        if pd.isna(val): return None
        try:
            v = float(val)
            return min(v, max_val)
        except: return None

    def _int(val):
        v = _num(val)
        return int(v) if v is not None else None

    def _get(row, col):
        return row[col] if col and col in row.index else None

    SUST_MAP = {
        'alcohol':    ['alcohol'],
        'marihuana':  ['marihuana'],
        'pastabase':  ['pasta base'],
        'cocaina':    ['coca'],
        'sedantes':   ['sedante', 'tranquilizante'],
        'otra_sust':  ['otra sustancia'],
    }
    SEM_MAP = {
        's4': ['ltima semana','última semana','ultima semana'],
        's3': ['semana 3'],
        's2': ['semana 2'],
        's1': ['semana 1'],
    }

    registros = []
    errores   = []

    for i, row in df.iterrows():
        try:
            r = {'pais': pais}

            # Identificación
            col = _col(df, ['centro']); r['centro'] = str(_get(row, col) or '').strip() or None
            col = _col(df, ['codigo', 'identificacion']); r['codigo_paciente'] = str(_get(row, col) or '').strip() or None
            col = _col(df, ['fecha', 'nacimiento']); r['fecha_nacimiento'] = _limpiar_fecha(_get(row, col))
            col = _col(df, ['fecha', 'entrevista']); r['fecha_entrevista'] = _limpiar_fecha(_get(row, col))
            col = _col(df, ['sexo']); r['sexo'] = str(_get(row, col) or '').strip() or None
            col = _col(df, ['entrevistador']); r['nombre_entrevistador'] = str(_get(row, col) or '').strip() or None
            col = _col(df, ['etapa']); r['etapa'] = _etapa(_get(row, col))
            col = _col(df, ['sustancia', 'principal']); r['sustancia_principal'] = str(_get(row, col) or '').strip() or None
            col = _col(df, ['nombre', 'otra']); r['otra_sust_nombre'] = str(_get(row, col) or '').strip() or None

            # Sustancias
            for sust, frags in SUST_MAP.items():
                for sem, sem_frags in SEM_MAP.items():
                    col = next(
                        (c for c in df.columns if
                         any(f in c.lower() for f in frags) and
                         any(sf in unicodedata.normalize('NFD', c.lower()).encode('ascii','ignore').decode() for sf in sem_frags)),
                        None
                    )
                    r[f'{sust}_{sem}'] = _int(_get(row, col))
                # total
                col = next((c for c in df.columns if any(f in c.lower() for f in frags) and 'total' in c.lower()), None)
                r[f'{sust}_total'] = _int(_get(row, col))
                # prom
                col = next((c for c in df.columns if any(f in c.lower() for f in frags) and 'promedio' in c.lower()), None)
                r[f'{sust}_prom'] = _num(_get(row, col))

            # Transgresiones
            for campo, frag in [('hurto','hurto'),('robo','robo'),('venta_droga','venta'),('rina_pelea','pelea')]:
                col = next((c for c in df.columns if frag in c.lower()), None)
                r[campo] = _bool(_get(row, col))
            col = next((c for c in df.columns if 'otra acci' in c.lower() and '1' not in c), None)
            r['otra_accion'] = _bool(_get(row, col))
            col = next((c for c in df.columns if 'otra acci' in c.lower() and 'identifique' in c.lower()), None)
            r['otra_accion_desc'] = str(_get(row, col) or '').strip() or None

            # VIF
            for sem, sem_frags in SEM_MAP.items():
                col = next((c for c in df.columns if 'vif' in c.lower() or 'violencia intrafamiliar' in c.lower()
                            and any(sf in unicodedata.normalize('NFD', c.lower()).encode('ascii','ignore').decode() for sf in sem_frags)), None)
                if not col:
                    col = next((c for c in df.columns if ('intrafamiliar' in c.lower() or 'vif' in c.lower())
                                and any(sf in unicodedata.normalize('NFD', c.lower()).encode('ascii','ignore').decode() for sf in sem_frags)), None)
                r[f'vif_{sem}'] = _int(_get(row, col))
            col = next((c for c in df.columns if ('intrafamiliar' in c.lower() or 'vif' in c.lower()) and 'total' in c.lower()), None)
            r['vif_total'] = _int(_get(row, col))

            # Salud
            col = next((c for c in df.columns if 'psicol' in c.lower()), None); r['salud_psicologica'] = _int(_get(row, col))
            col = next((c for c in df.columns if 'salud f' in c.lower() or 'fisica' in c.lower()), None); r['salud_fisica'] = _int(_get(row, col))
            col = next((c for c in df.columns if 'calidad' in c.lower()), None); r['calidad_vida'] = _int(_get(row, col))

            # Trabajo
            for sem, sem_frags in SEM_MAP.items():
                col = next((c for c in df.columns if 'trabajo' in c.lower()
                            and any(sf in unicodedata.normalize('NFD', c.lower()).encode('ascii','ignore').decode() for sf in sem_frags)), None)
                r[f'dias_trabajo_{sem}'] = _int(_get(row, col))
            col = next((c for c in df.columns if 'trabajo' in c.lower() and 'total' in c.lower()), None)
            r['dias_trabajo_total'] = _int(_get(row, col))

            # Educación
            for sem, sem_frags in SEM_MAP.items():
                col = next((c for c in df.columns if ('colegio' in c.lower() or 'educaci' in c.lower())
                            and any(sf in unicodedata.normalize('NFD', c.lower()).encode('ascii','ignore').decode() for sf in sem_frags)), None)
                r[f'dias_educacion_{sem}'] = _int(_get(row, col))
            col = next((c for c in df.columns if ('colegio' in c.lower() or 'educaci' in c.lower()) and 'total' in c.lower()), None)
            r['dias_educacion_total'] = _int(_get(row, col))

            # Vivienda
            col = next((c for c in df.columns if 'estable' in c.lower()), None); r['vivienda_estable'] = _bool(_get(row, col))
            col = next((c for c in df.columns if 'b' in c.lower() and 'sica' in c.lower() and 'vivienda' in c.lower()), None); r['vivienda_basica'] = _bool(_get(row, col))

            registros.append({k: v for k, v in r.items() if v is not None})
        except Exception as e:
            errores.append((i, str(e)))

    # Normalizar: todos los registros deben tener exactamente las mismas claves
    if registros:
        todas_claves = set()
        for r in registros:
            todas_claves.update(r.keys())
        for r in registros:
            for k in todas_claves:
                if k not in r:
                    r[k] = None

    return registros, errores


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def _verificar_login(pais_sel, clave):
    secret_key = SECRET_KEY_MAP.get(pais_sel)
    if not secret_key:
        return False
    try:
        return clave == st.secrets[secret_key]
    except Exception:
        return False

def _mostrar_login():
    st.markdown("""
    <style>
    /* Fondo azul oscuro en toda la página */
    .stApp { background: #0f2540 !important; }
    section[data-testid="stMain"] > div { background: transparent !important; }
    .block-container { background: transparent !important; padding-top: 0 !important; }

    /* Panel izquierdo informativo */
    .login-panel-left {
        background: #1a3a5c;
        border-radius: 12px 0 0 12px;
        padding: 44px 36px;
        display: flex; flex-direction: column; gap: 18px;
    }
    .login-top-badge {
        background: #2563a8; color: #9DC3E6;
        font-size: 2rem; font-weight: 900;
        padding: 8px 18px; border-radius: 6px;
        letter-spacing: 3px; width: fit-content;
    }
    .login-panel-title { color: #ffffff; font-size: 1rem; font-weight: 700; line-height: 1.6; }
    .login-panel-sub   { color: #7fa8cc; font-size: .75rem; line-height: 1.9; }
    .login-panel-author {
        color: #7fa8cc; font-size: .75rem;
        margin-top: 8px; padding-top: 12px;
        border-top: 1px solid rgba(255,255,255,.1);
    }

    /* Panel derecho — formulario */
    .login-panel-right {
        background: #2E5F8A;
        border-radius: 0 12px 12px 0;
        padding: 44px 36px;
        display: flex; flex-direction: column; gap: 10px; justify-content: center;
    }
    .login-panel-right-title {
        color: #BDD7EE; font-size: .78rem;
        font-weight: 700; letter-spacing: 1px;
        margin-bottom: 6px;
    }

    /* Widgets Streamlit dentro del panel derecho — sin blanco */
    div[data-testid="stSelectbox"] > div > div,
    div[data-testid="stTextInput"] > div > div > input {
        background: rgba(255,255,255,0.1) !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        border-radius: 6px !important;
        color: #ffffff !important;
    }
    div[data-testid="stSelectbox"] label,
    div[data-testid="stTextInput"] label {
        color: #BDD7EE !important;
        font-size: .8rem !important;
    }
    div[data-testid="stSelectbox"] svg { fill: #9DC3E6 !important; }
    div[data-testid="stSelectbox"] > div > div > div {
        color: #ffffff !important;
    }
    /* Dropdown list */
    div[data-baseweb="popover"] { background: #1a3a5c !important; border: 1px solid #2563a8 !important; }
    div[data-baseweb="menu"] li { color: #ffffff !important; background: #1a3a5c !important; }
    div[data-baseweb="menu"] li:hover { background: #2563a8 !important; }
    </style>

    <div style="display:grid;grid-template-columns:1fr 1fr;max-width:680px;margin:3rem auto;
                border-radius:12px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.35);">
      <div class="login-panel-left">
        <div class="login-top-badge">TOP</div>
        <div class="login-panel-title">Sistema de Monitoreo<br>de Resultados<br>de Tratamiento</div>
        <div class="login-panel-sub">QALAT · UNODC<br>Región América Latina</div>
        <div class="login-panel-author">© Rodrigo Portilla</div>
      </div>
      <div class="login-panel-right">
        <div class="login-panel-right-title">ACCESO AL SISTEMA</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 1.05, 1])
    with col_c:
        st.markdown('<div style="margin-top:-170px;padding:0 36px;">', unsafe_allow_html=True)
        pais_sel = st.selectbox(
            'País / institución',
            [''] + PAISES_ACTIVOS + ['UNODC'],
            format_func=lambda p: '— País / institución —' if p == '' else f"{PAISES_CONFIG[p]['flag']}  {p}",
            key='login_pais'
        )
        clave = st.text_input('Contraseña', type='password', key='login_clave',
                              placeholder='Ingresa tu contraseña')
        if st.button('Ingresar →', use_container_width=True, key='btn_login'):
            if pais_sel == '':
                st.error('❌ Selecciona un país o institución.')
            elif _verificar_login(pais_sel, clave):
                st.session_state['autenticado'] = True
                st.session_state['rol_pais']    = pais_sel
                st.rerun()
            else:
                st.error('❌ Contraseña incorrecta. Intenta nuevamente.')
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state.get('autenticado', False):
    _mostrar_login()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# USUARIO AUTENTICADO
# ══════════════════════════════════════════════════════════════════════════════
rol       = st.session_state['rol_pais']
es_unodc  = (rol == 'UNODC')
pais_fijo = None if es_unodc else rol
flag      = PAISES_CONFIG[rol]['flag']
rol_lbl   = f'{flag} {rol}'

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""<div class="qalat-hdr">
  <h1>📊 QALAT · Monitoreo de Resultados de Tratamiento — Instrumento <span class="instrumento">TOP</span></h1>
  <p>Procesamiento automático TOP · Sube tu Excel, aplica filtros y descarga todos los reportes</p>
  <p style="margin-top:.4rem;font-size:.8rem;color:#9DC3E6;">Sesión activa: <b>{rol_lbl}</b></p>
  <p style="margin-top:.2rem;font-size:.75rem;color:#7fa8cc;">© Rodrigo Portilla · UNODC</p>
</div>""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('### 📋 Pasos')
    st.markdown('1. Selecciona fuente de datos\n2. Aplica filtros (opcional)\n3. Elige reportes\n4. Clic en **Procesar**\n5. Descarga')
    st.markdown('---')
    st.caption(f'QALAT v5.0 · {datetime.now().strftime("%d/%m/%Y")}')
    st.markdown(f'**Sesión:** {rol_lbl}')
    st.markdown('---')
    if st.button('🚪 Cerrar sesión', use_container_width=True, key='btn_logout'):
        for k in ['autenticado','rol_pais','supabase_path','supabase_df',
                  'filename','result','outputs','seleccion','wide_path','work_dir','raw_path',
                  'corr_registros','corr_editando','corr_confirm_del']:
            st.session_state.pop(k, None)
        st.rerun()
    st.markdown('---')
    st.markdown(
        '<div style="font-size:.75rem;color:#999;line-height:1.6;">'
        '© Rodrigo Portilla<br><span style="color:#bbb;">UNODC Chile · Proyecto QALAT</span>'
        '</div>', unsafe_allow_html=True
    )

# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑAS
# ══════════════════════════════════════════════════════════════════════════════
if es_unodc:
    tab_panel, tab_reportes, tab_correccion, tab_migracion, tab_respaldos = st.tabs(
        ['🏠 Panel de gestión', '📊 Reportes', '✏️ Corrección de registros',
         '📥 Migración JotForm (obsoleta)', '💾 Respaldos']
    )
else:
    tab_panel, tab_reportes, tab_correccion = st.tabs(
        ['🏠 Panel de gestión', '📊 Reportes', '✏️ Corrección de registros']
    )
    tab_migracion = None
    tab_respaldos = None


# ──────────────────────────────────────────────────────────────────────────────
# TAB 0: PANEL DE GESTIÓN
# ──────────────────────────────────────────────────────────────────────────────
with tab_panel:

    # UNODC: selectbox de país arriba; país: usa pais_fijo directo
    if es_unodc:
        col_sel, col_refresh = st.columns([4, 1])
        with col_sel:
            pais_panel = st.selectbox(
                'País a visualizar',
                PAISES_ACTIVOS,
                format_func=lambda p: f"{PAISES_CONFIG[p]['flag']}  {p}",
                key='panel_pais_sb'
            )
        with col_refresh:
            st.markdown('<div style="height:1.7rem"></div>', unsafe_allow_html=True)
            if st.button('🔄 Actualizar', use_container_width=True, key='panel_refresh_unodc'):
                invalidar_cache_pais()
                st.rerun()
    else:
        pais_panel = pais_fijo
        col_titulo, col_refresh = st.columns([5, 1])
        with col_titulo:
            st.markdown(
                f'<div style="font-size:1.25rem;font-weight:700;color:#1F1F1F;'
                f'padding:.35rem 0;">🏠 Panel de gestión · '
                f'{PAISES_CONFIG[pais_panel]["flag"]} {pais_panel}</div>',
                unsafe_allow_html=True
            )
        with col_refresh:
            st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)
            if st.button('🔄 Actualizar', use_container_width=True, key='panel_refresh_pais'):
                invalidar_cache_pais()
                st.rerun()

    # Carga automática con manejo de error blindado
    try:
        df_panel = cargar_datos_pais(pais_panel)
    except KeyError:
        st.error('⚠ Las credenciales de Supabase no están configuradas en Secrets.')
        st.stop()
    except Exception as e:
        st.error(f'❌ No se pudieron cargar los datos: {e}')
        if st.button('🔄 Reintentar', key='panel_retry'):
            invalidar_cache_pais()
            st.rerun()
        st.stop()

    if df_panel.empty:
        st.info(f'ℹ Aún no hay registros para {pais_panel} en la base.')
    else:
        # ── Métricas superiores ───────────────────────────────────────────────
        panel_metricas.render(df_panel, pais_panel, centro_id=None)

        st.markdown('<div style="height:.3rem"></div>', unsafe_allow_html=True)

        # ── Semáforo de actividad reciente por centro ─────────────────────────
        panel_semaforo.render(df_panel, pais_panel, centro_id=None)

        st.markdown('<div style="height:.3rem"></div>', unsafe_allow_html=True)

        # ── Registros mensuales (barras + curva acumulada) ────────────────────
        panel_mensuales.render(df_panel, pais_panel, centro_id=None)

        st.markdown('<div style="height:.3rem"></div>', unsafe_allow_html=True)

        # ── Ranking + Continuidad lado a lado ─────────────────────────────────
        col_rk, col_cont = st.columns(2, gap='small')
        with col_rk:
            panel_ranking.render(df_panel, pais_panel, centro_id=None)
        with col_cont:
            panel_continuidad.render(df_panel, pais_panel, centro_id=None)

        st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

        # ── Perfil de pacientes al ingreso ────────────────────────────────────
        st.markdown(
            '<div class="seccion-panel">'
            '  <span class="seccion-panel-titulo">Perfil de pacientes al ingreso</span>'
            '  <span class="seccion-panel-linea"></span>'
            '  <span class="seccion-panel-sub">primera evaluación TOP · no incluye seguimientos</span>'
            '</div>',
            unsafe_allow_html=True
        )

        # ── Fila 1: Dona de sexo + Rango de edad ─────────────────────────────
        st.markdown('<div class="panel-fila-1">', unsafe_allow_html=True)
        col_sexo, col_edad = st.columns(2, gap='small')
        with col_sexo:
            panel_piramide.render(df_panel, pais_panel, centro_id=None)
        with col_edad:
            panel_edad.render(df_panel, pais_panel, centro_id=None)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

        # ── Fila 2: Sustancia principal + Días de consumo ─────────────────────
        st.markdown('<div class="panel-fila-2">', unsafe_allow_html=True)
        col_sust, col_dias = st.columns(2, gap='small')
        with col_sust:
            panel_sustancia.render(df_panel, pais_panel, centro_id=None)
        with col_dias:
            panel_dias_consumo.render(df_panel, pais_panel, centro_id=None)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

        # ── Fila 3: Transgresión + Salud y Calidad de Vida ───────────────────
        st.markdown('<div class="panel-fila-3">', unsafe_allow_html=True)
        col_trans, col_salud = st.columns(2, gap='small')
        with col_trans:
            panel_transgresion.render(df_panel, pais_panel, centro_id=None)
        with col_salud:
            panel_salud.render(df_panel, pais_panel, centro_id=None)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

        # ── Reporte de avance por centro ──────────────────────────────────────
        with st.container(border=True):
            st.markdown(
                '<div style="font-size:.92rem;font-weight:600;color:#1F1F1F;'
                'padding:.02rem .1rem .18rem .1rem;">📊&nbsp;&nbsp;Reporte de avance por centro</div>'
                '<div style="font-size:.72rem;color:#777;padding:0 .1rem .3rem .1rem;">'
                'Excel consolidado · una fila por centro con ingresos, continuidad y actividad'
                '</div>',
                unsafe_allow_html=True,
            )
            panel_avance_centros.boton_descarga(df_panel, pais_panel)


# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: REPORTES
# ──────────────────────────────────────────────────────────────────────────────
with tab_reportes:

    # ── CSS especifico del tab Reportes ──────────────────────────────────
    st.markdown("""
    <style>
    .rep-section-title {font-size:1rem;font-weight:700;color:#004AAD;margin:1.2rem 0 .15rem 0;}
    .rep-section-sub   {font-size:.75rem;color:#888;margin-bottom:.7rem;}
    .rep-quick-card    {background:white;border:1px solid #E5E5E5;border-radius:10px;
                        padding:1rem 1.2rem;display:flex;align-items:center;gap:1rem;margin-bottom:.3rem;}
    .rep-quick-icon    {font-size:2rem;flex-shrink:0;}
    .rep-quick-title   {font-size:.95rem;font-weight:700;color:#1F3864;}
    .rep-quick-desc    {font-size:.75rem;color:#666;}
    .rep-card          {background:white;border:1px solid #E5E5E5;border-radius:10px;
                        padding:1rem 1.1rem 1.1rem 1.1rem;}
    .rep-card-title    {font-size:.95rem;font-weight:700;color:#1F3864;margin-bottom:.2rem;}
    .rep-card-desc     {font-size:.78rem;color:#666;min-height:2.5rem;}
    .rep-tag           {display:inline-block;font-size:.68rem;font-weight:700;
                        padding:.15rem .5rem;border-radius:20px;margin-left:.4rem;vertical-align:middle;}
    .rep-tag-top1      {background:#E8F0FE;color:#004AAD;}
    .rep-tag-top12     {background:#E6F4EA;color:#1D9E75;}
    .rep-filtros-box   {background:#F8FAFD;border:1px solid #E5E5E5;border-radius:10px;
                        padding:.9rem 1.1rem;margin:.5rem 0 .8rem 0;}
    .rep-filtros-label {font-size:.72rem;font-weight:600;color:#888;
                        text-transform:uppercase;letter-spacing:.05em;margin-bottom:.25rem;}
    </style>
    """, unsafe_allow_html=True)

    # ── Carga automatica desde Supabase ───────────────────────────────────
    if 'supabase_path' not in st.session_state:
        try:
            _pais_carga = pais_fijo if not es_unodc else None
            _registros  = _cargar_supabase(_pais_carga)
            if _registros:
                _df_sb = pd.DataFrame(_registros)
                _df_sb = _df_sb.rename(columns={k: v for k, v in RENAME_MAP.items() if k in _df_sb.columns})
                _tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
                _df_sb.to_excel(_tmp.name, index=False)
                _tmp.close()
                st.session_state['supabase_path'] = _tmp.name
                st.session_state['supabase_df']   = _df_sb
                st.session_state['filename']       = f'Supabase_{pais_fijo if not es_unodc else "Todos"}'
        except Exception:
            pass

    supabase_data     = st.session_state.get('supabase_df')
    filtro_centro_val = None
    fecha_desde_val   = None
    fecha_hasta_val   = None

    # ── Encabezado: fuente + boton actualizar ─────────────────────────────
    _n_reg = len(supabase_data) if supabase_data is not None else 0
    _hcol1, _hcol2 = st.columns([3, 1])
    with _hcol1:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:.8rem;padding:.3rem 0;">'
            f'  <span style="background:#E8F0FE;color:#004AAD;font-size:.78rem;font-weight:600;'
            f'  padding:.3rem .8rem;border-radius:20px;">&#128452; Base actual (Supabase)</span>'
            f'  <span style="color:#888;font-size:.8rem;">carga automatica al entrar &nbsp;&middot;&nbsp;'
            f'  <b style="color:#1F3864">{_n_reg:,}</b> registros cargados</span>'
            f'</div>',
            unsafe_allow_html=True
        )
    with _hcol2:
        if st.button('Actualizar datos', use_container_width=True, key='rep_refresh'):
            for _k in ['supabase_path','supabase_df','filename','result','outputs','wide_path','work_dir']:
                st.session_state.pop(_k, None)
            st.rerun()

    st.markdown('<div style="height:.4rem"></div>', unsafe_allow_html=True)

    # ── Descargas rapidas ─────────────────────────────────────────────────
    st.markdown(
        '<div class="rep-section-title">Descargas rapidas</div>'
        '<div class="rep-section-sub">archivos maestros con toda la informacion sin filtros</div>',
        unsafe_allow_html=True
    )
    _q1, _q2 = st.columns(2, gap='small')
    with _q1:
        st.markdown(
            '<div class="rep-quick-card">'
            '  <div class="rep-quick-icon">&#128452;</div>'
            '  <div>'
            '    <div class="rep-quick-title">Base Wide completa</div>'
            '    <div class="rep-quick-desc">Excel con 6 hojas &middot; Wide, Resumen, Alertas, Calidad, Por Centro, Pendientes</div>'
            '  </div>'
            '</div>',
            unsafe_allow_html=True
        )
        if supabase_data is not None:
            if st.button('Generar y descargar', key='q_wide', use_container_width=True):
                with st.spinner('Generando Base Wide...'):
                    try:
                        _rq = procesar_wide(st.session_state['supabase_path'])
                        st.session_state['dl_quick_wide'] = _rq['excel_bytes'].getvalue()
                    except Exception as _e:
                        st.error(f'Error: {_e}')
            if 'dl_quick_wide' in st.session_state:
                st.download_button('Descargar Base Wide (.xlsx)',
                    data=st.session_state['dl_quick_wide'],
                    file_name=f'TOP_Base_Wide_{datetime.now().strftime("%Y-%m-%d")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True, key='save_wide')
    with _q2:
        st.markdown(
            '<div class="rep-quick-card">'
            '  <div class="rep-quick-icon">&#128202;</div>'
            '  <div>'
            '    <div class="rep-quick-title">Reporte de avance por centro</div>'
            '    <div class="rep-quick-desc">Excel &middot; una fila por centro con TOP1, TOP2, continuidad, actividad</div>'
            '  </div>'
            '</div>',
            unsafe_allow_html=True
        )
        if supabase_data is not None:
            from pipeline.panel.avance_centros import _calcular_avance, _generar_excel as _gen_av
            _df_av  = _calcular_avance(supabase_data)
            _pais_av = pais_fijo if not es_unodc else 'Todos los paises'
            st.download_button('Descargar Reporte de avance (.xlsx)',
                data=_gen_av(_df_av, _pais_av),
                file_name=f'Avance_centros_{datetime.now().strftime("%Y-%m-%d")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True, key='dl_avance')

    st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)

    # ── Filtros ───────────────────────────────────────────────────────────
    st.markdown('<div class="rep-filtros-box">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:.8rem;font-weight:600;color:#555;margin-bottom:.5rem;">'
        'Filtros para reportes analiticos</div>',
        unsafe_allow_html=True
    )
    centros_disponibles = []
    if supabase_data is not None:
        for _cc in ['Codigo del centro de tratamiento', 'Código del centro de tratamiento']:
            if _cc in supabase_data.columns:
                centros_disponibles = sorted(supabase_data[_cc].dropna().astype(str).str.strip().unique().tolist())
                break

    MESES     = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
    _hoy_rep  = datetime.now()
    _anio_act = _hoy_rep.year
    _mes_idx  = _hoy_rep.month - 1
    _anios    = list(range(_anio_act - 4, _anio_act + 1))
    _idx_a    = len(_anios) - 1

    _fc1, _fc2 = st.columns([1.2, 2.5])
    with _fc1:
        st.markdown('<div class="rep-filtros-label">Centro</div>', unsafe_allow_html=True)
        _opts = ['Todos los centros'] + centros_disponibles
        _sel  = st.selectbox('Centro', _opts, label_visibility='collapsed', key='rep_centro')
        if _sel != 'Todos los centros':
            filtro_centro_val = _sel
    with _fc2:
        _fd1, _fd2 = st.columns(2)
        with _fd1:
            st.markdown('<div class="rep-filtros-label">Desde</div>', unsafe_allow_html=True)
            _cc1, _cc2 = st.columns(2)
            with _cc1: mes_d  = st.selectbox('M',  MESES, index=0,       label_visibility='collapsed', key='rep_mes_d')
            with _cc2: anio_d = st.selectbox('A',  _anios, index=0,      label_visibility='collapsed', key='rep_anio_d')
        with _fd2:
            st.markdown('<div class="rep-filtros-label">Hasta</div>', unsafe_allow_html=True)
            _cc3, _cc4 = st.columns(2)
            with _cc3: mes_h  = st.selectbox('M2', MESES,  index=_mes_idx, label_visibility='collapsed', key='rep_mes_h')
            with _cc4: anio_h = st.selectbox('A2', _anios, index=_idx_a,   label_visibility='collapsed', key='rep_anio_h')
    _usar_per = st.checkbox('Aplicar filtro de periodo', value=False, key='rep_periodo')
    if _usar_per:
        fecha_desde_val = f'{anio_d}-{MESES.index(mes_d)+1:02d}'
        fecha_hasta_val = f'{anio_h}-{MESES.index(mes_h)+1:02d}'
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)

    # ── Helper para cards de reporte ──────────────────────────────────────
    def _rep_card(col, key, icono, label, desc):
        with col:
            st.markdown(
                f'<div class="rep-card">'
                f'  <div style="font-size:1.6rem;margin-bottom:.3rem;">{icono}</div>'
                f'  <div class="rep-card-title">{label}</div>'
                f'  <div class="rep-card-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            st.markdown('<div style="height:.3rem"></div>', unsafe_allow_html=True)
            if supabase_data is not None:
                if st.button(f'Descargar {label}', key=f'btn_{key}', use_container_width=True):
                    with st.spinner(f'Generando {label}...'):
                        try:
                            _wr = procesar_wide(st.session_state['supabase_path'],
                                               filtro_centro=filtro_centro_val,
                                               fecha_desde=fecha_desde_val,
                                               fecha_hasta=fecha_hasta_val)
                            _wd = tempfile.mkdtemp(prefix='qalat_')
                            _wp = os.path.join(_wd, 'TOP_Base_Wide.xlsx')
                            with open(_wp, 'wb') as _f: _f.write(_wr['excel_bytes'].getvalue())
                            _buf, _fn, _mi = run_script(key, _wp, filtro_centro=filtro_centro_val)
                            st.session_state[f'dl_{key}'] = (_buf, _fn, _mi)
                        except Exception as _e:
                            st.error(f'Error: {_e}')
                if f'dl_{key}' in st.session_state:
                    _b, _f2, _m = st.session_state[f'dl_{key}']
                    st.download_button(f'Guardar {label} (.xlsx/.docx/.pptx)',
                        data=_b.getvalue(), file_name=_f2, mime=_m,
                        use_container_width=True, key=f'save_{key}')
            else:
                st.caption('Sin datos cargados')

    # ── Reportes de ingreso ───────────────────────────────────────────────
    st.markdown(
        '<div class="rep-section-title">Reportes de ingreso '
        '<span class="rep-tag rep-tag-top1">TOP1</span></div>'
        '<div class="rep-section-sub">caracterizacion de los pacientes al momento del ingreso</div>',
        unsafe_allow_html=True
    )
    _ri1, _ri2, _ri3 = st.columns(3, gap='small')
    _rep_card(_ri1, 'caract_excel', '&#128215;', 'Excel',
              '11 hojas con tablas de perfil, sustancias, transgresion, homogresion')
    _rep_card(_ri2, 'word_caract',  '&#128216;', 'Word',
              '4 secciones narrativas con graficos y tablas para informe institucional')
    _rep_card(_ri3, 'pptx_caract', '&#128214;', 'PowerPoint',
              '6 diapositivas ejecutivas para presentar a autoridad institucional')

    st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)

    # ── Reportes de seguimiento ───────────────────────────────────────────
    st.markdown(
        '<div class="rep-section-title">Reportes de seguimiento '
        '<span class="rep-tag rep-tag-top12">TOP1 vs TOP2</span></div>'
        '<div class="rep-section-sub">analisis comparativo entre ingreso y segunda evaluacion</div>',
        unsafe_allow_html=True
    )
    _rs1, _rs2, _rs3 = st.columns(3, gap='small')
    _rep_card(_rs1, 'seg_excel', '&#128215;', 'Excel',
              'Tablas comparativas TOP1 vs TOP2 con cambios porcentuales por dimension')
    _rep_card(_rs2, 'word_seg',  '&#128216;', 'Word',
              'Analisis narrativo de evolucion entre ingreso y seguimiento')
    _rep_card(_rs3, 'pptx_seg', '&#128214;', 'PowerPoint',
              '6 diapositivas con evolucion visual entre TOP1 y TOP2')

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

    if 'result' in st.session_state:
        R    = st.session_state['result']
        s    = R['stats']; wide = R['wide']
        fc   = R.get('filtro_centro'); fd = R.get('fecha_desde'); fh = R.get('fecha_hasta')
        filtro_str = (f' · Centro: {fc}' if fc else '') + (f' · {fd} → {fh}' if fd else '')

        st.markdown('---')
        st.markdown(f'<div class="sec">📊 Resultados — {R["periodo"]}{filtro_str}</div>', unsafe_allow_html=True)

        k1,k2,k3,k4,k5,k6 = st.columns(6)
        for col,lbl,val,sub,cls in [
            (k1,'Pacientes únicos',       s['N_total'],   '',                           ''),
            (k2,'Con seguimiento TOP2',   s['N_top2'],    f"{s['pct_top2']}% del total", ''),
            (k3,'Solo TOP1 (pendientes)', s['N_solo1'],   '',                           ''),
            (k4,'Valores corregidos',     s['N_alertas'], '', 'red' if s['N_alertas'] else 'green'),
            (k5,'🔴 Urgentes (90+ días)', s['n_rojo'],    '',                           'red'),
            (k6,'🟠 Próximos (60–89d)',   s['n_naranja'], '',                           'orange'),
        ]:
            with col:
                st.markdown(f'<div class="kpi {cls}"><div class="kpi-lbl">{lbl}</div>'
                            f'<div class="kpi-val">{val}</div>'
                            f'{"<div class=kpi-sub>"+sub+"</div>" if sub else ""}</div>',
                            unsafe_allow_html=True)

        centros = R.get('centros', [])
        if centros and not fc:
            st.markdown('<div class="sec">🏥 Resumen por Centro / Servicio de Tratamiento</div>', unsafe_allow_html=True)
            df_c = pd.DataFrame(centros)
            df_c.columns = ['Centro','Aplicaciones','Pacientes únicos','Con TOP2','Sin TOP2 (pendientes)','Valores corregidos']
            rows_html = ''
            for i, row in df_c.iterrows():
                is_total = str(row.iloc[0]) == 'TOTAL'
                bg = f'background:{NAVY};color:white;font-weight:700;' if is_total else \
                     ('background:#EEF4FB;' if i%2==0 else 'background:white;')
                cells = ''
                for j, val in enumerate(row):
                    align  = 'left' if j==0 else 'center'
                    corr   = (j==5 and not is_total and int(val)>0)
                    color  = 'white' if is_total else (RED if corr else '#333')
                    weight = 'font-weight:700;' if is_total or corr else ''
                    cells += f'<td style="padding:7px 12px;text-align:{align};color:{color};{weight}">{val}</td>'
                rows_html += f'<tr style="{bg}">{cells}</tr>'
            hdrs = ''.join(f'<th style="padding:9px 12px;text-align:{"left" if i==0 else "center"};'
                           f'background:{NAVY};color:white;font-size:.85rem;">{c}</th>'
                           for i,c in enumerate(df_c.columns))
            st.markdown(f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;'
                        f'font-family:Calibri,sans-serif;font-size:.9rem;">'
                        f'<thead><tr>{hdrs}</tr></thead><tbody>{rows_html}</tbody></table></div>',
                        unsafe_allow_html=True)

        st.markdown('<div class="sec">📈 Análisis visual</div>', unsafe_allow_html=True)
        gc1,gc2,gc3 = st.columns(3)
        sv=[s['n_verde'],s['n_naranja'],s['n_rojo']]
        sl=['Pendientes <60d','Pendientes 60-89d','Urgentes 90+d']; sc=[GREEN,ORANGE,RED]
        sv_f=[v for v in sv if v>0]; sl_f=[l for l,v in zip(sl,sv) if v>0]; sc_f=[c for c,v in zip(sc,sv) if v>0]
        sust=s.get('sust_dist',{})
        sd=pd.DataFrame(list(sust.items()),columns=['S','n']).sort_values('n') if sust else pd.DataFrame()
        colors_s=[MID if i%2==0 else ACCENT for i in range(len(sd))]

        with gc1:
            fig,ax=plt.subplots(figsize=(4.5,3.2))
            bars=ax.bar(['Con TOP2','Solo TOP1'],[s['N_top2'],s['N_solo1']],color=[MID,'#CCC'],width=.5)
            for b,v in zip(bars,[s['N_top2'],s['N_solo1']]):
                ax.text(b.get_x()+b.get_width()/2.,b.get_height()+.5,str(v),
                        ha='center',va='bottom',fontsize=11,fontweight='bold',color=NAVY)
            ax.set_title('Estado de seguimiento',fontsize=11,color=NAVY,fontweight='bold',pad=8)
            ax.set_facecolor('#F8FAFD'); fig.patch.set_facecolor('#F8FAFD')
            ax.spines[['top','right','left']].set_visible(False); ax.yaxis.set_visible(False)
            plt.tight_layout(); st.pyplot(fig); plt.close()

        with gc2:
            fig,ax=plt.subplots(figsize=(4.5,3.2))
            if sv_f:
                w,_,at=ax.pie(sv_f,colors=sc_f,autopct='%1.0f%%',startangle=90,
                    wedgeprops={'edgecolor':'white','linewidth':1.5},textprops={'fontsize':9})
                for a in at: a.set_color('white'); a.set_fontweight('bold')
                ax.legend(w,[f'{l} ({v})' for l,v in zip(sl_f,sv_f)],
                    loc='lower center',bbox_to_anchor=(.5,-.3),fontsize=7.5,ncol=2,frameon=False)
            ax.set_title('Semáforo de seguimiento',fontsize=11,color=NAVY,fontweight='bold',pad=8)
            fig.patch.set_facecolor('#F8FAFD'); plt.tight_layout(); st.pyplot(fig); plt.close()

        with gc3:
            fig,ax=plt.subplots(figsize=(4.5,3.2))
            if not sd.empty:
                ax.barh(sd['S'],sd['n'],color=colors_s,height=.6)
                tot=sd['n'].sum()
                for b,v in zip(ax.patches,sd['n']):
                    ax.text(b.get_width()+.3,b.get_y()+b.get_height()/2,
                            f'{v} ({round(v/tot*100,1) if tot else 0}%)',va='center',fontsize=8,color=NAVY)
                ax.spines[['top','right','bottom']].set_visible(False); ax.xaxis.set_visible(False)
            else:
                ax.text(.5,.5,'Sustancia no detectada',ha='center',va='center',
                        transform=ax.transAxes,fontsize=10,color='#888')
            ax.set_title('Sustancia principal (TOP1)',fontsize=11,color=NAVY,fontweight='bold',pad=8)
            ax.set_facecolor('#F8FAFD'); fig.patch.set_facecolor('#F8FAFD')
            plt.tight_layout(); st.pyplot(fig); plt.close()

        pend = wide[wide['Alerta_TOP2'].isin(['🟠 60-89 dias','🔴 90+ dias'])].copy()
        if len(pend):
            st.markdown('<div class="sec">🚨 Pendientes urgentes</div>', unsafe_allow_html=True)
            pend = pend.loc[:,~pend.columns.duplicated()]
            id_c  = wide.columns[0]; cs=[id_c]
            col_c = next((c for c in pend.columns if 'centro' in c.lower() and '_TOP1' in c), None)
            col_f = next((c for c in pend.columns if 'fecha entrevista' in c.lower() and '_TOP1' in c), None)
            if col_c: cs.append(col_c)
            if col_f: cs.append(col_f)
            cs += ['Dias_desde_TOP1','Alerta_TOP2']
            cs  = list(dict.fromkeys(c for c in cs if c in pend.columns))
            tab = pend[cs].copy()
            tab['_o'] = tab['Alerta_TOP2'].apply(lambda x: 0 if '90' in str(x) else 1)
            tab = tab.sort_values(['_o','Dias_desde_TOP1'],ascending=[True,False]).drop(columns='_o')
            st.dataframe(tab.head(30), use_container_width=True, height=280)

        with st.expander('📋 Log de procesamiento'):
            for log in R['logs']: st.text(log)

        st.markdown('---')
        st.markdown('<div class="sec">⬇️ Descargar reportes</div>', unsafe_allow_html=True)

        fname_base = os.path.splitext(st.session_state.get('filename','base'))[0]
        if fc:  fname_base += f'_{fc}'
        if fd:  fname_base += f'_{fd}_{fh}'
        today_str = datetime.now().strftime('%Y-%m-%d')
        outputs   = st.session_state.get('outputs',{})
        sel       = st.session_state.get('seleccion',{})

        d1,d2,d3 = st.columns(3)
        with d1:
            st.markdown('<div class="outcard"><h4>📊 Base Wide completa</h4>'
                        '<p>6 hojas: Wide · Resumen · Alertas · Calidad · Por Centro · Pendientes</p></div>',
                        unsafe_allow_html=True)
            st.download_button('⬇️ Base Wide (.xlsx)',
                data=R['excel_bytes'].getvalue(),
                file_name=f'TOP_Base_Wide_{fname_base}_{today_str}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True, key='dl_wide')

        for key,col,dlkey in [('caract_excel',d2,'dl_ce'),('seg_excel',d3,'dl_se')]:
            o=outputs.get(key,{}); lbl,fmt,desc=LABELS[key]
            with col:
                st.markdown(f'<div class="outcard"><h4>{lbl}</h4><p>{desc}</p></div>', unsafe_allow_html=True)
                if not sel.get(key,False):    st.caption('No seleccionado')
                elif o.get('ok'):             st.download_button(f'⬇️ {fmt}',data=o['buf'].getvalue(),
                                                  file_name=o['fname'],mime=o['mime'],use_container_width=True,key=dlkey)
                else:                         st.warning(f"⚠️ {o.get('error','Error')[:100]}")

        st.markdown('---')
        d4,d5 = st.columns(2)
        for key,col,dlkey in [('pdf_caract',d4,'dl_pc'),('pdf_seg',d5,'dl_ps')]:
            o=outputs.get(key,{}); lbl,fmt,desc=LABELS[key]
            with col:
                st.markdown(f'<div class="outcard"><h4>{lbl}</h4><p>{desc}</p></div>', unsafe_allow_html=True)
                if not sel.get(key,False):    st.caption('No seleccionado')
                elif o.get('ok'):             st.download_button(f'⬇️ {fmt}',data=o['buf'].getvalue(),
                                                  file_name=o['fname'],mime=o['mime'],use_container_width=True,key=dlkey)
                else:                         st.warning(f"⚠️ {o.get('error','Error')[:100]}")

        st.markdown('---')
        d6,d7 = st.columns(2)
        for key,col,dlkey in [('pptx_caract',d6,'dl_ppc'),('pptx_seg',d7,'dl_pps')]:
            o=outputs.get(key,{}); lbl,fmt,desc=LABELS[key]
            with col:
                st.markdown(f'<div class="outcard"><h4>{lbl}</h4><p>{desc}</p></div>', unsafe_allow_html=True)
                if not sel.get(key,False):    st.caption('No seleccionado')
                elif o.get('ok'):             st.download_button(f'⬇️ {fmt}',data=o['buf'].getvalue(),
                                                  file_name=o['fname'],mime=o['mime'],use_container_width=True,key=dlkey)
                else:                         st.warning(f"⚠️ {o.get('error','Error')[:100]}")

        # ── Distribución por centros ──────────────────────────────────────────
        if 'wide_path' in st.session_state and not filtro_centro_val:
            st.markdown('---')
            st.markdown('<div class="sec">📦 Distribución por centros</div>', unsafe_allow_html=True)
            st.markdown(
                '<div style="background:#EEF4FB;border-left:4px solid #2E75B6;'
                'padding:.8rem 1.2rem;border-radius:6px;margin-bottom:1rem;">'
                '<b>¿Qué genera este botón?</b><br>'
                'Un archivo <b>.zip</b> con una carpeta por cada centro. '
                'Cada carpeta incluye la base Wide filtrada + los reportes seleccionados.'
                '</div>', unsafe_allow_html=True
            )
            st.markdown('**Selecciona qué incluir en cada paquete:**')
            dc1, dc2, dc3 = st.columns(3)
            with dc1:
                d_ce = st.checkbox('📋 Excel caracterización', value=True,  key='d_ce')
                d_se = st.checkbox('📋 Excel seguimiento',     value=True,  key='d_se')
            with dc2:
                d_pc = st.checkbox('📄 Word caracterización',  value=True,  key='d_pc')
                d_ps = st.checkbox('📄 Word seguimiento',      value=True,  key='d_ps')
            with dc3:
                d_ppc = st.checkbox('📑 PPT caracterización',  value=False, key='d_ppc')
                d_pps = st.checkbox('📑 PPT seguimiento',      value=False, key='d_pps')

            keys_dist = [k for k,v in {
                'caract_excel':d_ce,'seg_excel':d_se,
                'pdf_caract':d_pc,'pdf_seg':d_ps,
                'pptx_caract':d_ppc,'pptx_seg':d_pps,
            }.items() if v]

            n_centros = len(centros_disponibles)
            st.caption(f'Se generarán **{n_centros} carpetas** — una por cada centro detectado')

            if st.button('📦 Generar paquetes por centro', use_container_width=True, key='btn_dist'):
                wide_path_dist = st.session_state['wide_path']
                status_box = st.empty()
                prog_dist  = st.progress(0, text='Iniciando...')
                def _cb(i, total, centro):
                    pct = i/total if total else 1
                    txt = f'Procesando centro {i+1}/{total}: {centro}' if centro != 'listo' else '✅ ZIP generado'
                    prog_dist.progress(pct, text=txt); status_box.info(txt)
                try:
                    with st.spinner('Generando paquetes — esto puede tomar varios minutos...'):
                        zip_buf = run_paquetes_centros(
                            wide_path_dist, keys_sel=keys_dist,
                            progress_cb=_cb, raw_input_path=st.session_state.get('raw_path')
                        )
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    prog_dist.progress(1.0, text='✅ Listo')
                    status_box.success(f'✅ ZIP generado con {n_centros} carpetas · {len(keys_dist)} reportes por centro')
                    st.download_button(
                        label=f'⬇️ Descargar ZIP ({n_centros} centros)',
                        data=zip_buf.getvalue(),
                        file_name=f'QALAT_Paquetes_Centros_{today_str}.zip',
                        mime='application/zip',
                        use_container_width=True, key='dl_dist'
                    )
                except Exception as e:
                    st.error(f'❌ Error generando paquetes: {e}')




# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: CORRECCIÓN DE REGISTROS — HTML embebido directamente
# ──────────────────────────────────────────────────────────────────────────────
import streamlit.components.v1 as _components

_CORRECCION_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QALAT — Corrección TOP · Perú</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --azul:       #1a3a5c;
    --azul-med:   #2563a8;
    --azul-claro: #dbeafe;
    --verde:      #16a34a;
    --naranja:    #d97706;
    --rojo:       #dc2626;
    --gris-bg:    #e8eef6;
    --gris-borde: #b0c4de;
    --blanco:     #ffffff;
    --texto:      #1e293b;
    --texto-suave:#4a6080;
    --radio:      6px;
    --sombra:     0 2px 8px rgba(26,58,92,.13);
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'IBM Plex Sans', sans-serif;
    background: linear-gradient(160deg, #1a3a5c 0%, #2563a8 40%, #3b82c4 70%, #dbeafe 100%);
    background-attachment: fixed;
    color: var(--texto);
    min-height: 100vh;
    padding-bottom: 60px;
  }

  header {
    background: rgba(10,25,47,0.93);
    backdrop-filter: blur(6px);
    color: #fff;
    padding: 14px 28px;
    display: flex;
    align-items: center;
    gap: 18px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 12px rgba(0,0,0,.3);
    border-bottom: 2px solid #d97706;
  }
  header .header-texto { display: flex; flex-direction: column; gap: 2px; }
  header .titulo-form { font-size: .95rem; font-weight: 600; color: #fcd34d; letter-spacing: .5px; }
  header .subtitulo   { font-size: .78rem; opacity: .65; color: #cbd5e1; }
  header .pais-badge {
    margin-left: auto;
    background: #dc2626;
    color: #fff;
    font-size: .75rem;
    font-weight: 700;
    padding: 5px 14px;
    border-radius: 20px;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  header .modo-badge {
    background: #d97706;
    color: #fff;
    font-size: .72rem;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 1px;
    text-transform: uppercase;
  }

  .contenedor { max-width: 860px; margin: 28px auto; padding: 0 16px; }

  /* ── BÚSQUEDA ── */
  .busqueda-card {
    background: rgba(255,255,255,.97);
    border-radius: 10px;
    box-shadow: var(--sombra);
    margin-bottom: 20px;
    overflow: hidden;
    border: 2px solid #d97706;
  }
  .busqueda-header {
    background: #d97706;
    color: #fff;
    padding: 12px 20px;
    font-size: .85rem;
    font-weight: 700;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .busqueda-body { padding: 20px; }
  .busqueda-grid { display: grid; grid-template-columns: 1fr 1fr auto; gap: 14px; align-items: end; }
  .fecha-busq-grid { display: grid; grid-template-columns: 1fr 1fr 1.3fr; gap: 8px; }

  @media (max-width: 600px) {
    .busqueda-grid { grid-template-columns: 1fr; }
  }

  .campo { display: flex; flex-direction: column; gap: 5px; }
  .campo label {
    font-size: .75rem; font-weight: 700;
    color: var(--texto-suave);
    text-transform: uppercase; letter-spacing: .6px;
  }
  .campo input, .campo select {
    border: 1.5px solid var(--gris-borde);
    border-radius: var(--radio);
    padding: 9px 12px;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: .9rem;
    color: var(--texto);
    background: var(--blanco);
    width: 100%;
  }
  .campo input:focus, .campo select:focus {
    outline: none;
    border-color: var(--azul-med);
    box-shadow: 0 0 0 3px rgba(37,99,168,.12);
  }
  .campo input.error { border-color: var(--rojo); }

  .btn-buscar {
    background: var(--azul-med);
    color: #fff;
    border: none;
    border-radius: var(--radio);
    padding: 10px 24px;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: .9rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: background .15s;
    height: 42px;
  }
  .btn-buscar:hover { background: #1a3a5c; }
  .btn-buscar:disabled { background: #94a3b8; cursor: not-allowed; }

  /* ── REGISTRO ENCONTRADO ── */
  .seccion {
    background: rgba(255,255,255,.97);
    border-radius: 10px;
    box-shadow: var(--sombra);
    margin-bottom: 20px;
    overflow: hidden;
    border: 1px solid rgba(37,99,168,.15);
  }
  .seccion-header {
    background: var(--azul);
    color: #fff;
    padding: 12px 20px;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .seccion-header .num {
    background: rgba(255,255,255,.22);
    width: 24px; height: 24px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: .75rem; font-weight: 700;
  }
  .seccion-body { padding: 20px; }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .span-2 { grid-column: span 2; }
  @media (max-width: 600px) {
    .grid-2 { grid-template-columns: 1fr; }
    .span-2 { grid-column: span 1; }
  }

  /* Banner registro encontrado */
  .registro-encontrado {
    background: #dcfce7;
    border: 1.5px solid #16a34a;
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: .88rem;
    color: #14532d;
    font-weight: 600;
  }

  /* Banner advertencia edición */
  .advertencia-edicion {
    background: #fef3c7;
    border: 1.5px solid #d97706;
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 18px;
    font-size: .82rem;
    color: #78350f;
  }
  .advertencia-edicion strong { color: #92400e; }

  /* ── TABLA SUSTANCIAS ── */
  .tabla-wrap { overflow-x: auto; }
  table.sustancias {
    width: 100%; border-collapse: collapse; font-size: .82rem;
  }
  table.sustancias th {
    background: var(--azul); color: #fff;
    padding: 8px 10px; text-align: center;
    font-weight: 700; font-size: .73rem;
    letter-spacing: .5px; white-space: nowrap;
  }
  table.sustancias th:first-child { text-align: left; min-width: 140px; }
  table.sustancias td {
    padding: 6px 6px;
    border-bottom: 1px solid #e2eaf4;
    vertical-align: middle;
  }
  table.sustancias tr:last-child td { border-bottom: none; }
  table.sustancias tr:hover td { background: #f5f8fc; }
  table.sustancias td:first-child { font-weight: 600; padding-left: 10px; color: var(--texto); }
  table.sustancias td.total-cell {
    background: var(--azul-claro);
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 700; text-align: center;
    color: var(--azul); font-size: .85rem;
  }

  input.num-inp {
    width: 62px; border: 1.5px solid var(--gris-borde);
    border-radius: 4px; padding: 6px 4px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: .88rem; text-align: center;
    color: var(--texto); display: block; margin: 0 auto;
    -moz-appearance: textfield;
  }
  input.num-inp::-webkit-inner-spin-button,
  input.num-inp::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
  input.num-inp:focus {
    outline: none; border-color: var(--azul-med);
    box-shadow: 0 0 0 2px rgba(37,99,168,.14);
  }
  input.num-inp.inp-error { background: #fee2e2; border-color: var(--rojo); }

  input.prom-inp {
    width: 72px; border: 1.5px solid var(--gris-borde);
    border-radius: 4px; padding: 6px 4px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: .85rem; text-align: center;
    color: var(--texto-suave); display: block; margin: 0 auto;
    -moz-appearance: textfield;
  }
  input.prom-inp::-webkit-inner-spin-button,
  input.prom-inp::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }

  td.total-cell { min-width: 52px; }
  .sep { border: none; border-top: 1px solid #e2eaf4; margin: 16px 0; }

  /* ── TRANSGRESIÓN ── */
  .transgresion-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(175px, 1fr));
    gap: 12px; margin-bottom: 16px;
  }
  .toggle-campo { display: flex; flex-direction: column; gap: 5px; }
  .toggle-campo label {
    font-size: .75rem; font-weight: 700;
    color: var(--texto-suave);
    text-transform: uppercase; letter-spacing: .5px;
  }
  .toggle-btn-group { display: flex; border-radius: var(--radio); overflow: hidden; border: 1.5px solid var(--gris-borde); }
  .toggle-btn-group button {
    flex: 1; padding: 8px 0;
    border: none; background: var(--blanco);
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: .85rem; font-weight: 500;
    cursor: pointer; transition: background .15s, color .15s;
    color: var(--texto-suave);
  }
  .toggle-btn-group button:first-child { border-right: 1px solid var(--gris-borde); }
  .toggle-btn-group button.activo-si { background: #dcfce7; color: #16a34a; font-weight: 700; }
  .toggle-btn-group button.activo-no { background: #fee2e2; color: #dc2626; font-weight: 700; }

  table.vif-table {
    width: auto; border-collapse: collapse; font-size: .82rem; margin-top: 4px;
  }
  table.vif-table th {
    background: var(--azul); color: #fff;
    padding: 7px 12px; font-size: .73rem;
    text-align: center; font-weight: 700;
  }
  table.vif-table td { padding: 6px 8px; border-bottom: 1px solid #e2eaf4; }
  table.vif-table td.total-cell {
    background: var(--azul-claro);
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 700; color: var(--azul); text-align: center;
  }

  /* ── ESCALA 0-20 ── */
  .escala-wrap { margin-bottom: 16px; }
  .escala-label {
    font-size: .75rem; font-weight: 700; color: var(--texto-suave);
    text-transform: uppercase; letter-spacing: .6px; margin-bottom: 8px;
  }
  .escala-extremos {
    display: flex; justify-content: space-between;
    font-size: .68rem; font-weight: 600; color: var(--texto-suave);
    text-transform: uppercase; letter-spacing: .4px;
    margin-bottom: 4px; padding: 0 2px;
  }
  .escala-opciones { display: flex; flex-wrap: wrap; gap: 5px; }
  .escala-opciones label {
    display: flex; align-items: center; justify-content: center;
    background: var(--gris-bg);
    border: 1.5px solid var(--gris-borde);
    border-radius: 50%;
    width: 36px; height: 36px;
    cursor: pointer; font-size: .78rem; font-weight: 600;
    transition: all .15s; text-align: center;
    color: var(--texto); flex-shrink: 0;
  }
  .escala-opciones input[type=radio] { display: none; }
  .escala-opciones label:hover { background: #dbeafe; border-color: var(--azul-med); }
  .escala-opciones label:has(input:checked) {
    background: var(--azul-med); border-color: var(--azul-med);
    color: #fff; transform: scale(1.12);
    box-shadow: 0 2px 8px rgba(37,99,168,.35);
  }

  /* Vivienda */
  .vivienda-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }

  /* ── BOTÓN GUARDAR ── */
  .btn-guardar {
    display: block; width: 100%; padding: 16px;
    background: #d97706;
    color: #fff; border: none; border-radius: 8px;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.05rem; font-weight: 700;
    cursor: pointer; letter-spacing: .3px;
    box-shadow: 0 4px 14px rgba(217,119,6,.35);
    transition: background .15s, box-shadow .15s;
    margin-top: 8px;
  }
  .btn-guardar:hover { background: #b45309; box-shadow: 0 6px 18px rgba(217,119,6,.45); }
  .btn-guardar:disabled { background: #94a3b8; cursor: not-allowed; box-shadow: none; }

  .nota { text-align: center; font-size: .78rem; color: rgba(255,255,255,.7); margin-top: 10px; }

  /* ── TOAST ── */
  #toast {
    display: none; position: fixed; bottom: 28px; left: 50%;
    transform: translateX(-50%);
    background: #16a34a; color: #fff;
    padding: 12px 28px; border-radius: 8px;
    font-size: .9rem; font-weight: 600;
    box-shadow: 0 4px 16px rgba(0,0,0,.25);
    z-index: 999; min-width: 260px; text-align: center;
  }
  #toast.error-toast { background: #dc2626; }
  #toast.warn-toast  { background: #d97706; }

  /* Estado vacío */
  #formulario-correc { display: none; }
  .estado-inicial {
    text-align: center; padding: 3rem;
    color: rgba(255,255,255,.8);
  }
  .estado-inicial .icono { font-size: 3rem; margin-bottom: 1rem; }
  .estado-inicial p { font-size: 1rem; }
  .estado-inicial small { font-size: .85rem; opacity: .7; }
</style>
</head>
<body>

<header>
  <div class="header-texto">
    <div class="titulo-form">✏️ Corrección de Registros TOP</div>
    <div class="subtitulo">Proyecto QALAT · UNODC Chile</div>
    <div class="subtitulo">© Rodrigo Portilla · UNODC</div>
  </div>
  <span class="modo-badge">✏️ Edición</span>
  <span class="pais-badge">🇵🇪 Perú</span>
</header>

<div class="contenedor">

  <!-- ══ BÚSQUEDA ══ -->
  <div class="busqueda-card">
    <div class="busqueda-header">🔍 Buscar registro a corregir</div>
    <div class="busqueda-body">
      <div class="advertencia-edicion">
        <strong>⚠️ Módulo de corrección.</strong> Busca el registro por código de paciente y fecha de entrevista. Los cambios que guardes se aplicarán directamente en la base de datos QALAT.
      </div>
      <div class="busqueda-grid">
        <div class="campo">
          <label>Código de paciente</label>
          <input type="text" id="busq_codigo" placeholder="Ej: ROPE15031985" maxlength="12"
                 style="text-transform:uppercase;font-family:'IBM Plex Mono',monospace;letter-spacing:1px">
        </div>
        <div class="campo">
          <label>Fecha de entrevista</label>
          <div class="fecha-busq-grid">
            <input type="text" id="busq_dia" placeholder="DD" maxlength="2"
                   style="font-family:'IBM Plex Mono',monospace;text-align:center;border:1.5px solid var(--gris-borde);border-radius:var(--radio);padding:9px 6px;font-size:.9rem;width:100%">
            <input type="text" id="busq_mes" placeholder="MM" maxlength="2"
                   style="font-family:'IBM Plex Mono',monospace;text-align:center;border:1.5px solid var(--gris-borde);border-radius:var(--radio);padding:9px 6px;font-size:.9rem;width:100%">
            <input type="text" id="busq_anio" placeholder="AAAA" maxlength="4"
                   style="font-family:'IBM Plex Mono',monospace;text-align:center;border:1.5px solid var(--gris-borde);border-radius:var(--radio);padding:9px 6px;font-size:.9rem;width:100%">
          </div>
          <small style="color:var(--texto-suave);font-size:.7rem;margin-top:3px">Día · Mes · Año — puedes pegar la fecha</small>
        </div>
        <button class="btn-buscar" id="btnBuscar" onclick="buscarRegistro()">🔍 Buscar</button>
      </div>
    </div>
  </div>

  <!-- ══ ESTADO INICIAL ══ -->
  <div class="estado-inicial" id="estadoInicial">
    <div class="icono">🔍</div>
    <p>Ingresa el código de paciente y la fecha de entrevista para buscar el registro</p>
    <small>Solo puedes editar registros de Perú</small>
  </div>

  <!-- ══ FORMULARIO DE CORRECCIÓN ══ -->
  <div id="formulario-correc">

    <div class="registro-encontrado" id="bannerEncontrado">
      ✅ Registro encontrado — edita los campos que necesitas corregir y presiona Guardar cambios
    </div>

    <!-- Sección 0: Identificación -->
    <div class="seccion">
      <div class="seccion-header"><span class="num">0</span> Datos de Identificación</div>
      <div class="seccion-body">
        <div class="grid-2">
          <div class="campo">
            <label>Centro de tratamiento</label>
            <input type="text" id="centro" placeholder="Nombre del centro">
          </div>
          <div class="campo">
            <label>Etapa</label>
            <select id="etapa">
              <option value="">— Seleccione —</option>
              <option value="ingreso">Ingreso (TOP1)</option>
              <option value="seguimiento1">Seguimiento 1</option>
              <option value="seguimiento2">Seguimiento 2</option>
              <option value="egreso">Egreso</option>
            </select>
          </div>
          <div class="campo">
            <label>Código de paciente</label>
            <input type="text" id="codigo_paciente" maxlength="12"
                   style="text-transform:uppercase;font-family:'IBM Plex Mono',monospace;letter-spacing:1px"
                   placeholder="LLLLDDMMAAAA">
          </div>
          <div class="campo">
            <label>Fecha de entrevista</label>
            <input type="date" id="fecha_entrevista">
          </div>
          <div class="campo">
            <label>Fecha de nacimiento</label>
            <input type="date" id="fecha_nacimiento">
          </div>
          <div class="campo">
            <label>Sexo</label>
            <select id="sexo">
              <option value="">— Seleccione —</option>
              <option value="M">Masculino</option>
              <option value="F">Femenino</option>
              <option value="O">Otro</option>
            </select>
          </div>
          <div class="campo span-2">
            <label>Nombre del entrevistador</label>
            <input type="text" id="nombre_entrevistador" placeholder="Nombre completo">
          </div>
        </div>
      </div>
    </div>

    <!-- Sección 1: Sustancias -->
    <div class="seccion">
      <div class="seccion-header"><span class="num">1</span> Sección 1: Uso de Sustancias</div>
      <div class="seccion-body">
        <div class="tabla-wrap">
          <table class="sustancias">
            <thead>
              <tr>
                <th>Sustancia</th>
                <th>Última Semana</th>
                <th>Semana 3</th>
                <th>Semana 2</th>
                <th>Semana 1</th>
                <th>Total</th>
                <th>Promedio</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Alcohol</td>
                <td><input type="number" min="0" max="7" class="num-inp s4" data-sust="alcohol"></td>
                <td><input type="number" min="0" max="7" class="num-inp s3" data-sust="alcohol"></td>
                <td><input type="number" min="0" max="7" class="num-inp s2" data-sust="alcohol"></td>
                <td><input type="number" min="0" max="7" class="num-inp s1" data-sust="alcohol"></td>
                <td class="total-cell" id="alcohol_total"></td>
                <td><input type="number" step="any" class="prom-inp" id="alcohol_prom" placeholder="—"><br><small style="color:var(--texto-suave);font-size:.68rem;display:block;text-align:center">Tragos/día</small></td>
              </tr>
              <tr>
                <td>Marihuana</td>
                <td><input type="number" min="0" max="7" class="num-inp s4" data-sust="marihuana"></td>
                <td><input type="number" min="0" max="7" class="num-inp s3" data-sust="marihuana"></td>
                <td><input type="number" min="0" max="7" class="num-inp s2" data-sust="marihuana"></td>
                <td><input type="number" min="0" max="7" class="num-inp s1" data-sust="marihuana"></td>
                <td class="total-cell" id="marihuana_total"></td>
                <td><input type="number" step="any" class="prom-inp" id="marihuana_prom" placeholder="—"><br><small style="color:var(--texto-suave);font-size:.68rem;display:block;text-align:center">Pitos/día</small></td>
              </tr>
              <tr>
                <td>Pasta Base</td>
                <td><input type="number" min="0" max="7" class="num-inp s4" data-sust="pastabase"></td>
                <td><input type="number" min="0" max="7" class="num-inp s3" data-sust="pastabase"></td>
                <td><input type="number" min="0" max="7" class="num-inp s2" data-sust="pastabase"></td>
                <td><input type="number" min="0" max="7" class="num-inp s1" data-sust="pastabase"></td>
                <td class="total-cell" id="pastabase_total"></td>
                <td><input type="number" step="any" class="prom-inp" id="pastabase_prom" placeholder="—"><br><small style="color:var(--texto-suave);font-size:.68rem;display:block;text-align:center">Papelillos/día</small></td>
              </tr>
              <tr>
                <td>Cocaína</td>
                <td><input type="number" min="0" max="7" class="num-inp s4" data-sust="cocaina"></td>
                <td><input type="number" min="0" max="7" class="num-inp s3" data-sust="cocaina"></td>
                <td><input type="number" min="0" max="7" class="num-inp s2" data-sust="cocaina"></td>
                <td><input type="number" min="0" max="7" class="num-inp s1" data-sust="cocaina"></td>
                <td class="total-cell" id="cocaina_total"></td>
                <td><input type="number" step="any" class="prom-inp" id="cocaina_prom" placeholder="—"><br><small style="color:var(--texto-suave);font-size:.68rem;display:block;text-align:center">Gramos/día</small></td>
              </tr>
              <tr>
                <td>Sedantes o Tranquilizantes</td>
                <td><input type="number" min="0" max="7" class="num-inp s4" data-sust="sedantes"></td>
                <td><input type="number" min="0" max="7" class="num-inp s3" data-sust="sedantes"></td>
                <td><input type="number" min="0" max="7" class="num-inp s2" data-sust="sedantes"></td>
                <td><input type="number" min="0" max="7" class="num-inp s1" data-sust="sedantes"></td>
                <td class="total-cell" id="sedantes_total"></td>
                <td><input type="number" step="any" class="prom-inp" id="sedantes_prom" placeholder="—"><br><small style="color:var(--texto-suave);font-size:.68rem;display:block;text-align:center">Comprimidos/día</small></td>
              </tr>
              <tr class="otra-sust-fila">
                <td colspan="7" style="padding:8px 10px">
                  <input type="text" id="otra_sust_nombre" placeholder="Nombre de otra sustancia (si aplica)"
                         style="width:100%;border:1.5px solid var(--gris-borde);border-radius:4px;padding:6px 10px;font-family:inherit;font-size:.85rem;">
                </td>
              </tr>
              <tr>
                <td><em style="color:var(--texto-suave)">Otra sustancia problema</em></td>
                <td><input type="number" min="0" max="7" class="num-inp s4" data-sust="otra_sust"></td>
                <td><input type="number" min="0" max="7" class="num-inp s3" data-sust="otra_sust"></td>
                <td><input type="number" min="0" max="7" class="num-inp s2" data-sust="otra_sust"></td>
                <td><input type="number" min="0" max="7" class="num-inp s1" data-sust="otra_sust"></td>
                <td class="total-cell" id="otra_sust_total"></td>
                <td><input type="number" step="any" class="prom-inp" id="otra_sust_prom" placeholder="—"><br><small style="color:var(--texto-suave);font-size:.68rem;display:block;text-align:center">Medida/día</small></td>
              </tr>
            </tbody>
          </table>
        </div>
        <hr class="sep">
        <div class="campo">
          <label>Sustancia principal</label>
          <select id="sustancia_principal">
            <option value="">— Seleccione —</option>
            <option value="Alcohol">Alcohol</option>
            <option value="Marihuana">Marihuana</option>
            <option value="Pasta Base">Pasta Base</option>
            <option value="Cocaína">Cocaína</option>
            <option value="Sedantes">Sedantes</option>
            <option value="Otra">Otra sustancia</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Sección 2: Transgresión -->
    <div class="seccion">
      <div class="seccion-header"><span class="num">2</span> Sección 2: Transgresión a la Norma Social</div>
      <div class="seccion-body">
        <div class="transgresion-grid">
          <div class="toggle-campo">
            <label>Hurto</label>
            <div class="toggle-btn-group" id="tg-hurto">
              <button type="button" onclick="setToggle('hurto','S',this)">Sí</button>
              <button type="button" onclick="setToggle('hurto','N',this)">No</button>
            </div>
          </div>
          <div class="toggle-campo">
            <label>Robo</label>
            <div class="toggle-btn-group" id="tg-robo">
              <button type="button" onclick="setToggle('robo','S',this)">Sí</button>
              <button type="button" onclick="setToggle('robo','N',this)">No</button>
            </div>
          </div>
          <div class="toggle-campo">
            <label>Venta de droga</label>
            <div class="toggle-btn-group" id="tg-venta_droga">
              <button type="button" onclick="setToggle('venta_droga','S',this)">Sí</button>
              <button type="button" onclick="setToggle('venta_droga','N',this)">No</button>
            </div>
          </div>
          <div class="toggle-campo">
            <label>Riña / Pelea</label>
            <div class="toggle-btn-group" id="tg-rina_pelea">
              <button type="button" onclick="setToggle('rina_pelea','S',this)">Sí</button>
              <button type="button" onclick="setToggle('rina_pelea','N',this)">No</button>
            </div>
          </div>
          <div class="toggle-campo">
            <label>Otra acción</label>
            <div class="toggle-btn-group" id="tg-otra_accion">
              <button type="button" onclick="setToggle('otra_accion','S',this);mostrarOtraAccion(true)">Sí</button>
              <button type="button" onclick="setToggle('otra_accion','N',this);mostrarOtraAccion(false)">No</button>
            </div>
          </div>
        </div>
        <div id="otra-accion-desc-wrap" class="campo" style="display:none;margin-bottom:16px;">
          <label>Descripción de otra acción</label>
          <input type="text" id="otra_accion_desc" placeholder="Describa la acción">
        </div>

        <hr class="sep">
        <p style="font-size:.75rem;font-weight:700;color:var(--texto-suave);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">
          Violencia intrafamiliar (VIF) — días por semana (0–7)
        </p>
        <div class="tabla-wrap">
          <table class="vif-table">
            <thead>
              <tr><th>Última Semana</th><th>Semana 3</th><th>Semana 2</th><th>Semana 1</th><th>Total</th></tr>
            </thead>
            <tbody>
              <tr>
                <td><input type="number" id="vif_s4" min="0" max="7" class="num-inp" oninput="calcVif()"></td>
                <td><input type="number" id="vif_s3" min="0" max="7" class="num-inp" oninput="calcVif()"></td>
                <td><input type="number" id="vif_s2" min="0" max="7" class="num-inp" oninput="calcVif()"></td>
                <td><input type="number" id="vif_s1" min="0" max="7" class="num-inp" oninput="calcVif()"></td>
                <td class="total-cell" id="vif_total"></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Sección 3: Salud -->
    <div class="seccion">
      <div class="seccion-header"><span class="num">3</span> Sección 3: Salud y Funcionamiento Social</div>
      <div class="seccion-body">

        <!-- Salud psicológica -->
        <div class="escala-wrap">
          <div class="escala-label">3a. Salud Psicológica</div>
          <div class="escala-extremos"><span>0 · Pésima</span><span>20 · Excelente</span></div>
          <div class="escala-opciones">
            <label><input type="radio" name="salud_psicologica" value="0">0</label>
            <label><input type="radio" name="salud_psicologica" value="1">1</label>
            <label><input type="radio" name="salud_psicologica" value="2">2</label>
            <label><input type="radio" name="salud_psicologica" value="3">3</label>
            <label><input type="radio" name="salud_psicologica" value="4">4</label>
            <label><input type="radio" name="salud_psicologica" value="5">5</label>
            <label><input type="radio" name="salud_psicologica" value="6">6</label>
            <label><input type="radio" name="salud_psicologica" value="7">7</label>
            <label><input type="radio" name="salud_psicologica" value="8">8</label>
            <label><input type="radio" name="salud_psicologica" value="9">9</label>
            <label><input type="radio" name="salud_psicologica" value="10">10</label>
            <label><input type="radio" name="salud_psicologica" value="11">11</label>
            <label><input type="radio" name="salud_psicologica" value="12">12</label>
            <label><input type="radio" name="salud_psicologica" value="13">13</label>
            <label><input type="radio" name="salud_psicologica" value="14">14</label>
            <label><input type="radio" name="salud_psicologica" value="15">15</label>
            <label><input type="radio" name="salud_psicologica" value="16">16</label>
            <label><input type="radio" name="salud_psicologica" value="17">17</label>
            <label><input type="radio" name="salud_psicologica" value="18">18</label>
            <label><input type="radio" name="salud_psicologica" value="19">19</label>
            <label><input type="radio" name="salud_psicologica" value="20">20</label>
          </div>
        </div>

        <hr class="sep">
        <!-- Trabajo -->
        <p style="font-size:.75rem;font-weight:700;color:var(--texto-suave);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">3b. Trabajo remunerado — días por semana (0–7)</p>
        <div class="tabla-wrap" style="margin-bottom:16px;">
          <table class="vif-table">
            <thead><tr><th>Última Semana</th><th>Semana 3</th><th>Semana 2</th><th>Semana 1</th><th>Total</th></tr></thead>
            <tbody><tr>
              <td><input type="number" id="dias_trabajo_s4" min="0" max="7" class="num-inp" oninput="calcSimple('dias_trabajo')"></td>
              <td><input type="number" id="dias_trabajo_s3" min="0" max="7" class="num-inp" oninput="calcSimple('dias_trabajo')"></td>
              <td><input type="number" id="dias_trabajo_s2" min="0" max="7" class="num-inp" oninput="calcSimple('dias_trabajo')"></td>
              <td><input type="number" id="dias_trabajo_s1" min="0" max="7" class="num-inp" oninput="calcSimple('dias_trabajo')"></td>
              <td class="total-cell" id="dias_trabajo_total"></td>
            </tr></tbody>
          </table>
        </div>

        <!-- Educación -->
        <p style="font-size:.75rem;font-weight:700;color:var(--texto-suave);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">3c. Educación / Formación — días por semana (0–7)</p>
        <div class="tabla-wrap" style="margin-bottom:16px;">
          <table class="vif-table">
            <thead><tr><th>Última Semana</th><th>Semana 3</th><th>Semana 2</th><th>Semana 1</th><th>Total</th></tr></thead>
            <tbody><tr>
              <td><input type="number" id="dias_educacion_s4" min="0" max="7" class="num-inp" oninput="calcSimple('dias_educacion')"></td>
              <td><input type="number" id="dias_educacion_s3" min="0" max="7" class="num-inp" oninput="calcSimple('dias_educacion')"></td>
              <td><input type="number" id="dias_educacion_s2" min="0" max="7" class="num-inp" oninput="calcSimple('dias_educacion')"></td>
              <td><input type="number" id="dias_educacion_s1" min="0" max="7" class="num-inp" oninput="calcSimple('dias_educacion')"></td>
              <td class="total-cell" id="dias_educacion_total"></td>
            </tr></tbody>
          </table>
        </div>

        <hr class="sep">
        <!-- Salud física -->
        <div class="escala-wrap">
          <div class="escala-label">3e. Salud Física</div>
          <div class="escala-extremos"><span>0 · Pésima</span><span>20 · Excelente</span></div>
          <div class="escala-opciones">
            <label><input type="radio" name="salud_fisica" value="0">0</label>
            <label><input type="radio" name="salud_fisica" value="1">1</label>
            <label><input type="radio" name="salud_fisica" value="2">2</label>
            <label><input type="radio" name="salud_fisica" value="3">3</label>
            <label><input type="radio" name="salud_fisica" value="4">4</label>
            <label><input type="radio" name="salud_fisica" value="5">5</label>
            <label><input type="radio" name="salud_fisica" value="6">6</label>
            <label><input type="radio" name="salud_fisica" value="7">7</label>
            <label><input type="radio" name="salud_fisica" value="8">8</label>
            <label><input type="radio" name="salud_fisica" value="9">9</label>
            <label><input type="radio" name="salud_fisica" value="10">10</label>
            <label><input type="radio" name="salud_fisica" value="11">11</label>
            <label><input type="radio" name="salud_fisica" value="12">12</label>
            <label><input type="radio" name="salud_fisica" value="13">13</label>
            <label><input type="radio" name="salud_fisica" value="14">14</label>
            <label><input type="radio" name="salud_fisica" value="15">15</label>
            <label><input type="radio" name="salud_fisica" value="16">16</label>
            <label><input type="radio" name="salud_fisica" value="17">17</label>
            <label><input type="radio" name="salud_fisica" value="18">18</label>
            <label><input type="radio" name="salud_fisica" value="19">19</label>
            <label><input type="radio" name="salud_fisica" value="20">20</label>
          </div>
        </div>

        <hr class="sep">
        <!-- Vivienda -->
        <p style="font-size:.75rem;font-weight:700;color:var(--texto-suave);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">3f. Vivienda</p>
        <div class="vivienda-grid">
          <div class="toggle-campo">
            <label>Vivienda estable</label>
            <div class="toggle-btn-group" id="tg-vivienda_estable">
              <button type="button" onclick="setToggle('vivienda_estable','S',this)">Sí</button>
              <button type="button" onclick="setToggle('vivienda_estable','N',this)">No</button>
            </div>
          </div>
          <div class="toggle-campo">
            <label>Vivienda básica</label>
            <div class="toggle-btn-group" id="tg-vivienda_basica">
              <button type="button" onclick="setToggle('vivienda_basica','S',this)">Sí</button>
              <button type="button" onclick="setToggle('vivienda_basica','N',this)">No</button>
            </div>
          </div>
        </div>

        <hr class="sep">
        <!-- Calidad de vida -->
        <div class="escala-wrap">
          <div class="escala-label">3g. Calidad de Vida General</div>
          <div class="escala-extremos"><span>0 · Pésima</span><span>20 · Excelente</span></div>
          <div class="escala-opciones">
            <label><input type="radio" name="calidad_vida" value="0">0</label>
            <label><input type="radio" name="calidad_vida" value="1">1</label>
            <label><input type="radio" name="calidad_vida" value="2">2</label>
            <label><input type="radio" name="calidad_vida" value="3">3</label>
            <label><input type="radio" name="calidad_vida" value="4">4</label>
            <label><input type="radio" name="calidad_vida" value="5">5</label>
            <label><input type="radio" name="calidad_vida" value="6">6</label>
            <label><input type="radio" name="calidad_vida" value="7">7</label>
            <label><input type="radio" name="calidad_vida" value="8">8</label>
            <label><input type="radio" name="calidad_vida" value="9">9</label>
            <label><input type="radio" name="calidad_vida" value="10">10</label>
            <label><input type="radio" name="calidad_vida" value="11">11</label>
            <label><input type="radio" name="calidad_vida" value="12">12</label>
            <label><input type="radio" name="calidad_vida" value="13">13</label>
            <label><input type="radio" name="calidad_vida" value="14">14</label>
            <label><input type="radio" name="calidad_vida" value="15">15</label>
            <label><input type="radio" name="calidad_vida" value="16">16</label>
            <label><input type="radio" name="calidad_vida" value="17">17</label>
            <label><input type="radio" name="calidad_vida" value="18">18</label>
            <label><input type="radio" name="calidad_vida" value="19">19</label>
            <label><input type="radio" name="calidad_vida" value="20">20</label>
          </div>
        </div>

      </div>
    </div>

    <!-- Botón guardar -->
    <button type="button" class="btn-guardar" id="btnGuardar" onclick="guardarCambios()">
      ✓ &nbsp;Guardar cambios
    </button>
    <p class="nota">Los cambios se aplican directamente en la base de datos QALAT · UNODC Chile</p>

  </div><!-- fin formulario-correc -->
</div>

<div id="toast"></div>

<script>
const SUPABASE_URL = '%%SUPABASE_URL%%';
const SUPABASE_KEY = '%%SUPABASE_KEY%%';

// ID del registro encontrado (para el UPDATE)
let registroId = null;

// Toggles
const toggleValues = {
  hurto:null, robo:null, venta_droga:null,
  rina_pelea:null, otra_accion:null,
  vivienda_estable:null, vivienda_basica:null
};

function setToggle(campo, valor, btn) {
  toggleValues[campo] = valor;
  const group = btn.closest('.toggle-btn-group');
  group.querySelectorAll('button').forEach(b => b.classList.remove('activo-si','activo-no'));
  btn.classList.add(valor==='S' ? 'activo-si' : 'activo-no');
}
function mostrarOtraAccion(show) {
  document.getElementById('otra-accion-desc-wrap').style.display = show ? 'flex' : 'none';
}

// Toast
function mostrarToast(msg, tipo='ok') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = tipo === 'error' ? 'error-toast' : tipo === 'warn' ? 'warn-toast' : '';
  t.style.display = 'block';
  setTimeout(() => { t.style.display = 'none'; }, 5000);
}

// Cálculo totales sustancias
function calcAct(prefix) {
  const sems = ['s4','s3','s2','s1'];
  let total = null;
  sems.forEach(s => {
    const el = document.querySelector(`input.${s}[data-sust="${prefix}"]`);
    if (el && el.value !== '' && !el.classList.contains('inp-error')) {
      const v = parseInt(el.value);
      if (!isNaN(v)) total = (total === null ? 0 : total) + v;
    }
  });
  const tcell = document.getElementById(`${prefix}_total`);
  if (tcell) tcell.textContent = total !== null ? total : '';
}

function calcVif() {
  const ids = ['vif_s4','vif_s3','vif_s2','vif_s1'];
  let total = null;
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el && el.value !== '') {
      const v = parseInt(el.value);
      if (!isNaN(v)) total = (total === null ? 0 : total) + v;
    }
  });
  const tc = document.getElementById('vif_total');
  if (tc) tc.textContent = total !== null ? total : '';
}

function calcSimple(prefix) {
  const ids = [`${prefix}_s4`,`${prefix}_s3`,`${prefix}_s2`,`${prefix}_s1`];
  let total = null;
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el && el.value !== '') {
      const v = parseInt(el.value);
      if (!isNaN(v)) total = (total === null ? 0 : total) + v;
    }
  });
  const tc = document.getElementById(`${prefix}_total`);
  if (tc) tc.textContent = total !== null ? total : '';
}

// Inicializar listeners de sustancias
['alcohol','marihuana','pastabase','cocaina','sedantes','otra_sust'].forEach(prefix => {
  ['s4','s3','s2','s1'].forEach(s => {
    const el = document.querySelector(`input.${s}[data-sust="${prefix}"]`);
    if (!el) return;
    el.addEventListener('input', () => calcAct(prefix));
    el.addEventListener('blur', () => calcAct(prefix));
  });
});

// ── BÚSQUEDA ──────────────────────────────────────────────
async function buscarRegistro() {
  const codigo = document.getElementById('busq_codigo').value.trim().toUpperCase();
  const dia    = document.getElementById('busq_dia').value.trim().padStart(2,'0');
  const mes    = document.getElementById('busq_mes').value.trim().padStart(2,'0');
  const anio   = document.getElementById('busq_anio').value.trim();

  if (!codigo) {
    mostrarToast('⚠ Ingresa el código de paciente', 'error'); return;
  }
  if (!dia || !mes || !anio || anio.length !== 4) {
    mostrarToast('⚠ Ingresa la fecha completa (DD · MM · AAAA)', 'error'); return;
  }

  const fecha = `${anio}-${mes}-${dia}`;  // formato Supabase: YYYY-MM-DD

  const btn = document.getElementById('btnBuscar');
  btn.disabled = true;
  btn.textContent = 'Buscando…';

  try {
    const url = `${SUPABASE_URL}/rest/v1/top_registros?codigo_paciente=eq.${encodeURIComponent(codigo)}&fecha_entrevista=eq.${fecha}&pais=eq.Per%C3%BA&select=*`;
    const resp = await fetch(url, {
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': `Bearer ${SUPABASE_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    const data = await resp.json();

    if (!data || data.length === 0) {
      mostrarToast(`⚠ No se encontró registro: ${codigo} · ${dia}/${mes}/${anio}`, 'warn');
      document.getElementById('formulario-correc').style.display = 'none';
      document.getElementById('estadoInicial').style.display = 'block';
    } else {
      const reg = data[0];
      registroId = reg.id;
      poblarFormulario(reg);
      document.getElementById('estadoInicial').style.display = 'none';
      document.getElementById('formulario-correc').style.display = 'block';
      document.getElementById('bannerEncontrado').textContent =
        `✅ Registro encontrado — ID ${registroId} · ${codigo} · ${dia}/${mes}/${anio} — edita lo que necesitas y guarda`;
      mostrarToast('✓ Registro cargado correctamente');
    }
  } catch(e) {
    mostrarToast('Error de conexión al buscar: ' + e.message, 'error');
  }

  btn.disabled = false;
  btn.textContent = '🔍 Buscar';
}

// ── POBLAR FORMULARIO CON DATOS DEL REGISTRO ──────────────
function poblarFormulario(r) {
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el && val !== null && val !== undefined) el.value = val;
  };
  const setNum = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = (val !== null && val !== undefined) ? val : '';
  };
  const setTotal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = (val !== null && val !== undefined) ? val : '';
  };
  const setToggleBtn = (campo, val) => {
    if (!val) return;
    toggleValues[campo] = val;
    const group = document.getElementById(`tg-${campo}`);
    if (!group) return;
    group.querySelectorAll('button').forEach(b => b.classList.remove('activo-si','activo-no'));
    const btns = group.querySelectorAll('button');
    if (val === 'S' && btns[0]) btns[0].classList.add('activo-si');
    if (val === 'N' && btns[1]) btns[1].classList.add('activo-no');
  };
  const setRadio = (name, val) => {
    if (val === null || val === undefined) return;
    const radio = document.querySelector(`input[name="${name}"][value="${val}"]`);
    if (radio) radio.checked = true;
  };
  const setSustSem = (sust, sem, val) => {
    const el = document.querySelector(`input.${sem}[data-sust="${sust}"]`);
    if (el) el.value = (val !== null && val !== undefined) ? val : '';
  };

  // Identificación
  set('centro', r.centro);
  set('etapa', r.etapa);
  set('codigo_paciente', r.codigo_paciente);
  set('fecha_entrevista', r.fecha_entrevista);
  set('fecha_nacimiento', r.fecha_nacimiento);
  set('sexo', r.sexo);
  set('nombre_entrevistador', r.nombre_entrevistador);

  // Sustancias
  ['alcohol','marihuana','pastabase','cocaina','sedantes','otra_sust'].forEach(sust => {
    setSustSem(sust,'s4', r[`${sust}_s4`]);
    setSustSem(sust,'s3', r[`${sust}_s3`]);
    setSustSem(sust,'s2', r[`${sust}_s2`]);
    setSustSem(sust,'s1', r[`${sust}_s1`]);
    setTotal(`${sust}_total`, r[`${sust}_total`]);
    setNum(`${sust}_prom`, r[`${sust}_prom`]);
  });
  set('otra_sust_nombre', r.otra_sust_nombre);
  set('sustancia_principal', r.sustancia_principal);

  // Transgresión
  setToggleBtn('hurto', r.hurto);
  setToggleBtn('robo', r.robo);
  setToggleBtn('venta_droga', r.venta_droga);
  setToggleBtn('rina_pelea', r.rina_pelea);
  setToggleBtn('otra_accion', r.otra_accion);
  if (r.otra_accion === 'S') mostrarOtraAccion(true);
  set('otra_accion_desc', r.otra_accion_desc);

  // VIF
  setNum('vif_s4', r.vif_s4); setNum('vif_s3', r.vif_s3);
  setNum('vif_s2', r.vif_s2); setNum('vif_s1', r.vif_s1);
  setTotal('vif_total', r.vif_total);

  // Salud y funcionamiento
  setRadio('salud_psicologica', r.salud_psicologica);
  setNum('dias_trabajo_s4', r.dias_trabajo_s4); setNum('dias_trabajo_s3', r.dias_trabajo_s3);
  setNum('dias_trabajo_s2', r.dias_trabajo_s2); setNum('dias_trabajo_s1', r.dias_trabajo_s1);
  setTotal('dias_trabajo_total', r.dias_trabajo_total);
  setNum('dias_educacion_s4', r.dias_educacion_s4); setNum('dias_educacion_s3', r.dias_educacion_s3);
  setNum('dias_educacion_s2', r.dias_educacion_s2); setNum('dias_educacion_s1', r.dias_educacion_s1);
  setTotal('dias_educacion_total', r.dias_educacion_total);
  setRadio('salud_fisica', r.salud_fisica);
  setToggleBtn('vivienda_estable', r.vivienda_estable);
  setToggleBtn('vivienda_basica', r.vivienda_basica);
  setRadio('calidad_vida', r.calidad_vida);
}

// ── GUARDAR CAMBIOS (UPDATE) ──────────────────────────────
async function guardarCambios() {
  if (!registroId) {
    mostrarToast('⚠ Primero busca un registro', 'warn');
    return;
  }

  const btn = document.getElementById('btnGuardar');
  btn.disabled = true;
  btn.textContent = 'Guardando…';

  const n = id => { const v = parseFloat(document.getElementById(id)?.value); return isNaN(v) ? null : v; };
  const s = id => document.getElementById(id)?.value || null;
  const sv = (sust, sem) => {
    const el = document.querySelector(`input.${sem}[data-sust="${sust}"]`);
    return (el && el.value !== '') ? parseInt(el.value) : null;
  };
  const tv = id => { const el = document.getElementById(id); return el ? parseInt(el.textContent) || null : null; };
  const pv = id => { const el = document.getElementById(id); return el && el.value !== '' ? parseFloat(el.value) : null; };

  const payload = {
    centro: s('centro'), etapa: s('etapa'),
    codigo_paciente: s('codigo_paciente'),
    fecha_entrevista: s('fecha_entrevista'),
    fecha_nacimiento: s('fecha_nacimiento') || null,
    sexo: s('sexo') || null,
    nombre_entrevistador: s('nombre_entrevistador') || null,

    alcohol_s4: sv('alcohol','s4'), alcohol_s3: sv('alcohol','s3'),
    alcohol_s2: sv('alcohol','s2'), alcohol_s1: sv('alcohol','s1'),
    alcohol_total: tv('alcohol_total'), alcohol_prom: pv('alcohol_prom'),

    marihuana_s4: sv('marihuana','s4'), marihuana_s3: sv('marihuana','s3'),
    marihuana_s2: sv('marihuana','s2'), marihuana_s1: sv('marihuana','s1'),
    marihuana_total: tv('marihuana_total'), marihuana_prom: pv('marihuana_prom'),

    pastabase_s4: sv('pastabase','s4'), pastabase_s3: sv('pastabase','s3'),
    pastabase_s2: sv('pastabase','s2'), pastabase_s1: sv('pastabase','s1'),
    pastabase_total: tv('pastabase_total'), pastabase_prom: pv('pastabase_prom'),

    cocaina_s4: sv('cocaina','s4'), cocaina_s3: sv('cocaina','s3'),
    cocaina_s2: sv('cocaina','s2'), cocaina_s1: sv('cocaina','s1'),
    cocaina_total: tv('cocaina_total'), cocaina_prom: pv('cocaina_prom'),

    sedantes_s4: sv('sedantes','s4'), sedantes_s3: sv('sedantes','s3'),
    sedantes_s2: sv('sedantes','s2'), sedantes_s1: sv('sedantes','s1'),
    sedantes_total: tv('sedantes_total'), sedantes_prom: pv('sedantes_prom'),

    otra_sust_nombre: s('otra_sust_nombre') || null,
    otra_sust_s4: sv('otra_sust','s4'), otra_sust_s3: sv('otra_sust','s3'),
    otra_sust_s2: sv('otra_sust','s2'), otra_sust_s1: sv('otra_sust','s1'),
    otra_sust_total: tv('otra_sust_total'), otra_sust_prom: pv('otra_sust_prom'),

    sustancia_principal: s('sustancia_principal'),

    hurto: toggleValues.hurto, robo: toggleValues.robo,
    venta_droga: toggleValues.venta_droga, rina_pelea: toggleValues.rina_pelea,
    otra_accion: toggleValues.otra_accion,
    otra_accion_desc: s('otra_accion_desc') || null,
    vif_s4: n('vif_s4'), vif_s3: n('vif_s3'), vif_s2: n('vif_s2'), vif_s1: n('vif_s1'),
    vif_total: tv('vif_total'),

    salud_psicologica: parseInt(document.querySelector('input[name="salud_psicologica"]:checked')?.value ?? 'NaN') || null,
    dias_trabajo_s4: n('dias_trabajo_s4'), dias_trabajo_s3: n('dias_trabajo_s3'),
    dias_trabajo_s2: n('dias_trabajo_s2'), dias_trabajo_s1: n('dias_trabajo_s1'),
    dias_trabajo_total: tv('dias_trabajo_total'),
    dias_educacion_s4: n('dias_educacion_s4'), dias_educacion_s3: n('dias_educacion_s3'),
    dias_educacion_s2: n('dias_educacion_s2'), dias_educacion_s1: n('dias_educacion_s1'),
    dias_educacion_total: tv('dias_educacion_total'),
    salud_fisica: parseInt(document.querySelector('input[name="salud_fisica"]:checked')?.value ?? 'NaN') || null,
    vivienda_estable: toggleValues.vivienda_estable,
    vivienda_basica: toggleValues.vivienda_basica,
    calidad_vida: parseInt(document.querySelector('input[name="calidad_vida"]:checked')?.value ?? 'NaN') || null
  };

  try {
    const resp = await fetch(`${SUPABASE_URL}/rest/v1/top_registros?id=eq.${registroId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_KEY,
        'Authorization': `Bearer ${SUPABASE_KEY}`,
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify(payload)
    });

    if (resp.ok || resp.status === 204) {
      mostrarToast('✓ Cambios guardados correctamente en la base de datos');
    } else {
      const err = await resp.json();
      mostrarToast('Error al guardar: ' + (err.message || resp.status), 'error');
    }
  } catch(e) {
    mostrarToast('Error de conexión. Verifique su internet.', 'error');
  }

  btn.disabled = false;
  btn.textContent = '✓ Guardar cambios';
}

// Enter en búsqueda
['busq_codigo','busq_dia','busq_mes','busq_anio'].forEach(id => {
  document.getElementById(id).addEventListener('keydown', e => {
    if (e.key === 'Enter') buscarRegistro();
  });
});
document.getElementById('busq_codigo').addEventListener('input', function() {
  const pos = this.selectionStart;
  this.value = this.value.toUpperCase();
  this.setSelectionRange(pos, pos);
});
</script>
</body>
</html>
"""

CORRECCION_URLS = {
    'Perú':        'https://portilla3.github.io/App-TOP-3-Paises/correccion_top_peru.html',
    'Ecuador':     'https://portilla3.github.io/App-TOP-3-Paises/correccion_top_ecuador.html',
    'México':      'https://portilla3.github.io/App-TOP-3-Paises/correccion_top_mexico.html',
    'México CIJ':  'https://portilla3.github.io/App-TOP-3-Paises/correccion_top_mexicocij.html',
    'El Salvador': 'https://portilla3.github.io/App-TOP-3-Paises/correccion_top_elsalvador.html',
}
CORRECCION_FLAGS = {'Perú': '🇵🇪', 'Ecuador': '🇪🇨', 'México': '🇲🇽', 'México CIJ': '🇲🇽', 'El Salvador': '🇸🇻'}

with tab_correccion:
    if rol not in ('Perú', 'Ecuador', 'México', 'México CIJ', 'El Salvador', 'UNODC'):
        st.info(f'El formulario de corrección para {flag} {rol} estará disponible próximamente.')
    else:
        if es_unodc:
            pais_corr = st.selectbox(
                'Corregir registros de:',
                ['Perú', 'Ecuador', 'México', 'México CIJ', 'El Salvador'],
                key='corr_pais_sel'
            )
        else:
            pais_corr = rol

        flag_corr = CORRECCION_FLAGS.get(pais_corr, '')
        url_corr  = CORRECCION_URLS[pais_corr]

        st.markdown(
            f'''<div style="background:#FFF8E1;border-left:4px solid #F9A825;
            padding:.7rem 1.2rem;border-radius:6px;margin-bottom:1rem;font-size:.85rem;">
            <b>⚠ Módulo de corrección — {flag_corr} {pais_corr}.</b>
            Los cambios se aplican directamente en la base de datos QALAT.
            </div>''', unsafe_allow_html=True
        )
        st.link_button(
            "✏️ Abrir formulario de corrección",
            url_corr,
            use_container_width=True
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: MIGRACIÓN JOTFORM → SUPABASE (solo UNODC)
# ══════════════════════════════════════════════════════════════════════════════
if es_unodc and tab_migracion is not None:
    with tab_migracion:
        st.markdown(
            '<div style="background:#FFF3E0;border-left:4px solid #E65100;'
            'padding:.8rem 1.2rem;border-radius:6px;margin-bottom:1.2rem;font-size:.88rem;">'
            '<b>⚠ Módulo exclusivo UNODC.</b> Permite cargar registros históricos desde un '
            'Excel exportado de JotForm directamente a Supabase. Úsalo para pruebas de '
            'migración y bórralo después si es necesario.</div>',
            unsafe_allow_html=True
        )

        col_p, col_f = st.columns([1, 2])
        with col_p:
            pais_migra = st.selectbox('País de los datos', PAISES_ACTIVOS, key='migra_pais')
        with col_f:
            excel_migra = st.file_uploader(
                'Sube el Excel exportado de JotForm',
                type=['xlsx', 'xls'],
                key='migra_file'
            )

        if excel_migra:
            import io
            df_migra = pd.read_excel(io.BytesIO(excel_migra.getvalue()))
            st.success(f'✓ Archivo leído: {len(df_migra)} filas detectadas')

            if st.button('🔄 Preparar registros para migración', key='btn_preparar_migra'):
                with st.spinner('Mapeando columnas...'):
                    registros_migra, errores_migra = _migrar_excel_jotform(df_migra, pais_migra)
                st.session_state['migra_registros'] = registros_migra
                st.session_state['migra_errores']   = errores_migra
                st.session_state['migra_pais_sel']  = pais_migra
                if registros_migra:
                    st.markdown('**Primer registro construido (debug):**')
                    st.json(registros_migra[0])

            if 'migra_registros' in st.session_state:
                regs  = st.session_state['migra_registros']
                errs  = st.session_state['migra_errores']
                pais_sel = st.session_state['migra_pais_sel']

                st.markdown(f'**{len(regs)} registros listos para insertar** en Supabase (país: {pais_sel})')
                if errs:
                    st.warning(f'⚠ {len(errs)} filas con error de mapeo (no se insertarán)')

                st.markdown('---')
                st.markdown('**Confirmar inserción:**')

                if st.button(f'✅ Insertar {len(regs)} registros en Supabase', key='btn_confirmar_migra',
                             type='primary'):
                    LOTE = 50
                    total_ok = 0
                    errores_insert = []
                    progress = st.progress(0)
                    for i in range(0, len(regs), LOTE):
                        lote = regs[i:i+LOTE]
                        try:
                            _insertar_lote_supabase(lote)
                            total_ok += len(lote)
                        except Exception as e:
                            err_str = str(e)
                            # Mostrar detalle del error HTTP si está disponible
                            if hasattr(e, 'read'):
                                try: err_str += ' | ' + e.read().decode('utf-8')
                                except: pass
                            errores_insert.append(err_str)
                            st.error(f'Error detallado: {err_str}')
                            break
                        progress.progress(min((i + LOTE) / len(regs), 1.0))

                    if total_ok == len(regs):
                        st.success(f'🎉 {total_ok} registros migrados correctamente a Supabase.')
                    else:
                        st.warning(f'⚠ {total_ok}/{len(regs)} insertados. Errores: {errores_insert[:3]}')

                    st.session_state.pop('migra_registros', None)

        st.markdown('---')
        st.markdown('<div class="sec" style="background:#C00000;">🗑 Borrar registros de prueba</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div style="background:#FFEBEE;border-left:4px solid #C00000;'
            'padding:.7rem 1.2rem;border-radius:6px;margin-bottom:1rem;font-size:.85rem;">'
            'Elimina <b>todos</b> los registros del país seleccionado en Supabase. '
            'Usar solo después de una migración de prueba.</div>',
            unsafe_allow_html=True
        )
        pais_borrar = st.selectbox('País a borrar', PAISES_ACTIVOS, key='borrar_pais')
        confirmar_borrar = st.text_input(
            f'Escribe BORRAR para confirmar la eliminación de todos los registros de {pais_borrar}',
            key='confirmar_borrar'
        )
        if st.button('🗑 Eliminar todos los registros del país', key='btn_borrar', type='primary'):
            if confirmar_borrar == 'BORRAR':
                try:
                    _eliminar_por_pais(pais_borrar)
                    st.success(f'✓ Todos los registros de {pais_borrar} eliminados de Supabase.')
                except Exception as e:
                    st.error(f'Error al borrar: {e}')
            else:
                st.error('Debes escribir exactamente BORRAR para confirmar.')


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: RESPALDOS (solo UNODC)
# ══════════════════════════════════════════════════════════════════════════════
if es_unodc and tab_respaldos is not None:
    with tab_respaldos:
        st.markdown(
            '<div style="background:#E3F2FD;border-left:4px solid #1F3864;'
            'padding:.8rem 1.2rem;border-radius:6px;margin-bottom:1.2rem;font-size:.88rem;">'
            '<b>💾 Módulo exclusivo UNODC.</b> Permite generar respaldos completos '
            'de la base de datos QALAT. El respaldo Excel se descarga a tu computador '
            'y se guarda donde tú decidas. El snapshot en Supabase queda en la base '
            'como copia de seguridad interna (retención automática de 12 semanas).'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown('<div class="sec">📊 Estado actual</div>', unsafe_allow_html=True)
        try:
            stats = _stats_backup()
        except Exception as e:
            st.error(f'No se pudo cargar el panel de estado: {e}')
            stats = {}

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            n_vivos = stats.get('num_registros_vivos')
            st.markdown(
                f'<div class="kpi"><div class="kpi-lbl">Registros vivos</div>'
                f'<div class="kpi-val">{n_vivos if n_vivos is not None else "—"}</div>'
                f'<div class="kpi-sub">en top_registros</div></div>',
                unsafe_allow_html=True
            )

        with col2:
            us = stats.get('ultimo_snapshot')
            if us:
                fecha_str = us['fecha'][:16].replace('T', ' ')
                subtxt = f'{us["num_registros"]} registros'
            else:
                fecha_str = 'Nunca'
                subtxt = 'Sin snapshots aún'
            st.markdown(
                f'<div class="kpi green"><div class="kpi-lbl">Último snapshot Supabase</div>'
                f'<div class="kpi-val" style="font-size:1.1rem;">{fecha_str}</div>'
                f'<div class="kpi-sub">{subtxt}</div></div>',
                unsafe_allow_html=True
            )

        with col3:
            n_snap = stats.get('num_snapshots_vivos')
            st.markdown(
                f'<div class="kpi"><div class="kpi-lbl">Snapshots almacenados</div>'
                f'<div class="kpi-val">{n_snap if n_snap is not None else "—"}</div>'
                f'<div class="kpi-sub">retención: 12 semanas</div></div>',
                unsafe_allow_html=True
            )

        with col4:
            ue = stats.get('ultimo_excel')
            if ue:
                fecha_str = ue['fecha'][:16].replace('T', ' ')
            else:
                fecha_str = 'Nunca'
            st.markdown(
                f'<div class="kpi orange"><div class="kpi-lbl">Última descarga Excel</div>'
                f'<div class="kpi-val" style="font-size:1.1rem;">{fecha_str}</div>'
                f'<div class="kpi-sub">último registrado</div></div>',
                unsafe_allow_html=True
            )

        st.markdown('<br>', unsafe_allow_html=True)

        st.markdown('<div class="sec">1️⃣ Descargar respaldo Excel</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:.85rem;color:#555;margin-bottom:.8rem;">'
            'Descarga un archivo <code>.xlsx</code> con todos los registros de <code>top_registros</code>. '
            'Se abre directamente en Excel. Este archivo es tu respaldo de largo plazo: guárdalo '
            'en Google Drive, disco duro externo o donde tu institución lo respalde. '
            'No queda copia en Supabase.'
            '</div>',
            unsafe_allow_html=True
        )

        if st.button('📥 Generar archivo Excel', key='btn_gen_excel', type='primary'):
            with st.spinner('Descargando registros y armando Excel...'):
                try:
                    registros = _leer_todos_registros_full()
                    if not registros:
                        st.warning('No hay registros en la base para respaldar.')
                    else:
                        buf = _generar_excel_backup(registros)
                        from datetime import datetime as _dt
                        nombre = f'respaldo_top_registros_{_dt.now().strftime("%Y-%m-%d_%H%M%S")}.xlsx'
                        st.session_state['backup_excel_buf'] = buf.getvalue()
                        st.session_state['backup_excel_nombre'] = nombre
                        _registrar_backup_log(
                            tipo='excel_export',
                            num_registros=len(registros),
                            notas=f'Archivo generado: {nombre}'
                        )
                        st.success(f'✓ Archivo listo: {len(registros)} registros. Click abajo para descargar.')
                except Exception as e:
                    st.error(f'Error generando Excel: {e}')

        if 'backup_excel_buf' in st.session_state:
            st.download_button(
                label='⬇ Descargar ' + st.session_state.get('backup_excel_nombre', 'respaldo.xlsx'),
                data=st.session_state['backup_excel_buf'],
                file_name=st.session_state.get('backup_excel_nombre', 'respaldo.xlsx'),
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                key='dl_excel_backup'
            )

        st.markdown('<br>', unsafe_allow_html=True)

        st.markdown('<div class="sec">2️⃣ Crear snapshot en Supabase</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:.85rem;color:#555;margin-bottom:.8rem;">'
            'Crea una copia interna de <code>top_registros</code> en la tabla <code>top_registros_backup</code>. '
            'Sirve como recuperación rápida (se accede desde SQL Editor de Supabase) sin '
            'depender de archivos locales. Cada snapshot se rota automáticamente: los que tengan '
            f'más de <b>{RETENCION_SEMANAS_BACKUP} semanas</b> se eliminan al crear uno nuevo. '
            'Uso recomendado: una vez por semana.'
            '</div>',
            unsafe_allow_html=True
        )

        if st.button('📦 Crear snapshot ahora', key='btn_crear_snapshot', type='primary'):
            with st.spinner('Creando snapshot y rotando los antiguos...'):
                try:
                    resultado = _crear_snapshot_supabase()
                    msg = (
                        f'✓ Snapshot creado: **{resultado["snapshot_id"]}** · '
                        f'{resultado["num_registros"]} registros respaldados.'
                    )
                    if resultado['num_borrados'] > 0:
                        msg += f' Se eliminaron {resultado["num_borrados"]} filas de snapshots antiguos.'
                    st.success(msg)
                    st.info('Recarga la pestaña para ver el panel de estado actualizado.')
                except Exception as e:
                    st.error(f'Error creando snapshot: {e}')

        st.markdown('<br>', unsafe_allow_html=True)
        st.markdown(
            '<div style="background:#F5F5F5;border-left:4px solid #999;'
            'padding:.7rem 1rem;border-radius:6px;font-size:.8rem;color:#555;">'
            '<b>Notas operativas:</b><br>'
            '• El respaldo Excel es tu red de seguridad principal (vive fuera de Supabase).<br>'
            '• Los snapshots en Supabase son recuperación rápida (12 semanas de historial).<br>'
            '• Para restaurar un snapshot: contactar al equipo técnico. La restauración se '
            'hace manual desde SQL Editor para evitar errores accidentales.<br>'
            '• Este módulo solo está disponible con rol UNODC.'
            '</div>',
            unsafe_allow_html=True
        )
