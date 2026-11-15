# QALAT · Texto de arranque de chat

Las reglas de trabajo viven en un solo lugar: `CLAUDE.md`, en la raíz del
repositorio. Claude Code lo lee solo al abrir el repo, y los chats del proyecto
"App 2.0 QALAT" lo leen desde GitHub porque las instrucciones del proyecto se lo
ordenan.

Este archivo tiene dos partes. La primera es el texto corto que va copiado en el
campo **Instrucciones personalizadas** del proyecto en Claude. La segunda
explica por qué las reglas dicen lo que dicen, para quien las tenga que
modificar más adelante.

Si cambias una regla, cámbiala en `CLAUDE.md`. El texto de la Parte 1 casi no
debería cambiar; si cambia, cambia también este archivo en el mismo commit.

---

## PARTE 1 · Texto para el campo de instrucciones del proyecto

QALAT es el sistema de monitoreo de resultados de tratamiento de drogas de
UNODC, con los instrumentos TOP e IRT. Rodrigo Portilla es el consultor a cargo
y el único desarrollador.

**Las reglas de trabajo están en un solo lugar: `CLAUDE.md` del repositorio
público `Portilla3/App-TOP-3-Paises`, rama `main`.** Al empezar cada chat, léelo
completo desde:

`https://raw.githubusercontent.com/Portilla3/App-TOP-3-Paises/main/CLAUDE.md`

y síguelo. Ahí están los documentos fuente de verdad (DECISIONES, CHANGELOG,
PENDIENTES, INCIDENTES), dónde se escribe cada cosa, la carpeta local, los dos
accesos, las reglas de trabajo numeradas y cómo responder.

Si no alcanzas el repositorio, usa la copia `claude/CLAUDE.md` del knowledge del
proyecto y dilo explícitamente en tu respuesta. Si este texto y `CLAUDE.md` se
contradicen, manda `CLAUDE.md`.

Responde siempre en español neutro, sin modismos argentinos, sin rayas largas,
como asesor y no como asistente, con etiquetas [Seguro], [Probable] o
[Suposición].

---

## PARTE 2 · Por qué dice lo que dice

**Por qué el texto va en el campo de instrucciones del proyecto y no en un
archivo que se pega al abrir cada chat.** Pegarlo depende de acordarse y de
pegarlo completo. El campo de instrucciones se inyecta solo, en todos los chats,
sin gastar un mensaje.

**Por qué la orden de leer es explícita.** Un documento en el knowledge del
proyecto no se lee solo: el chat ve la lista de nombres y decide si lo abre. Si
la pregunta es sobre sustancias y el archivo se llama "estado completo", puede
no mirarlo nunca. Sin una orden explícita, tener la memoria ordenada no sirve.

**Por qué el repositorio manda sobre el knowledge.** El repositorio se escribe
en el mismo commit que el código, así que no envejece. El knowledge se
actualiza a mano y por eso envejece. La copia existe solo porque hay chats que
no alcanzan `raw.githubusercontent.com`, y en ese caso una copia vieja es mejor
que nada, siempre que el chat sepa que puede estar vieja.

**Por qué "intenta primero el repositorio".** Sin esa frase, todos los chats
leerían siempre la copia del knowledge por comodidad, aunque puedan alcanzar la
buena.

**Por qué la regla 10.** El 8 de septiembre se verificó que las apps arrancaran
después de arreglar el despliegue. Al día siguiente Ecuador reportó que los
reportes no se generaban. Arrancar y funcionar no son lo mismo.

**Por qué la regla 4 menciona a Rodrigo.** El 2 de septiembre, dos de tres
diagnósticos escritos resultaron falsos al medirlos. El 9 de septiembre, dos
hipótesis sobre unos registros faltantes resultaron falsas y se corrigieron solo
porque Rodrigo pidió la evidencia.

**Por qué las reglas viven en `CLAUDE.md` y no en las instrucciones del
proyecto.** Desde el 14 de noviembre de 2026 Rodrigo también trabaja con Claude
Code en su computador, que no ve las instrucciones del proyecto de Claude pero
sí lee `CLAUDE.md` solo. Tener las reglas en dos lugares obligaba a mantenerlas
iguales a mano, y dos copias a mano terminan distintas. Con una sola copia en el
repositorio, el chat y Code siguen las mismas reglas y un cambio se hace una vez.

**Por qué las reglas 9 y 11 siguen en `CLAUDE.md` aunque Code no las use.**
Para que haya una sola lista. Van marcadas "solo chats en la nube" y conservan
su número porque otros documentos las citan así.
