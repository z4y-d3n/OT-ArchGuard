# V15-04 — Entrega al propietario

Resultados locales cerrados contra recibos reales. Todas las rutas de evidencia
son relativas al checkout; los datos grandes permanecen ignorados bajo `output/v15-04/`.
La matriz hosted y la autorización del propietario permanecen pendientes.

## 1. Veredicto ejecutivo

**READY_FOR_OWNER_REVIEW**. La optimización T1
supera el criterio de latencia local predefinido de 3%: 6.1435% en la campaña
balanceada y 6.1052% en una confirmación posterior con orden invertido. No se
alcanzó el objetivo aspiracional de 15%; se seleccionó de antemano un cambio
excepcionalmente pequeño, con un umbral menor explícito, sin omitir verificaciones.

La revisión independiente de bytes encontró cero diferencias en 76 sitios
generados. La implementación, suites completas, compatibilidad, paquetes y auditorías locales
han pasado; el cierre documental y sus archivos se identifican en el recibo final externo. Este trabajo es un hito de desarrollo, no una versión
estable, certificación industrial ni garantía de capacidad universal.

## 2. Identidades Git de partida y cierre

| Identidad | Valor comprobado |
|---|---|
| Merge V15-03 inicial | `18cb7e84ef16871daf857af48e3cd003ec8200ba` |
| Árbol inicial | `0b512bce31da2b0d9b10160b1a8cdc13ec23fab4` |
| Primer experimento de implementación | `8657b7a9242ec5964e3e255ebe88df704bb188eb` |
| Árbol del primer experimento | `2d2157d04b05d7cb475ee2c988779b0356c48888` |
| Implementación corregida y verificada | `3410924d80a2373bdbe75385c07a84a51441b878` |
| Árbol de implementación corregida | `b48ca8cc911195a6188681c8b86223712903d754` |
| Rama local | `codex/v15-04-performance-scalability` |
| SHA/árbol de cierre documental | `output/v15-04/final/freeze.json`: SHA y árbol del HEAD entregado |
| Estado final limpio de la rama | Limpio; estado y comando retenidos en `final/freeze.json` |

La partida estaba limpia y coincidía con `origin/main` después de un fetch de
lectura. `8657b7a` es el experimento anterior: el primer verificador integral falló
por una lista vacía de excepciones del comparador nativo y fue corregido en `3410924`. Los
97 módulos de runtime permanecieron idénticos entre ambos commits, por lo que la
campaña de rendimiento sigue midiendo exactamente el runtime de la implementación
corregida. La corrección afectó a la verificación y sus regresiones.

Separar expresamente la implementación probada `3410924` del eventual commit que
solo cierre documentación. Registrar SHA/árbol finales y auditoría de paquetes
finales sin introducir un hash propio circular en el mismo documento. Cualquier
nuevo cambio de runtime requiere repetir las comprobaciones afectadas.

## 3. Dependencia del gate anterior

V15-03 está fusionado mediante PR #28. Su ejecución posterior al merge,
[41841310683](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/41841310683),
terminó con éxito en los seis trabajos Windows/Ubuntu/macOS × Python 3.12/3.14.
El recibo está en `output/v15-04/baseline/ci.json`.

La instalación regular `.venv-v153-final` dev2 pasó el verificador V15-03 sin
modificar, antes de investigar: 97 módulos instalados, motor nativo 1.3.0. La
política histórica verifica su propio productor; no autoriza automáticamente
el nuevo dev3.

## 4. Baseline de rendimiento

Entorno medido: Windows 11 build 26100 AMD64, CPython 3.12.14, dependencias
idénticas salvo la distribución OT-ArchGuard. Se reutilizó el mismo árbol de
entradas ficticias de `tools.synthetic_explorer.explorer_workload`, con hashes
del constructor, driver, entradas y 97 módulos. Los perfiles anteriores de
V15-01 solo sirvieron para priorizar, no como denominador de esta comparación.

