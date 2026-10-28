# V14-04 — Corrección visual final de UX

Fecha: 2026-10-28. Rama `codex/v14-04-historical-explorer`.
Checkpoint revisado: `ccadcf1d5dd21d10a26d0a3734353c4023daaa41`.

El propietario informa que sus controles funcionales 1–7 pasan, salvo los
defectos visuales de native y Modbus. Esta corrección conserva ese alcance;
no constituye otro hito ni aceptación visual de las páginas corregidas.

## Defectos y corrección

1. `normal/native.html`: siete niveles de description lists repetían la grilla
   etiqueta/valor. Dentro de dos paneles y con wrap agresivo, cada nivel consumía
   más ancho. Ahora los grupos retenidos usan bloques verticales sin sangría
   horizontal acumulativa, incluidas listas. Los dos paneles se mantienen sólo
   cuando cada uno puede ocupar al menos 32 rem; en anchos intermedios se apilan.
2. `normal/protocol-modbus-tcp.html`: columnas automáticas dejaban que Meaning
   desplazara Finding y Comparability. Las tablas de hallazgos comparten columnas
   reservadas y un mínimo de 60 rem, dentro de su scroll rotulado y enfocable.
   Los códigos sólo pueden cortar visualmente entre componentes separados por
   underscore; el texto canónico sigue siendo exacto. Las tablas de comparabilidad
   de cinco columnas reciben el mismo tratamiento de overflow y estados.

Los identificadores técnicos pueden partirse; el texto corriente conserva cortes
por palabra. No se redujeron fuentes, omitieron campos ni ocultaron pruebas.
Print libera mínimos y usa proporciones de columnas aptas para papel.

| Patrón | Antes | Después |
|---|---|---|
| Evidencia anidada | Hasta siete grillas que reducían el ancho recursivamente | Bloques verticales sin consumo horizontal por nivel |
| Comparación a 1024/768 px | Dos paneles hasta 700 px | Un panel por fila si no caben dos de 32 rem |
| Tabla Modbus y equivalentes | Columnas automáticas, Meaning desplazaba las primeras | Finding 14 rem, categoría 16 rem, estado 13 rem; Meaning recibe el resto |
| Estados compuestos | Cortes arbitrarios por falta de ancho | Cortes entre componentes; texto DOM exacto |

## Preservación y alcance

Único módulo de producción cambiado: `drift/explorer_render.py`. Se agregan
regresiones de layout y se adapta una aserción antigua al texto DOM de los estados.
Engine, lifecycle, replay, publicación, auditor de bundles y fixtures congelados
permanecen sin cambios. Las salidas originales no se modifican; se regeneran
bundles en directorios nuevos y se registran nuevas identidades.

Se revisan los patrones compartidos en native, las siete familias de protocolos,
comunicaciones, arquitectura, cobertura, comparabilidad, fuentes, aprobación,
estados vacíos y paginación densa.

Se compararon **277 HTML de seis escenarios**, 149 registros canónicos y 265
referencias a fuentes: texto DOM completo, orden de hrefs y anclajes idénticos.
Los JSON drift y recibos de generación conservan exactamente sus bytes. Los seis
bundles anteriores permanecen intactos y pasan integridad portátil con el auditor
actual. El renderer exacto sigue vinculando la reproducción de la presentación;
los nuevos sitios, con sus nuevas identidades, pasan reproducción de fuentes.

Solo estos seis archivos fuente cambian:

- `src/otarchguard/drift/explorer_render.py`.
- `tests/test_historical_explorer_render.py`: compara texto DOM de estados.
- `tests/test_historical_explorer_layout.py`: 24 regresiones nuevas.
- Este informe y los inventarios `MANIFEST.in` / `tools/public-files.txt`.

Los otros **95 módulos de producción** conservan sus bytes respecto de
`ccadcf1d5dd21d10a26d0a3734353c4023daaa41`. No hay cambios en goldens.

## Verificación y límites visuales

Regresiones enfocadas iniciales: 106 PASS, 1 SKIP por creación de junction denegada.
24 casos nuevos modelan geometría y semántica de markup, evidencia profunda,
mensajes largos, estados, tablas y print. Un oráculo independiente rechaza
deliberadamente los patrones defectuosos originales.

El revisor independiente comprobó 74 HTML con evidencia profunda y texto hostil:
texto DOM, hrefs y anclajes exactamente conservados; sin defecto bloqueante.
Es una revisión estática, no una prueba visual de navegador.

Se calculan contratos CSS a 1440, 1024, 768, 390 y 375 px, y viewport CSS reducido
para zoom 200%. No se confunde ese cálculo con pintura, teclado o zoom reales.
Browser Use había bloqueado `file://`; no se elude mediante otro navegador,
proxy ni servidor. La revisión humana de ambas correcciones queda **PENDING**.

| Ancho de referencia | Columnas de comparación en el contrato CSS | Ancho interior por panel calculado |
|---|---:|---:|
| 1440 px | 2 | 617,8 px |
| 1024 px | 1 | 894,6 px |
| 768 px | 1 | 653,9 px |
| 390 px | 1 | 298 px |
| 375 px | 1 | 283 px |
| 1440 / 1024 / 768 a 200% | 1 | 608,8 / 412 / 292 px |

