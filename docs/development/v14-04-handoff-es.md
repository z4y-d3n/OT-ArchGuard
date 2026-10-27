# V14-04 — Historical Evidence & Drift Explorer

Fecha: 2026-10-27. Checkpoint de desarrollo; no es una versión estable v1.4.

## A. Resultado ejecutivo

**READY_FOR_OWNER_REVIEW**. Implementado el Explorer histórico offline con
reproducción obligatoria de fuentes, navegación multipágina, trazabilidad,
publicación segura y verificación del bundle. Las tres suites completas pasan;
la aceptación global V14-04 permanece pendiente de revisión visual humana y CI
del nuevo checkpoint. No se declara una versión estable ni aceptación humana.

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

Salida real para revisión: abrir directamente
`output/v144-walk-wheel/historical_explorer_walkthrough/normal/index.html`.
Las variantes `incomplete`, `decoder`, `revoked`, `dense` y `unchanged` están al
lado. El sitio normal tiene 39 páginas HTML, 553 enlaces locales y 400.416 bytes
de contenido; usa 10 registros por página. No hay enlaces/fragmentos rotos.

La política de Browser Use rechazó `file://`: sólo admite HTTP/HTTPS. No se
intentó otro navegador, proxy ni servidor para eludirla. Se rasterizó el SVG real
con el CSS publicado: `output/v144-visual/final-communications.png`. Es una imagen
del diagrama, **no una captura de navegador ni prueba de navegación o zoom**.
La tipografía del raster depende de su motor de fuentes y no certifica la del
navegador. El raster estrecho inicial reveló etiquetas demasiado pequeñas;
se corrigió con un dibujo de ancho mínimo 900 px dentro de una región de scroll
rotulada y enfocada por teclado. Regresión estructural y auditoría pasan;
el comportamiento visual real queda para el propietario.

Recibo de límites visuales: `output/v144-visual/receipt.json`. El auditor final
independiente comprobó seis escenarios, 149 hallazgos y 265 joins exactos de
análisis a fuentes, sin defecto semántico bloqueante. No usó un navegador.

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

Reporte normal:
`drift-98d4db74cd42e65fb321317e73e92fa88f194cd6bcfa70eb94bef043040de95d`.
Bundle normal:
`historical-explorer-2f4f853253c9f3401c3d7adbf5a17a7acc8be5aabbe717e2f1094734067512a7`.
Las generaciones repetidas en destinos distintos tienen bytes/manifests iguales.
Wheel y sdist producen la misma identidad. Python 3.12 reproduce el sitio creado
con 3.14 y resuelve correctamente su aprobación actual REVOKED, sin reescribirlo.

## H. Rendimiento

Tres ensayos normales sin instrumentación, después de warmup y sin las suites
completas concurrentes. La preparación no entra en la latencia. Allocations se
miden en otro proceso/ensayo; sus publicaciones tienen las mismas identidades.

| Escala ficticia | Hallazgos | HTML | Generación mediana | Replay | Rendering | Auditoría enlaces | Bytes publicados |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 14 | 37 | 0,807 s | 0,141 s | 0,056 s | 0,074 s | 400.844 |
| 64 | 77 | 44 | 2,434 s | 0,622 s | 0,283 s | 0,326 s | 1.738.671 |
| 512 | 525 | 107 | 13,775 s | 4,077 s | 1,845 s | 2,097 s | 11.332.558 |

Mayor HTML del caso denso: 629.154 bytes, por debajo de 2 MiB. Pico Python
separado: 36.659.083 / 40.684.720 / 81.332.346 bytes. RSS máximo de esos procesos:
79.663.104 / 95.203.328 / 180.031.488 bytes; incluye overhead de tracemalloc y
es un high-water del proceso, no memoria exclusiva del renderer. Los tiempos con
tracemalloc no se presentan como latencia normal. El caso 512 llega al límite del
productor ficticio; no demuestra escala industrial ni todos los límites del motor.

Comparación con el V14-03 instalado exacto, mismo Python 3.14.5, cinco ensayos por
operación y outputs canónicos idénticos en las siete operaciones:

| Operación | V14-03 mediana | V14-04 mediana | Variación |
|---|---:|---:|---:|
| Verificar workspace | 96,276 ms | 107,758 ms | +11,9% |
| Inspeccionar revisiones | 98,415 ms | 106,792 ms | +8,5% |
| Comparar drift | 116,052 ms | 100,010 ms | −13,8% |
| Reproducir reporte | 136,114 ms | 146,845 ms | +7,9% |
| Comparación nativa | 30,193 ms | 28,194 ms | −6,6% |
| Observaciones capture | 3,542 ms | 2,914 ms | −17,7% |
| Enrichment protocolos | 3,226 ms | 2,848 ms | −11,7% |

Arranque de consola en proceso fresco, cinco pares alternados: 619,8 → 625,0 ms,
+0,8%. Cachés del SO y scheduler no se controlan; las pequeñas regresiones se
declaran, sin atribuir mejoras universales. Los módulos analíticos no cambiaron.
Pruebas V14-02P de adquisición, invalidación, mutación y reuso pasan en las suites.
Recibos exactos: `output/v144-final-timing/timing.json`,
`output/v144-final-memory/memory.json`, `output/v144-final-regression-summary.json`.
Las primeras mediciones exploratorias `output/v144-benchmark/` no sustituyen estos
recibos del source estabilizado. Ninguna medición omite replay para ganar velocidad.