| Carga | Parámetros assets/interfaces/connectors/sources | Mediana dev2 de 6 muestras / MAD, s |
|---|---|---|
| small | 20 / 30 / 40 / 3 | 1.174949 / 0.020441 |
| medium | 150 / 200 / 250 / 5 | 9.978064 / 0.444023 |
| larger | 500 / 600 / 750 / 6 | 33.318590 / 0.160888 |
| adversarial | 150 / 200 / 250 / 5; hostile=True | 10.665843 / 0.562494 |

Medición normal con `perf_counter`, fixtures y hashes fuera del intervalo,
un calentamiento excluido por bloque/caso. Orden B3→A3→A3→B3: seis muestras
por runtime/caso. cProfile, tracemalloc y RSS usan ejecuciones separadas.

## 5. Cuellos de botella medidos

El perfil CPU larger atribuyó 90.261 s instrumentados a la generación completa.
La auditoría del sitio costó 45.172 s, incluyendo lecturas reales y HTMLParser;
la carga de provenance, 22.578 s. Son costes anidados: no sumarlos como fases
independientes. La serialización, agrupación y reescritura también se midieron.

`check_text` recibió 585,785 llamadas; su generador acumuló 10,377,420 llamadas
y el conjunto 7.543 s instrumentados. Esto demuestra trabajo repetido por
carácter, pero no predice la mejora normal: cProfile aumenta especialmente el
coste relativo de generadores. `_compact` no fue el cuello dominante y no hay
evidencia de complejidad cuadrática. Conservar la auditoría de bytes emitidos y
las validaciones de provenance tiene una función de integridad necesaria.

## 6. Optimización seleccionada

T1 sustituye el predicado Python por carácter de `explorer_data.check_text` por
una búsqueda con una clase de caracteres regex fija y compilada. Mantiene primero
el límite de 4,096 caracteres y conserva código, ubicación, mensaje y precedencia
de rechazo. Rechaza los mismos C0 salvo TAB/LF/CR, C1 y sustitutos Unicode.

No hay caché de evidencia, memoización entre invocaciones, dependencia nueva,
cambio de orden, límite elevado, resultado muestreado, fuente omitida ni
verificación saltada. El oráculo independiente es la función del merge V15-03
inmutable y sus sitios antes del cambio; los outputs nuevos no se autorizan solos.

## 7. Módulos de producción modificados

Exactamente dos de los 97 módulos de runtime cambian; los otros 95 deben coincidir
con el archivo Git inmutable:

| Módulo | Cambio | SHA-256 autorizado de candidato |
|---|---|---|
| `__init__.py` | Identidad de distribución dev3 | `7ccf2c03974ffdadc0fc1f6d1a2af50c88cb53b937002bf616399adc9ecdffdc` |
| `explorer_data.py` | T1: búsqueda equivalente de texto inválido | `d501ecb1a00488a081c39b6fa3e4560d9e9565b7f8a3c8562797ca2e9abeb715` |

Inventario completo de cambios rastreados de tests, herramientas, CI, manifiestos
y documentación: `final/changed-files.txt`, `final/source-checkout.json` y `final/freeze.json`.

## 8. Versión de desarrollo y renderer

Distribución `1.5.0.dev2`→`1.5.0.dev3`. Motor nativo `1.3.0`, schema YAML `1` y
contratos de captura/observación/análisis sin transición. La versión publicada
estable sigue siendo v1.4.0; no se han alterado sus tags ni activos.

Las cinco fuentes ligadas al renderer histórico no cambian. Conserva versión
`1.5.0.dev1-historical-explorer.1` y digest
`442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b`.
La igualdad de HTML y la igualdad de productor son garantías distintas.

## 9. Comparaciones antes/después reales

