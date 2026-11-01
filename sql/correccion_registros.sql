-- sql/correccion_registros.sql
--
-- Corrección de registros TOP desde la app, con bitácora. Ver DECISIONES.md,
-- "Los registros se corrigen dentro de la app, con bitácora". Aplicado el
-- 2026-11-01 como migración `correccion_registros_con_bitacora`.
--
-- Tres piezas:
--   * top_correcciones: una fila por campo corregido desde la app, con el valor
--     anterior, el nuevo, el motivo y quién lo hizo (el país o UNODC).
--   * top_registros_auditoria: copia del registro antes y después de cualquier
--     modificación o borrado de top_registros, venga de donde venga, incluido el
--     SQL Editor. Es la red de seguridad: no depende de que alguien anote nada.
--   * corregir_registro(): aplica una corrección de una sola vez. Comprueba que el
--     registro sea del país que corrige, que haya motivo y que los campos existan
--     y se puedan corregir. Solo la puede llamar la llave secreta, que vive en el
--     servidor de la app; la llave pública no.

CREATE TABLE IF NOT EXISTS public.top_correcciones (
    id             bigserial PRIMARY KEY,
    registro_id    bigint      NOT NULL,
    pais           text        NOT NULL,
    campo          text        NOT NULL,
    valor_anterior text,
    valor_nuevo    text,
    motivo         text        NOT NULL,
    realizado_por  text        NOT NULL,
    fecha          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_top_correcciones_registro ON public.top_correcciones (registro_id);
ALTER TABLE public.top_correcciones ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.top_correcciones FROM anon, authenticated;

CREATE TABLE IF NOT EXISTS public.top_registros_auditoria (
    id          bigserial PRIMARY KEY,
    registro_id bigint,
    operacion   text        NOT NULL,
    antes       jsonb,
    despues     jsonb,
    usuario_db  text        NOT NULL DEFAULT current_user,
    fecha       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_top_auditoria_registro ON public.top_registros_auditoria (registro_id);
ALTER TABLE public.top_registros_auditoria ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.top_registros_auditoria FROM anon, authenticated;

CREATE OR REPLACE FUNCTION public._auditar_top_registros()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
    -- Quién: el rol de la llave que llegó por la API (service_role es la app), o
    -- el usuario de la sesión cuando el cambio viene del SQL Editor.
    v_quien text := coalesce(
        nullif(current_setting('request.jwt.claims', true), '')::jsonb->>'role',
        session_user);
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF to_jsonb(OLD) IS DISTINCT FROM to_jsonb(NEW) THEN
            INSERT INTO top_registros_auditoria (registro_id, operacion, antes, despues, usuario_db)
            VALUES (OLD.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), v_quien);
        END IF;
        RETURN NEW;
    END IF;
    INSERT INTO top_registros_auditoria (registro_id, operacion, antes, usuario_db)
    VALUES (OLD.id, 'DELETE', to_jsonb(OLD), v_quien);
    RETURN OLD;
END;
$function$;
REVOKE ALL ON FUNCTION public._auditar_top_registros() FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS trg_auditar_top_registros ON public.top_registros;
CREATE TRIGGER trg_auditar_top_registros
    AFTER UPDATE OR DELETE ON public.top_registros
    FOR EACH ROW EXECUTE FUNCTION public._auditar_top_registros();

CREATE OR REPLACE FUNCTION public.corregir_registro(
    p_id bigint, p_pais text, p_cambios jsonb, p_motivo text, p_realizado_por text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
    v_fila   jsonb;
    v_campo  text;
    v_valor  jsonb;
    v_tipo   text;
    v_sets   text[] := '{}';
    v_n      integer := 0;
BEGIN
    IF coalesce(btrim(p_motivo), '') = '' THEN
        RETURN jsonb_build_object('ok', false, 'error', 'motivo');
    END IF;
    IF p_cambios IS NULL OR jsonb_typeof(p_cambios) <> 'object' OR p_cambios = '{}'::jsonb THEN
        RETURN jsonb_build_object('ok', false, 'error', 'sin_cambios');
    END IF;

    SELECT to_jsonb(t) INTO v_fila FROM top_registros t WHERE t.id = p_id FOR UPDATE;
    IF v_fila IS NULL THEN
        RETURN jsonb_build_object('ok', false, 'error', 'no_existe');
    END IF;
    IF v_fila->>'pais' IS DISTINCT FROM p_pais THEN
        RETURN jsonb_build_object('ok', false, 'error', 'otro_pais');
    END IF;

    -- Primero se revisan todos los campos; si uno no sirve, no se toca nada.
    FOR v_campo, v_valor IN SELECT key, value FROM jsonb_each(p_cambios) LOOP
        IF v_campo IN ('id', 'created_at', 'pais') THEN
            RETURN jsonb_build_object('ok', false, 'error', 'campo', 'campo', v_campo);
        END IF;
        SELECT data_type INTO v_tipo
          FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'top_registros'
           AND column_name = v_campo;
        IF v_tipo IS NULL THEN
            RETURN jsonb_build_object('ok', false, 'error', 'campo', 'campo', v_campo);
        END IF;
        IF jsonb_typeof(v_valor) = 'null' THEN
            v_sets := v_sets || format('%I = NULL', v_campo);
        ELSE
            v_sets := v_sets || format('%I = (%L)::%s', v_campo, v_valor #>> '{}', v_tipo);
        END IF;
    END LOOP;

    -- Un solo UPDATE: una sola fila en la auditoría por corrección.
    EXECUTE format('UPDATE top_registros SET %s WHERE id = $1', array_to_string(v_sets, ', '))
      USING p_id;

    FOR v_campo, v_valor IN SELECT key, value FROM jsonb_each(p_cambios) LOOP
        INSERT INTO top_correcciones (registro_id, pais, campo, valor_anterior, valor_nuevo,
                                      motivo, realizado_por)
        VALUES (p_id, p_pais, v_campo, v_fila->>v_campo, v_valor #>> '{}',
                btrim(p_motivo), coalesce(nullif(btrim(p_realizado_por), ''), '(sin dato)'));
        v_n := v_n + 1;
    END LOOP;

    RETURN jsonb_build_object('ok', true, 'cambios', v_n);
END;
$function$;
REVOKE ALL ON FUNCTION public.corregir_registro(bigint, text, jsonb, text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.corregir_registro(bigint, text, jsonb, text, text) TO service_role;
