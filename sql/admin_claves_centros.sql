-- Gestión de las claves de centro por cada gobierno.
--
-- Cada país (o institución, en México) tiene una clave de administrador propia,
-- guardada cifrada con bcrypt en `pais_admin`. Con ella, desde la pestaña
-- "Claves de centros" de la app, el gobierno crea, restablece o desactiva las
-- claves de sus centros. Ver DECISIONES.md, "Cada gobierno administra las claves
-- de sus centros".
--
-- Seguridad:
--   * `pais_admin` tiene RLS activo y ningún permiso para anon ni authenticated.
--     Solo se lee desde estas funciones, que corren como su dueño.
--   * Las tres funciones públicas exigen la clave de administrador del país en
--     cada llamada. La llave pública de los formularios sola no alcanza.
--   * Con 5 intentos fallidos en 15 minutos para un país, la verificación se
--     niega sin mirar la clave. Los fallidos quedan en `centro_bitacora`.
--   * Las funciones no levantan excepción ante una clave incorrecta: devuelven
--     {"ok": false}. Una excepción desharía el registro del intento fallido y el
--     bloqueo nunca se activaría.
--   * La clave nueva de un centro se genera acá, se devuelve una sola vez y solo
--     se guarda su hash. No pasa por la bitácora.
--
-- Aplicado en Supabase el 2026-10-27, migración `admin_claves_centros`.
-- Si se modifica en Supabase, hay que actualizar este archivo en el mismo commit.
-- La prueba `tests/test_gestion_claves.py` revisa estas reglas.

CREATE TABLE IF NOT EXISTS public.pais_admin (
    pais            text PRIMARY KEY,
    clave_hash      text NOT NULL,
    activo          boolean NOT NULL DEFAULT true,
    creado_at       timestamptz NOT NULL DEFAULT now(),
    ultima_rotacion timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.pais_admin ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.pais_admin FROM anon, authenticated;
-- Protección declarada, no por ausencia (DECISIONES.md, Seguridad).
DROP POLICY IF EXISTS deny_all_pais_admin ON public.pais_admin;
CREATE POLICY deny_all_pais_admin ON public.pais_admin AS RESTRICTIVE
    FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);

-- Un código de centro tiene una sola clave, aunque se escriba con otras
-- mayúsculas o espacios. Antes nada impedía tener 'csp' y 'CSP'.
CREATE UNIQUE INDEX IF NOT EXISTS centro_credenciales_centro_normalizado
    ON public.centro_credenciales (upper(trim(centro)));


-- ── Internas: no se exponen ─────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public._admin_pais_valido(p_pais text, p_clave text)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'extensions'
AS $function$
DECLARE
    v_fallos integer;
    v_ok     boolean;
BEGIN
    SELECT count(*) INTO v_fallos
      FROM centro_bitacora
     WHERE pais = coalesce(p_pais, '')
       AND accion = 'admin_fallido'
       AND fecha > now() - interval '15 minutes';
    IF v_fallos >= 5 THEN
        RETURN FALSE;
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM pais_admin pa
         WHERE pa.pais = p_pais
           AND pa.activo
           AND pa.clave_hash = crypt(coalesce(p_clave, ''), pa.clave_hash)
    ) INTO v_ok;

    IF NOT v_ok THEN
        INSERT INTO centro_bitacora (centro, pais, accion, realizado_por)
        VALUES ('(administración)', left(coalesce(p_pais, '(vacío)'), 50), 'admin_fallido', 'anon');
    END IF;
    RETURN v_ok;
END;
$function$;

CREATE OR REPLACE FUNCTION public._clave_aleatoria(p_largo integer DEFAULT 10)
 RETURNS text
 LANGUAGE plpgsql
 SET search_path TO 'public', 'extensions'
AS $function$
DECLARE
    -- Sin 0/O, 1/l/I: se dictan por teléfono sin confundirse.
    v_alfabeto text := 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789';
    v_bytes    bytea := gen_random_bytes(p_largo);
    v_clave    text := '';
BEGIN
    FOR i IN 0 .. p_largo - 1 LOOP
        v_clave := v_clave || substr(v_alfabeto, (get_byte(v_bytes, i) % length(v_alfabeto)) + 1, 1);
    END LOOP;
    RETURN v_clave;
END;
$function$;