| Carga | Mediana dev2 / MAD, s | Mediana dev3 / MAD, s | Cambio de mediana |
|---|---|---|---|
| small | 1.174949 / 0.020441 | 1.177159 / 0.057821 | +0.1881% |
| medium | 9.978064 / 0.444023 | 9.235999 / 0.296051 | −7.4370% |
| larger | 33.318590 / 0.160888 | 31.271646 / 0.851891 | −6.1435% |
| adversarial | 10.665843 / 0.562494 | 9.279541 / 0.023271 | −12.9976% |

La primera pareja larger fue inconsistente: 33.299866→35.066495 s de mediana.
Se conservaron todas las muestras, incluida 43.908725 s. La pareja invertida
mejoró de baseline 33.960679 a candidato 30.541709 s. La fase de rendering mejoró
en ambas parejas; las fases sin cambios también mostraron variación ambiental.
No se aceptó el cambio basándose solo en una fase o eliminando muestras lentas.

Se hizo una confirmación larger en una ventana más tranquila, con candidato
primero, cinco muestras por runtime y un calentamiento excluido: dev3
**32.584346 / MAD 1.053446 s**, dev2 **34.703024 / MAD 0.178273 s**: **6.1052%**.
El peor candidato (33.897263 s)
fue más rápido que el mejor baseline (34.347190 s). Los once datos por versión
dan 34.347190→31.530900 s, 8.1995%, solo como contexto descriptivo secundario;
no sustituir con ese agregado los dos efectos de campaña de aproximadamente 6.1%.

Recibos: `output/v15-04/{before,after}/{block-1,block-2,confirmation}/receipt.json`;
revisión independiente: `benchmarks/{independent-review,phase-review,confirmation-review}.json`.
Cache de archivos, antivirus, temperatura, planificación y actividad ajena del
equipo no están plenamente controlados. No se afirma significancia universal ni
la misma mejora en otras plataformas.

## 10. Memoria e inventarios de salida

Las muestras separadas de memoria larger dieron un peak de asignación Python
tracemalloc de **174,062,151→174,062,312 bytes**: 161 bytes de diferencia. La memoria
del proceso fue **229,732,352→228,876,288 bytes**. No aparece una regresión material
en estas observaciones. PeakWorkingSet/RSS es un máximo de vida del proceso que
incluye imports/setup; no es asignación aislada de la operación. No hay medición
de memoria de procesos hijos. Los tiempos con tracing no se comparan con latencia.

La auditoría independiente rehashó 76 sitios reales, 96,624 archivos y
1,631,323,668 bytes; cero diferencias con el inventario before original. Son
58 generaciones medidas más 18 calentamientos, no 76 tests únicos.

| Carga | HTML / archivos totales | Enlaces locales | Bytes del sitio |
|---|---|---:|---:|
| small | 139 / 141 | 2,771 | 1,324,454 |
| medium | 805 / 807 | 20,881 | 12,021,447 |
| larger | 2,446 / 2,448 | 71,180 | 43,170,895 |
| adversarial | 805 / 807 | 20,881 | 13,062,762 |

Larger retiene 12,028 anchors. Se preservan todos los archivos, manifiestos,
records, ubicaciones, fragmentos, paginación y bytes. Las cargas son ficticias y
finitas, no máximos de capacidad del producto.

## 11. Contratos nativos y de evidencia

No se editó el motor nativo. El comparador corregido fijó ambos mapas de los
33 módulos top-level contra el Git anterior y el inventario candidato autorizado
de 97 módulos, incluyendo `__init__.py`; permite únicamente la excepción exacta
de `explorer_data.py` en el comparador nativo. Los **123 artefactos nativos son
EXACT_BYTES**. No se acepta una excepción global para módulos alterados. Se
preservan validación, reachability, deny/policy, intents, trace, witness,
diagnósticos y rechazo de recursos.

La equivalencia exacta de sitios de arquitectura ya está comprobada. En captura
se rehasharon físicamente **36 sitios, 3,444 archivos, 3,300 páginas y 123,372
enlaces**; coinciden los valores canónicos y congelados, identidades y navegación.
Con cinco muestras medidas por instalación y un warmup, las medianas de control
fueron:

