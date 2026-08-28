"""
pipeline.sb_paginado — Descarga completa de consultas a Supabase (PostgREST).

Problema que resuelve: PostgREST devuelve como máximo 1000 filas por respuesta.
Una consulta que pide "todos los registros" sobre una tabla más grande recibe
solo las primeras 1000, sin error y sin aviso. El consumidor cree que tiene la
base completa y trabaja sobre un subconjunto.

Eso ya estaba ocurriendo en el módulo de respaldo: la tabla tenía unas 1400
filas y el Excel exportado traía 1000. Las consultas filtradas por país todavía
no llegaban al límite, pero lo iban a alcanzar sin producir ningún síntoma
visible.

Uso:
    from pipeline.sb_paginado import fetch_todo
    filas = fetch_todo(url, headers)

La URL debe incluir un `order` con desempate único (por ejemplo
`order=fecha_entrevista.asc,id.asc`). Sin un orden estable, dos páginas
consecutivas pueden repetir u omitir filas cuando hay valores empatados.
"""
import json
import urllib.request

PAGE_SIZE = 1000
MAX_PAGINAS = 200  # Guardarraíl: 200.000 filas. Evita un bucle infinito si el
                   # servidor devolviera siempre una página llena.


def fetch_todo(url, headers, page_size=PAGE_SIZE, timeout=30):
    """
    Descarga todas las filas de una consulta PostgREST, pidiéndolas por tandas.

    Args:
        url:       URL completa de la consulta, con su `select` y su `order`.
        headers:   dict de cabeceras (apikey, Authorization, etc.).
        page_size: filas por tanda. 1000 es el máximo que acepta Supabase.
        timeout:   segundos por petición.

    Returns:
        list de dicts con todas las filas.
    """
    filas = []
    for pagina in range(MAX_PAGINAS):
        desde = pagina * page_size
        hasta = desde + page_size - 1

        h = dict(headers)
        h['Range-Unit'] = 'items'
        h['Range'] = '%d-%d' % (desde, hasta)

        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            lote = json.loads(r.read().decode('utf-8'))

        filas.extend(lote)

        # Una página incompleta significa que ya no queda nada más.
        if len(lote) < page_size:
            return filas

    return filas
