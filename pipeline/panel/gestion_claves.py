"""
pipeline.panel.gestion_claves — Pestaña "Claves de centros" del perfil de país.

Cada gobierno crea, restablece y desactiva las claves de acceso de sus centros,
con una clave de administrador propia que se verifica en Supabase. Las
operaciones viven en `sql/admin_claves_centros.sql`; acá solo se llaman y se
muestran. Ver DECISIONES.md, "Cada gobierno administra las claves de sus
centros".

La clave de administrador se guarda solo en la sesión de Streamlit y se pide de
nuevo al cerrar sesión. La clave nueva de un centro se muestra una sola vez.

Función expuesta: render(pais, llamar=None)
`llamar(nombre_funcion, payload) -> dict` permite probar sin Supabase.
"""
import json
import urllib.request

import pandas as pd
import streamlit as st

MENSAJES = {
    'clave':     'Clave de administrador incorrecta. Después de 5 intentos fallidos el acceso '
                 'se bloquea 15 minutos.',
    'centro':    'Falta el código del centro.',
    'correo':    'Para un centro que todavía no tiene clave, el correo institucional es obligatorio.',
    'otro_pais': 'Ese código de centro ya tiene clave en otro país o institución.',
    'sin_clave': 'Ese centro no tiene una clave activa.',
}

ESTADO = {
    (True, True):   'Activa',
    (True, False):  'Desactivada',
    (False, False): 'Sin clave',
}


def _llamar_supabase(nombre, payload):
    url = f"{st.secrets['SUPABASE_URL']}/rest/v1/rpc/{nombre}"
    headers = {
        'apikey':        st.secrets['SUPABASE_KEY'],
        'Authorization': f"Bearer {st.secrets['SUPABASE_KEY']}",
        'Content-Type':  'application/json',
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                 method='POST', headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def listar(pais, clave, llamar=None):
    return (llamar or _llamar_supabase)('admin_listar_centros',
                                        {'p_pais': pais, 'p_clave': clave})


def crear(pais, clave, centro, correo, responsable, llamar=None):
    return (llamar or _llamar_supabase)('admin_crear_clave_centro', {
        'p_pais': pais, 'p_clave': clave, 'p_centro': centro,
        'p_correo': correo, 'p_responsable': responsable,
    })


def desactivar(pais, clave, centro, llamar=None):
    return (llamar or _llamar_supabase)('admin_desactivar_clave_centro',
                                        {'p_pais': pais, 'p_clave': clave, 'p_centro': centro})


def mensaje_error(res):
    return MENSAJES.get((res or {}).get('error'), 'No se pudo completar la operación.')


def tabla_centros(centros):
    """Lista de centros que devuelve Supabase → tabla para mostrar."""
    filas = []
    for c in centros or []:
        filas.append({
            'Centro':            c.get('centro'),
            'TOP cargados':      c.get('registros', 0),
            'Último TOP':        c.get('ultimo_top') or '—',
            'Clave':             ESTADO.get((bool(c.get('tiene_clave')), bool(c.get('clave_activa'))), '—'),
            'Último ingreso':    (c.get('ultimo_ingreso') or '—')[:10],
            'Responsable':       c.get('responsable') or '—',
            'Correo':            c.get('correo') or '—',
        })
    return pd.DataFrame(filas, columns=['Centro', 'TOP cargados', 'Último TOP', 'Clave',
                                        'Último ingreso', 'Responsable', 'Correo'])


def render(pais, llamar=None):
    k = f'admin_{pais}'
    st.markdown(
        '<div style="background:#E3F2FD;border-left:4px solid #004AAD;padding:.7rem 1.2rem;'
        'border-radius:6px;margin-bottom:1rem;font-size:.85rem;">'
        '<b>🔑 Claves de acceso de los centros.</b> Desde aquí se crea, restablece o '
        'desactiva la clave con la que cada centro entra a ver sus propios datos. '
        'Se necesita la clave de administrador del país, distinta de la clave de esta sesión.'
        '</div>', unsafe_allow_html=True)

    clave = st.session_state.get(f'{k}_clave')
    if not clave:
        with st.form(f'{k}_entrar'):
            intento = st.text_input('Clave de administrador', type='password')
            if st.form_submit_button('Entrar'):
                try:
                    res = listar(pais, intento, llamar)
                except Exception as e:  # noqa: BLE001
                    st.error(f'No se pudo conectar con la base: {str(e)[:150]}')
                    return
                if res.get('ok'):
                    st.session_state[f'{k}_clave'] = intento
                    st.rerun()
                else:
                    st.error(mensaje_error(res))
        return

    try:
        res = listar(pais, clave, llamar)
    except Exception as e:  # noqa: BLE001
        st.error(f'No se pudo conectar con la base: {str(e)[:150]}')
        return
    if not res.get('ok'):
        st.session_state.pop(f'{k}_clave', None)
        st.error(mensaje_error(res))
        return

    df = tabla_centros(res.get('centros'))
    n_activas = int((df['Clave'] == 'Activa').sum())
    st.markdown(f'**{len(df)} centros** · {n_activas} con clave activa')
    st.dataframe(df, use_container_width=True, hide_index=True)

    # La clave recién creada se muestra una sola vez, hasta la próxima acción.
    nueva = st.session_state.pop(f'{k}_nueva', None)
    if nueva:
        st.success(f'Clave de {nueva["centro"]} '
                   f'{"creada" if nueva["accion"] == "clave_creada" else "restablecida"}. '
                   'Cópiela ahora: no se vuelve a mostrar.')
        st.code(nueva['clave'], language=None)
        st.caption('Entréguela al responsable del centro por un canal privado. El usuario es el '
                   'código del centro.')

    centros = df['Centro'].tolist()
    col1, col2 = st.columns(2, gap='large')

    with col1:
        st.markdown('**Crear o restablecer una clave**')
        with st.form(f'{k}_crear', clear_on_submit=True):
            sel = st.selectbox('Centro', ['(otro código)'] + centros)
            otro = st.text_input('Código del centro, si no está en la lista')
            correo = st.text_input('Correo institucional (obligatorio si el centro no tiene clave)')
            resp = st.text_input('Nombre del responsable')
            if st.form_submit_button('Generar clave'):
                centro = otro.strip() if sel == '(otro código)' else sel
                r = crear(pais, clave, centro, correo, resp, llamar)
                if r.get('ok'):
                    st.session_state[f'{k}_nueva'] = r
                    st.rerun()
                else:
                    st.error(mensaje_error(r))

    with col2:
        st.markdown('**Desactivar una clave**')
        activas = df.loc[df['Clave'] == 'Activa', 'Centro'].tolist()
        if not activas:
            st.caption('No hay claves activas.')
        else:
            with st.form(f'{k}_desactivar'):
                sel_d = st.selectbox('Centro', activas)
                seguro = st.checkbox('Confirmo que este centro deja de entrar')
                if st.form_submit_button('Desactivar'):
                    if not seguro:
                        st.warning('Marque la confirmación para desactivar.')
                    else:
                        r = desactivar(pais, clave, sel_d, llamar)
                        if r.get('ok'):
                            st.rerun()
                        else:
                            st.error(mensaje_error(r))

    if st.button('Salir de la administración de claves', key=f'{k}_salir'):
        st.session_state.pop(f'{k}_clave', None)
        st.rerun()