| Control | dev2→dev3, s | Cambio observado |
|---|---|---|
| supported, 10 flujos | 0.234291→0.219505 | −6.3110% |
| limited, 12 flujos | 0.262319→0.249705 | −4.8087% |
| dense130 | 1.951754→1.934180 | −0.9004% |

No se activó el umbral de revisión de regresión de 10%; estas muestras son
controles, no una afirmación de aceleración de captura. Mantienen las correcciones
V15-03 de contexto y paginación. Recibo de estadísticas:
`output/v15-04/profiles/capture/control-summary.json`; rehash físico: `output/v15-04/profiles/capture/physical-review.json`. Nunca se reclasifica un rechazo/no-soportado
como success, blocked o unreachable.

## 12. Límites de productores y reproducción histórica

Cambiar `__init__.py` crea otra identidad de productor en revisions, aunque el
cálculo nativo y HTML permanezcan iguales. Los objetos, revisiones, baselines y
aprobaciones dev2 permanecen intactos; no confieren autoridad de replay a dev3.
Una diferencia de versión de fuente no demuestra cambio del tráfico físico.

La política V15-04 fija el commit/árbol dev2, los dos hashes autorizados y el
inventario completo. Rechaza módulos faltantes/extra/no autorizados y comprueba
bytes instalados antes de importar el runtime. No es una firma; el propietario
debe revisar su nueva autorización. Los verificadores V15-03/V15-02 y sus fixtures
quedan sin modificar, con sus significados originales.

La cadena integral corregida `full-retry` terminó **PASS**: instaló el archivo
dev2 en un entorno separado, ejecutó **24 tests dev2 y 30 tests dev1** en sus
fuentes correspondientes y conservó sus comprobaciones anidadas y referencias
v1.4. El resultado portable en dev3 declaró `analytical_reproduction=False`;
el replay incompatible falló con `EVIDENCE_REVISION`; la fuente original recuperó
la reproducción (`True`). Se mantuvo el mismo bundle ID y los **71 archivos
históricos** permanecieron intactos, verificados también independientemente por
F. La integridad portable por hashes no implica autenticidad ni reproducción
analítica. No se transfirió autoridad de aprobación al nuevo productor.

## 13. Regresiones y ataques controlados

Los tests añadidos comparan Unicode y diagnósticos con la función inmutable,
incluyen combinaciones e invalidación interior, límites 4096/4097 y precedencia.
La política añade casos de módulos/recursos faltantes o extra, fixtures rehashados,
shadowing, bytes instalados maliciosos y bytecode obsoleto. Las **siete regresiones
nuevas de la corrección del comparador** pasaron; F intentó además tres falsificaciones
del límite de comparación y todas fueron rechazadas. No sumar estas ejecuciones
repetidas a los tests únicos de la suite integral.

El primer intento integral de la transición falló con la lista de excepciones de módulos
nativos vacía pese a que `explorer_data.py` estaba autorizado. Ese fallo permanece
con sus logs en `output/v15-04/transition/full`; no fue borrado ni presentado como
PASS. La corrección `compare_native` verifica ambos mapas exactos de 33 módulos,
incluido init, contra fuentes independientes/autorizadas y permite solo el cambio
fijo de Explorer. Se añadieron regresiones negativas, se auditó la corrección y se
repitió la cadena completa como `full-retry`, que pasó con 123 artefactos exactos.

Agent F ejecutó en una copia aislada la mutación `search(value)`→`match(value)`:
un carácter inválido interior pasó a aceptarse, aunque los singleton se comportan
igual. Intentó acompañarla con un recibo autoconsistente rehashado. El verificador
V15-04 rechazó el módulo alterado. El control de copia aprobada pasó. Evidencia
`output/v15-04/audit/independent-mutation-verified/receipt.json` (PASS). No se
modificó la fuente de producción ni los oráculos protegidos para esta prueba.

