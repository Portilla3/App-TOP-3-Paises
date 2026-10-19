-- Función de login de centro.
--
-- Vive en Supabase y se invoca por PostgREST desde app.py. Este archivo existe
-- porque hasta el 2026-10-18 las funciones de la base no estaban versionadas en
-- ningún lado: la única copia era la de producción. Un cambio hecho desde
-- cualquier sesión se perdía sin dejar rastro y sin forma de compararlo.
--
-- Si se modifica en Supabase, hay que actualizar este archivo en el mismo
-- commit. La prueba `tests/test_login_centro.py` verifica que la normalización
-- del código de centro siga acá.
--
-- Última aplicación: migración `login_centro_insensible_a_mayusculas`,
-- 2026-10-18. Ver DECISIONES.md, "El usuario del login de centro es el código".

CREATE OR REPLACE FUNCTION public.validar_login_centro(p_correo text, p_password text)
 RETURNS TABLE(valido boolean, centro text, pais text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'extensions'
AS $function$
DECLARE
    v_centro text;
    v_pais   text;
    v_entrada text;
BEGIN
    -- El código de centro no distingue mayúsculas ni espacios de borde. La
    -- clave sí: bcrypt compara exacto y eso no se toca.
    v_entrada := upper(trim(coalesce(p_correo, '')));

    SELECT cc.centro, cc.pais
      INTO v_centro, v_pais
      FROM centro_credenciales cc
     WHERE upper(trim(cc.centro)) = v_entrada
       AND cc.activo        = TRUE
       AND cc.password_hash = crypt(p_password, cc.password_hash)
     LIMIT 1;

    IF v_centro IS NOT NULL THEN
        BEGIN
            INSERT INTO centro_bitacora (centro, pais, accion, realizado_por)
            VALUES (v_centro, v_pais, 'login_exitoso', v_centro);
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;

        RETURN QUERY SELECT TRUE, v_centro, v_pais;
    ELSE
        -- En el fallido se guarda lo que la persona escribió, no un centro.
        -- Esa columna es la que permitió medir por qué fallan los intentos.
        BEGIN
            INSERT INTO centro_bitacora (centro, pais, accion, realizado_por)
            VALUES (
                left(coalesce(p_correo, '(vacio)'), 50),
                '(desconocido)',
                'login_fallido',
                'anon'
            );
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
    END IF;
END;
$function$;
