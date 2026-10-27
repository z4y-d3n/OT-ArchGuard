# V14-04 — Historical Evidence & Drift Explorer

Fecha: 2026-10-27. Checkpoint de desarrollo; no es una versión estable v1.4.

## A. Resultado ejecutivo

Implementación local del Explorer histórico offline con reproducción obligatoria
de fuentes, navegación multipágina, trazabilidad y verificación del bundle.
La aceptación final se registra tras ejecutar las puertas locales; la aceptación
humana del propietario permanece **PENDING**.

## B. Arquitectura

`drift/explorer.py` coordina una adquisición lifecycle y replay V14-03;
`explorer_render.py` presenta los hallazgos canónicos;
`explorer_bundle.py` audita y publica el contrato de presentación versión 1.
Reutiliza escape/tablas/identidades del Explorer existente; mantiene separado
su significado histórico. No cambia el motor nativo ni el comparador.

## C. Seguridad y autoridad

La identidad recalculada de un JSON falso no concede autoridad: se exige replay
contra dependencias exactas. Se separan aprobación registrada, estado comprobado
al generar y estado actual obtenido con una verificación nueva. Las revisiones
siguen siendo afirmaciones locales no autenticadas. Publicación exclusiva,
manifest final, límites, escape, CSP sin scripts y auditoría de enlaces/fragmentos.

## D. Experiencia de usuario

Overview, comparabilidad por pareja/dimensión, comunicaciones, siete familias de
protocolos, arquitectura declarada, consultas nativas, interpretación, cobertura,
evidencia y aprobación. Índices por categoría/estado/resultado, paginación estática,
detalles lado a lado, fuentes exactas y navegación de retorno. SVG acotado para
relaciones pequeñas; tablas completas cuando el diagrama se omite.

## E. Visualización

Las salidas representativas y las observaciones reales se registran en los
recibos locales bajo `output/v144-*`. No se infiere aceptación humana a partir de
HTML válido o de una captura automatizada.

## F. Offline y portabilidad

Abrir `index.html` mediante archivo local. Sin servidor, JavaScript ni recursos
externos. Copiar el directorio completo. El bundle incluye HTML/CSS, metadata
drift exacta y recibo; no incluye PCAP ni adjuntos originales. La metadata y los
textos importados pueden contener información sensible: revisar antes de compartir.
`explore-verify` verifica integridad; `--workspace` añade reproducción analítica
y estado de aprobación actual sin reescribir la publicación.

## G. Determinismo

Origen V14-03: `6f3abb2084e40ae4a90d4d01200b7f79a617463c`.
La identidad de presentación incluye renderer, opciones y bytes exactos de reporte;
excluye paths de ejecución y reloj local. Las pruebas comparan publicaciones
completas repetidas y verifican lectura sin mutación.

## H. Rendimiento

Mediciones separadas de generación, replay, rendering, enlaces, memoria Python y
RSS se conservan como recibos JSON. Los tiempos con tracemalloc no se presentan
como latencia normal. Workloads finitos no prueban escala industrial universal.

## I. Pruebas

Los resultados ejecutados, conteos únicos, paquetes y hashes se consolidan en
esta sección al completar la verificación. No se atribuye PASS a una puerta sin
ejecución. El CI remoto del padre V14-03 pasó Windows/Ubuntu/macOS × 3.12/3.14;
no se ha despachado ni publicado CI V14-04.

## J. Aceptación visual

| Criterio del propietario | Estado |
|---|---|
| Comprensión inmediata de referencia/candidato/diferencias/incertidumbre | PENDING |
| Distinción histórica entre declaración, observación, evaluación e interpretación | PENDING |
| Navegación de hallazgo a evidencia/contexto y retorno | PENDING |
| Aprobación histórica/actual, cobertura y autoridad no autenticada | PENDING |
| Legibilidad estrecha/200%, teclado y foco visible | PENDING |
| Archivos locales sin red y navegación completa | PENDING |

Registrar commit candidato, hashes de paquetes y bundle, sistema operativo,
navegador/versión, fecha y revisor. Abrir normal, incomplete, decoder, revoked,
dense y unchanged; seguir Overview → dominio → hallazgo → fuente → contexto;
comparar límites y conteos, recorrer páginas, usar Tab/Shift+Tab/Enter, 200% y
ventana estrecha. Registrar fallos concretos y capturas antes de conceder PASS.

## K. Limitaciones

Aceptación humana, lector de pantalla y validación multiplataforma de V14-04 no
se fabrican. La publicación es de escritor local único, no protege frente a un
administrador hostil concurrente. Hashes no autentican origen ni identidad humana.
La copia estática no mantiene aprobación viva. Los límites fallan de forma explícita.

## L. Estado Git

Rama local `codex/v14-04-historical-explorer`, basada exactamente en el SHA V14-03
anterior (descendiente de V14-02P). Base recomendada del próximo Draft PR apilado:
`codex/v14-03-historical-drift-analysis`. No se hizo push, PR, merge, tag, release,
dispatch ni cambios de configuración remota. Commits y estado final se registran
en los recibos de entrega locales.

## M. Preparación de V14-05

Pendientes: corpus externo con permisos y referencias independientes, robustez de
interoperabilidad, escalado, casos negativos reales, validación cruzada de paquetes
y plataformas y estabilización previa al release. V14-05 no está implementado.