Las comprobaciones actuales de destino existente/inseguro, fallo parcial de
publicación, dependencia histórica faltante, freshness, revocación y límites se
conservaron en la suite wheel completa aprobada. La suite sdist completa también pasó, con los mismos 4,499 casos únicos. No se elevaron techos ni desactivaron checks para hacerlas pasar.

## 14. Suites completas y herramientas

| Comprobación | Resultado real |
|---|---|
| Ruff lint / formato | PASS / 444 archivos formateados |
| Mypy estricto / pip check | PASS, 278 fuentes / dependencias consistentes |
| Suite completa wheel corregido | 4,498 PASS + 1 skip de junction; 920.36 s |
| Suite completa sdist | 4,498 PASS + el mismo skip; 1,091.89 s |
| Junction fuera del sandbox | El nodo omitido pasa en ambos runtimes: 1 PASS cada uno |
| Histórica exacta dev2 / dev1 | 24 PASS / 30 PASS; sin errores ni skips |
| Referencias nativas | 123 artefactos EXACT_BYTES; 45 casos; manifiesto fuente separado |
| Walkthroughs | Nueve PASS: project, explorer, document, quality, capture, evidence, evidence_history, drift, historical_explorer |
| Benchmark nativo existente | Cinco cargas: tres completas, dos rechazos de recurso correctos |
| Benchmark de calidad/comparación | Tres tamaños, tres muestras cada uno, bytes repetidos idénticos |
| Benchmark de captura | Nueve cargas: ocho completas, un rechazo de recurso correcto |

Hay **4,499 casos únicos actuales**, con los mismos node IDs en ambas suites.
Las dos suites producen 8,998 ejecuciones, incluyendo dos skips; los dos reruns
de junction añaden dos PASS del mismo nodo (9,000 ejecuciones en conjunto).
No son 9,000 tests únicos. Los focos anteriores y el primer wheel de 4,492 casos
son repeticiones/etapas previas conservadas, no cobertura única adicional.

Los archivos de políticas exactas dev1/dev2 se excluyen solo del entorno dev3 y
se ejecutaron sin modificar en sus fuentes/instalaciones archivadas compatibles.
La omisión Windows se debía al sandbox: el control real de junction fue aprobado
fuera de él, con destinos temporales resueltos dentro del workspace y guardia offline.
No se elevó ningún límite ni se desactivó una comprobación para obtener PASS.

Recibos: `regressions/{wheel-retry,sdist,junction-wheel-retry,junction-sdist-retry}.xml`,
`transition/full-retry/{historical-tests.xml,v15-03/historical-tests.xml}` y
`final/commands/receipt.json`. Cada comando conserva argv, cwd, salida, exit y UTC.

## 15. Paquetes e instalaciones

Los archivos corregidos `verified-retry`, construidos desde Git `3410924`, tienen
los siguientes hashes:

| Archivo de implementación verificado | SHA-256 |
|---|---|
| `otarchguard-1.5.0.dev3-py3-none-any.whl` | `6fc57e88217adb5b4824e60cee62e7c341ad529a60abdb23c0d983c9eadf3fda` |
| `otarchguard-1.5.0.dev3.tar.gz` | `3f86107db81ddf0a30dc68f77f74a805a09f361767d90b4c3feeacc506907aae` |

Auditoría de inventario: **104 miembros wheel, 559 miembros sdist, 551 archivos
públicos y 97 módulos de runtime**. Las instalaciones regulares verifican los
bytes autorizados. Conservar los recibos `direct_url`, versión, consola nativa e
inventario de dependencias. La suite sdist integral terminó PASS; la evidencia funcional está vinculada
a los mismos 97 módulos físicos de la implementación `3410924`.