REVOKE ALL ON FUNCTION public._admin_pais_valido(text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public._clave_aleatoria(integer) FROM PUBLIC, anon, authenticated;


-- ── Públicas: las llama la app ──────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.admin_listar_centros(p_pais text, p_clave text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'extensions'
AS $function$
BEGIN
    IF NOT _admin_pais_valido(p_pais, p_clave) THEN
        RETURN jsonb_build_object('ok', false, 'error', 'clave');
    END IF;

    RETURN jsonb_build_object('ok', true, 'centros', coalesce((
        SELECT jsonb_agg(to_jsonb(x) ORDER BY x.centro)
          FROM (
            WITH datos AS (
                SELECT upper(trim(centro)) AS c, min(trim(centro)) AS centro,
                       count(*) AS registros, max(fecha_entrevista) AS ultimo_top
                  FROM top_registros
                 WHERE pais = p_pais AND coalesce(trim(centro), '') <> ''
                 GROUP BY 1
            ), cred AS (
                SELECT upper(trim(centro)) AS c, trim(centro) AS centro, activo,
                       correo_institucional, responsable_nombre
                  FROM centro_credenciales
                 WHERE pais = p_pais
            ), ingresos AS (
                SELECT upper(trim(centro)) AS c, max(fecha) AS ultimo_ingreso
                  FROM centro_bitacora
                 WHERE accion = 'login_exitoso'
                 GROUP BY 1
            )
            SELECT coalesce(d.centro, cr.centro)      AS centro,
                   coalesce(d.registros, 0)           AS registros,
                   d.ultimo_top,
                   (cr.c IS NOT NULL)                 AS tiene_clave,
                   coalesce(cr.activo, false)         AS clave_activa,
                   cr.correo_institucional            AS correo,
                   cr.responsable_nombre              AS responsable,
                   i.ultimo_ingreso
              FROM datos d
              FULL JOIN cred cr ON cr.c = d.c
              LEFT JOIN ingresos i ON i.c = coalesce(d.c, cr.c)
          ) x
    ), '[]'::jsonb));
END;
$function$;

CREATE OR REPLACE FUNCTION public.admin_crear_clave_centro(
    p_pais text, p_clave text, p_centro text, p_correo text, p_responsable text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'extensions'
AS $function$
DECLARE
    v_centro text := upper(trim(coalesce(p_centro, '')));
    v_correo text := nullif(trim(coalesce(p_correo, '')), '');
    v_resp   text := nullif(trim(coalesce(p_responsable, '')), '');
    v_nueva  text;
    v_accion text;
BEGIN
    IF NOT _admin_pais_valido(p_pais, p_clave) THEN
        RETURN jsonb_build_object('ok', false, 'error', 'clave');
    END IF;
    IF v_centro = '' THEN
        RETURN jsonb_build_object('ok', false, 'error', 'centro');
    END IF;
    IF EXISTS (SELECT 1 FROM centro_credenciales
                WHERE upper(trim(centro)) = v_centro AND pais <> p_pais) THEN
        RETURN jsonb_build_object('ok', false, 'error', 'otro_pais');
    END IF;

    v_nueva := _clave_aleatoria(10);

    IF EXISTS (SELECT 1 FROM centro_credenciales
                WHERE upper(trim(centro)) = v_centro AND pais = p_pais) THEN
        UPDATE centro_credenciales
           SET password_hash        = crypt(v_nueva, gen_salt('bf')),
               activo               = TRUE,
               ultima_rotacion      = now(),
               correo_institucional = coalesce(v_correo, correo_institucional),
               responsable_nombre   = coalesce(v_resp, responsable_nombre)
         WHERE upper(trim(centro)) = v_centro AND pais = p_pais;
        v_accion := 'clave_restablecida';
    ELSE
        IF v_correo IS NULL THEN
            RETURN jsonb_build_object('ok', false, 'error', 'correo');
        END IF;
        -- El código se guarda como lo escribe el formulario TOP, si el centro ya cargó.
        INSERT INTO centro_credenciales (centro, pais, correo_institucional, password_hash,
                                         responsable_nombre, activo)
        VALUES (coalesce((SELECT min(trim(centro)) FROM top_registros
                           WHERE pais = p_pais AND upper(trim(centro)) = v_centro), v_centro),
                p_pais, v_correo, crypt(v_nueva, gen_salt('bf')), v_resp, TRUE);
        v_accion := 'clave_creada';
    END IF;

    INSERT INTO centro_bitacora (centro, pais, accion, realizado_por)
    VALUES (v_centro, p_pais, v_accion, 'gobierno:' || p_pais);

    RETURN jsonb_build_object('ok', true, 'accion', v_accion, 'centro', v_centro, 'clave', v_nueva);
END;
$function$;

CREATE OR REPLACE FUNCTION public.admin_desactivar_clave_centro(
    p_pais text, p_clave text, p_centro text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'extensions'
AS $function$
DECLARE
    v_centro text := upper(trim(coalesce(p_centro, '')));
BEGIN
    IF NOT _admin_pais_valido(p_pais, p_clave) THEN
        RETURN jsonb_build_object('ok', false, 'error', 'clave');
    END IF;

    UPDATE centro_credenciales
       SET activo = FALSE
     WHERE upper(trim(centro)) = v_centro AND pais = p_pais AND activo;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('ok', false, 'error', 'sin_clave');
    END IF;

    INSERT INTO centro_bitacora (centro, pais, accion, realizado_por)
    VALUES (v_centro, p_pais, 'clave_desactivada', 'gobierno:' || p_pais);

    RETURN jsonb_build_object('ok', true, 'accion', 'clave_desactivada', 'centro', v_centro);
END;
$function$;

REVOKE ALL ON FUNCTION public.admin_listar_centros(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.admin_crear_clave_centro(text, text, text, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.admin_desactivar_clave_centro(text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_listar_centros(text, text) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_crear_clave_centro(text, text, text, text, text) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_desactivar_clave_centro(text, text, text) TO anon, authenticated;


-- ── Clave de administrador de cada país ─────────────────────────────────────
-- No va en este archivo: la elige Rodrigo y la pega en el SQL Editor, una vez
-- por país, con la clave entre las comillas:
--
--   INSERT INTO pais_admin (pais, clave_hash)
--   VALUES ('Perú', extensions.crypt('CLAVE_ELEGIDA', extensions.gen_salt('bf', 10)))
--   ON CONFLICT (pais) DO UPDATE
--      SET clave_hash = excluded.clave_hash, activo = TRUE, ultima_rotacion = now();
--
-- El nombre del país tiene que ser exactamente el de la columna `pais`:
-- 'Perú', 'Ecuador', 'El Salvador', 'México' (IMSS-Bienestar), 'México CIJ'.
-- Monte Fénix y Mahanaim no llevan administrador: cada una es un solo centro y
-- su perfil de institución ya es el del centro. Sin fila en `pais_admin`, nadie
-- puede administrar claves a su nombre.