Son cálculos del contrato con rem de 16 CSS px, no mediciones del motor de un
navegador; no incluyen diferencias de font shaping o scrollbar. Ninguno concede
PASS visual. Las regiones de tabla conservan rol, rótulo y `tabindex=0`; foco y
print tienen pruebas estructurales, no una sesión real de teclado/impresión.

## Pruebas, paquetes y rendimiento

**4.018 tests únicos**, incluidos los 24 nuevos. Las repeticiones no aumentan el
inventario. Suites completas offline con source estabilizado:

| Entorno Windows real | Resultado | Tiempo pytest | Recibo bajo `output/v144-ux/` |
|---|---|---:|---|
| Source 3.14.5 | 4.017 PASS, 1 SKIP | 879,14 s | `source-suite.xml` |
| Wheel regular 3.14.5 | 4.017 PASS, 1 SKIP | 877,86 s | `wheel-suite.xml` |
| Sdist regular 3.14.5 | 4.017 PASS, 1 SKIP | 878,27 s | `sdist-suite.xml` |
| Wheel 3.12.14, drift/Explorer enfocados | 253 PASS, 1 SKIP | 178,65 s | `py312-focused.xml` |

El SKIP único es junction real denegado por el entorno; pasan su simulación y el
rechazo de symlink real. Ruff lint/formato y mypy estricto pasan, igual que
`pip check` en los cuatro entornos. Compatibilidad nativa: **124 archivos iguales**.
Consumers supported/limited, corpus sintético y ejemplos pasan. Pasan todos los
walkthroughs wheel evidence/history/drift/historical Explorer y sdist
project/Explorer/document/quality/capture/drift/historical Explorer. Se conservaron
los tests de replay, seguridad, fuentes congeladas y V14-02P.

Los paquetes se auditan por inventario exacto (462 archivos públicos, 96 módulos),
se instalan de forma regular y se comparan con el source. La actualización final
de este informe sólo cambia documentación: se reauditan archives e identidades,
se verifica que los módulos sean idénticos a los probados y se hace smoke CLI.
No se repiten las suites completas por esa edición documental.

Medición finita antes/después, mismo Python 3.14.5, tres ensayos sin instrumentación
y sin suites completas concurrentes; caché/scheduler del SO no controlados:

| Caso | Generación antes → después | Rendering antes → después | Bytes de contenido antes → después |
|---|---:|---:|---:|
| Normal | 0,913 → 1,009 s (+10,5%) | 0,061 → 0,065 s | 400.413 → 414.643 |
| Denso | 3,336 → 3,817 s (+14,4%) | 0,375 → 0,360 s | 2.246.524 → 2.365.232 |

Se declara el aumento de generación y markup; no se atribuye una mejora universal.
La medición incluye replay y publicación completos. No se ampliaron límites ni
se retiraron auditorías para ocultar ese costo. Los datos no prueban escala
industrial máxima. Recibos: `performance-before/performance.json` y
`performance-after/performance.json`.

## Identidades y estado Git

Reporte normal inalterado:
`drift-98d4db74cd42e65fb321317e73e92fa88f194cd6bcfa70eb94bef043040de95d`.
Bundle normal nuevo:
`historical-explorer-bb239aaea16965199a0987b4b7cc6f476a9e54865692e90a0f92dcd7baf1fc84`.
Bundle denso nuevo:
`historical-explorer-4cbf531f68f4439ee9346428094c74250f0e6f5fb3329fd6c1502741929c82be`.
Las seis identidades coinciden entre source, wheel y sdist; la repetición en
destinos nuevos produce iguales archivos y manifests.

Recibos exactos bajo `output/v144-ux/`: `preservation-layout.json`,
`cross-package-bundles.json`, `production-scope.json`, auditorías e identidades
finales de paquetes. El SHA de commit probado/final y el estado limpio se fijan
después del commit local en `final-git.json`; sus módulos deben coincidir con los
96 hashes de los paquetes ejecutados por las suites. No se cambia de rama.

## Revisión exacta del propietario

Abrir directamente los archivos regenerados; comprobar etiquetas, hashes,
testigos y diagnósticos completos, comparación apilada a 1024/768 px, scroll
de tabla mediante teclado, 375–390 px, 200% y print. No conceder PASS a los dos
defectos originales hasta inspeccionar estas nuevas páginas.

Comparación anterior, conservada sin cambios:
`output/v144-walk-wheel/historical_explorer_walkthrough/normal/`.

Archivos definitivos regenerados del wheel, relativos al repositorio:

- Native: `output/v144-ux/wheel-walk/historical_explorer_walkthrough/normal/native.html`.
- Modbus: `output/v144-ux/wheel-walk/historical_explorer_walkthrough/normal/protocol-modbus-tcp.html`.
- Equivalente: `output/v144-ux/wheel-walk/historical_explorer_walkthrough/incomplete/native.html`.
- Denso/estrecho: `output/v144-ux/wheel-walk/historical_explorer_walkthrough/dense/communications-2.html`.

Registrar navegador/versión, ancho CSS, zoom, identidad del bundle y resultado
concreto de cada página. Verificar que no haya texto vertical de un carácter,
solapamiento, clipping ni scroll horizontal del documento; el scroll propio de
la tabla es intencional. Las dos correcciones y pintura/teclado/zoom/print reales
quedan **PENDING de inspección del propietario**. No se inventan screenshots.

No se hizo push, PR, merge, tag, release, dispatch ni ningún cambio remoto.