El commit posterior cierra únicamente Markdown. Los archivos de cierre se
reempaquetan en `output/v15-04/packages/closure/`, se auditan contra su propio
commit público y se instalan regularmente. Deben conservar exactamente los 97
módulos ya probados; la comprobación fuente se repite antes de importar runtime.
No se atribuye la auditoría del sdist `3410924` a documentos posteriores, ni se
simula una segunda ejecución funcional sobre código distinto. Las suites completas
anteriores cubren ese runtime idéntico; los hashes del cierre y sus comprobaciones
de archivo/instalación están en `output/v15-04/final/freeze.json`. Ese recibo externo
evita una referencia circular al hash del propio commit o archivo distribuido.

No usar una instalación editable como aceptación. No presentar el hash de un
paquete nuevo como su propia autorización. Si se cierra solo documentación,
identificar qué bytes de runtime se probaron y qué archivos de distribución
cambiaron; repetir la auditoría final de paquetes pertinente.

## 16. Auditoría independiente

Especialistas: A arquitectura, B histórico, C captura, D metodología, E
compatibilidad/paquetes/CI y F auditor escéptico final. Se turnaron según los
cuatro slots disponibles; el integrador mantiene la propiedad de cambios
rastreados. No hubo campañas pesadas duplicadas en la ventana de latencia.

D encontró y comunicó un directorio padre faltante del driver; fue corregido
antes de medir. Se añadió rechazo del modo RSS multicarga para evitar arrastrar
máximos previos. D recalculó estadísticas, verificó paridad y rehashó físicamente
todos los sitios; exigió la confirmación por el primer bloque ruidoso y luego
dio por resuelto ese punto de confianza para la carga seleccionada.

F no identificó P0/P1 en su inspección inicial; la mutación significativa y tres
falsificaciones del comparador fueron rechazadas. F comprobó independientemente la
recuperación original y los 71 archivos históricos intactos. El primer fallo del
verificador, su corrección y el rerun PASS se conservan como parte de la auditoría.
F cerró la auditoría de implementación sin P0/P1 abiertos tras verificar ambos
conjuntos de 4,499 casos, los 54 históricos, paquetes, 123 artefactos nativos,
71 archivos históricos intactos, memoria, controles y los tres benchmarks.
Su revisión de documentos/archivos de cierre se conserva separadamente bajo
`output/v15-04/audit/`; no sustituye el review del propietario ni autentica capturas.

## 17. Hipótesis rechazadas

- `_compact` como cuello dominante o supuesto O(N²): no demostrado por perfiles.
- Eliminar lecturas, validaciones o la segunda auditoría histórica: cumplen
  límites distintos de integridad y bytes publicados; no son trabajo redundante
  demostrado.
- Usar el perfil CPU como porcentaje de aceleración normal o timing con
  tracemalloc como latencia: comparación metodológicamente inválida.
- Declarar una regresión V15-03 de captura: su repetición previa no la reprodujo.
- Descartar la muestra 43.908725 s o escoger solo bloques favorables: rechazado;
  se conservó y se realizó otra campaña completa identificada.
- Optimizar todos los subsistemas o elevar límites para hacer pasar fixtures:
  fuera del alcance y sin justificación.

## 18. Trabajo de rendimiento diferido

T2, el loop BIDI compartido, exigiría otra revisión de identidad del renderer
para una ganancia todavía no medida. T3, `_safe_text` de ingestion/tabular,
recibe 561,943 llamadas en el perfil larger; tiene un predicado similar pero
una superficie mayor: CSV, cada scalar JSON, preflight XML, atributos y extracción
documental. Su coste instrumentado no demuestra su beneficio normal. No se
implementó ni se convirtió en una tercera modificación de runtime.

Histórico ya reutiliza un contexto privado de validación por operación. No se
implementó caché entre ejecuciones ni se saltó replay/freshness. Captura ya indexa
hosts/flujos y destinos por invocación; no hubo evidencia para reescribirla.
Evaluar oportunidades siguientes solo con perfiles y oráculos nuevos.

## 19. Revisión y aceptación del propietario