## I. Pruebas

Hay **3.994 tests únicos**: 3.901 conservados y 93 nuevos. Repetir una suite no
aumenta ese inventario. Resultados del commit de implementación probado:

| Entorno Windows real | Resultado | Tiempo pytest | Recibo local |
|---|---|---:|---|
| Source, Python 3.14.5 | 3.993 PASS, 1 SKIP | 901,21 s | `output/v144-source-suite.xml` |
| Wheel regular, Python 3.14.5 | 3.993 PASS, 1 SKIP | 903,38 s | `output/v144-wheel-suite.xml` |
| Sdist regular, Python 3.14.5 | 3.993 PASS, 1 SKIP | 902,55 s | `output/v144-sdist-suite.xml` |
| Wheel regular, Python 3.12.14, Explorer + drift enfocados | 229 PASS, 1 SKIP | 176,94 s | `output/v144-py312-focused.xml` |

Las tres suites completas corrieron en paralelo: sus tiempos no comparan
rendimiento. El único SKIP es creación real de junction denegada por el entorno;
rechazo de junction simulado y de symlink real pasan. Explorer enfocado:
92 PASS y ese mismo SKIP. No hay fallos ni errores.

Ruff lint/formato: PASS, 362 archivos. Mypy estricto: PASS, 244 archivos.
`pip check`: PASS en los cuatro entornos. Las suites completas incluyen contratos
nativos/congelados, drift anterior y pruebas V14-02P de mutación/reuso/rendimiento.
Compatibilidad nativa independiente: **124 archivos capturados iguales**.
Consumers congelados supported/limited, corpus sintético y ejemplos pasan.
Walkthroughs wheel: evidence/history/drift/historical Explorer. Sdist:
project/Explorer/document/quality/capture/drift/historical Explorer. Todos pasan
offline con operaciones de red Python denegadas. Ninguna suite antigua se redujo
ni se modificaron golden files.

Inventario de source: 460 archivos públicos y 96 módulos de producción. Wheel y
sdist regulares coinciden byte a byte con los módulos revisados. Se verificaron
inventarios source y archives; hashes exactos y auditorías finales se conservan
en `output/v144-final-package-identities.json`, `output/v144-final-archive-audit.json`
y `output/v144-final-source-checkout.json`. La consolidación posterior sólo cambia
documentación: la identidad de los 96 módulos probados se conserva y se revalida.

El CI remoto del padre V14-03 pasó las seis configuraciones Windows/Ubuntu/macOS
× 3.12/3.14 contra su SHA exacto. El workflow conserva esas seis configuraciones
y añade ambos walkthroughs históricos. No se despachó ni publicó CI V14-04.

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

Bloquea la aceptación global del hito: revisión humana de los seis criterios,
browser real a ancho estrecho/200% y CI hospedado del nuevo checkpoint siguen
PENDING. La restricción de acceso a archivos locales está registrada, sin bypass.
Lector de pantalla no probado; no hay certificación formal de accesibilidad.

No bloquea la revisión local de desarrollo: la medición densa llega al límite
512 del productor ficticio, no a todos los máximos del motor. Los techos de
20.000 hallazgos/32 MiB de reporte/256 MiB de bundle no constituyen una promesa
de que cualquier combinación quepa; los excesos fallan cerrados, sin ocultar
hallazgos. Escalado máximo y corpus industrial real quedan para endurecimiento.

La publicación es de escritor local único, no protege frente a un administrador
hostil concurrente. Hashes no autentican origen ni identidad humana. El recibo
histórico tampoco está autenticado: una reproducción nueva informa autoridad
actual por separado. La copia estática no mantiene aprobación viva. `report.json`
conserva texto importado sensible incluso cuando HTML oculta strings tipo path.

## L. Estado Git

Rama local `codex/v14-04-historical-explorer`, basada exactamente en el SHA V14-03
anterior (descendiente de V14-02P). Commit de implementación y de las suites
completas: `a6ac5ef99396c894352801b227e6d655a5a26526`. Módulos cambiados:
los tres nuevos `drift/explorer*.py`, integración mínima en `evidence/cli.py`,
tests/harness, walkthroughs, docs e inventarios. Los otros 92 módulos del padre
permanecen iguales. El baseline instalado usado en regresión coincide con sus
93 módulos exactos de V14-03 (`output/v144-baseline-identity.json`).

Commit documental final y estado limpio se registran tras consolidar en
`output/v144-final-git.json`; las suites completas corresponden al commit de
implementación y el paquete final conserva exactamente sus módulos probados.
Base recomendada del próximo Draft PR apilado:
`codex/v14-03-historical-drift-analysis`. No se hizo push, PR, merge, tag, release,
dispatch ni cambios de configuración remota. El propietario conserva la decisión
de revisar, autorizar push y abrir el Draft PR apilado.

## M. Preparación de V14-05

Pendientes: corpus externo con permisos y referencias independientes, robustez de
interoperabilidad, escalado, casos negativos reales, validación cruzada de paquetes
y plataformas y estabilización previa al release. V14-05 no está implementado.