Revisar el diff final, los dos módulos, autorización literal V15-04 y preservación
de las políticas históricas; comprobar los hashes y recibos archivados. Examinar el efecto
de aproximadamente 6.1% frente al objetivo aspiracional de 15% y la justificación
previa del cambio pequeño. Revisar incertidumbre ambiental y límites de escala.

La aceptación exige cero hallazgos bloqueantes y todos los checks locales
requeridos. **CI hosted de la rama candidata: PENDIENTE DE PUBLICACIÓN POR EL
PROPIETARIO**, seis trabajos de Windows/Ubuntu/macOS × Python 3.12/3.14. El éxito
del CI anterior no sustituye el de este SHA. No insertar umbrales de wall-clock
frágiles en CI; comprobar corrección, límites e identidad deterministas.

## 20. Procedimiento Git/PowerShell de publicación por el propietario

No se ejecutaron push, creación de PR, merge, tag ni Release. Los comandos
siguientes son instrucciones condicionales para el propietario, **solo después
de aceptar la revisión concreta y completar las verificaciones locales**.

```powershell
Set-Location -LiteralPath 'C:\Users\PC\Desktop\OT-ArchGuard-CLEAN'
git status --short --branch
git diff --check
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git fetch --no-tags origin main
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
# Revisar que SHA, árbol y estado coincidan con la entrega final.
git push --set-upstream origin codex/v15-04-performance-scalability
```

Después del push autorizado, se puede preparar una descripción concreta y crear
el PR sin publicar una Release:

```powershell
$prBodyPath = Join-Path (Get-Location) 'output\v15-04\final\pr-body-es.md'
@'
T1 sustituye el scan Python de texto por una búsqueda regex equivalente; conserva
límites y diagnósticos. Dos módulos de runtime cambian mediante política V15-04.
Mejora larger medida: 6.1435% balanceada y 6.1052% confirmación, bytes exactos.
Ver la aceptación y entrega V15-04 para resultados locales, limitaciones,
identidades y revisión de productores. La matriz hosted de seis jobs está pendiente.
'@ | Set-Content -LiteralPath $prBodyPath -Encoding utf8
gh pr create --base main --head codex/v15-04-performance-scalability --title 'V15-04: profile-guided text validation performance' --body-file $prBodyPath
gh run list --branch codex/v15-04-performance-scalability --limit 5
```

El propietario debe leer los seis resultados del SHA exacto antes de considerar
merge. No añadir tag ni Release estable como parte de este gate. Si `origin/main`
avanzó, revisar la integración y repetir checks afectados; no usar reset
destructivo ni force-push.

## 21. Objetivo propuesto para V15-05

Investigar una reutilización estrictamente acotada del informe histórico ya
validado dentro de una sola operación. Antes de optimizar, revisar el límite de
confianza y vida útil: fuente/inventario exactos, invalidación, dependencias,
freshness final, identidad de productor y renderer, verificaciones de publicación
y autoridad actual de aprobaciones. Medir si existe trabajo realmente redundante;
no introducir caché entre ejecuciones ni compartir autoridad entre productores.

Documentar qué fuentes quedan cubiertas por cada digest, qué garantiza integridad
portable y qué requiere replay con fuente exacta. Añadir pruebas adversariales de
cambios intermedios y dependencias faltantes, sin migrar objetos históricos ni
transferir aprobaciones. Un resultado sin optimización es válido si no se demuestra
una reutilización segura y útil.

Solo después, evaluar T3 como experimento independiente y limitado, con oráculos
Unicode/importación inmutables y comparación normal antes/después. Su potencial
1–3% incremental es una hipótesis de investigación, no un beneficio obtenido.

Entrega rastreada: `docs/development/v15-04-handoff-es.md`. El SHA/árbol de
implementación, cierre documental, archivos finales y estado Git están separados
en `output/v15-04/final/freeze.json`. Conservar todo `output/v15-04/` para el review local.
