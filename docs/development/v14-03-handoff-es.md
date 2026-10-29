# OT-ArchGuard V14-03 — entrega de ingeniería al propietario

Fecha: 27 de octubre de 2026, America/Santiago. Distribución `1.4.0.dev1`;
motor nativo `1.3.0`; motor de comparación `1.4.0-drift.1`.

## A. Resultado ejecutivo

Se implementó un motor real de comparación histórica offline: referencia aprobada
exacta, candidatos explícitos, comparabilidad por dimensión, comunicaciones
direccionales, metadatos de siete protocolos, arquitectura declarada, consultas
nativas equivalentes y reportes independientes reproducibles. No hay cambios en
los contratos históricos ni expansión del almacenamiento workspace-v2.

La implementación está registrada en el commit local
`1750f275b0808380ef942184f40cf6a8ba2d5402`.
**READY_WITH_NONBLOCKING_LIMITATIONS — aceptación local.** Las cuatro suites
completas pasan los mismos 3.901 casos únicos; rendimiento pareado, reproducción,
walkthroughs y distribución instalada están comprobados. CI hospedado V14-03
permanece pendiente de publicación autorizada por el propietario. Esto no declara
release estable ni aceptación de los seis trabajos remotos de V14-03.

## B. Semántica de drift

Los dominios son independientes: cambio de declaración, diferencia de observación,
diferencia de metadatos de protocolo, evaluación relativa al modelo, interpretación
analítica, cobertura y abstención. Cada registro contiene clave exacta, fuentes,
estado de comparabilidad, explicación y límites. Una diferencia no establece
anomalía, incidente, atribución, autorización ni seguridad industrial.

Los registros de soporte `OBSERVED_IN_BOTH`, `REACHABILITY_UNCHANGED` y
`RECONCILIATION_ASSESSMENT_UNCHANGED` se cuentan aparte de diferencias y abstenciones.
La taxonomía completa, reglas y versiones están en el
[contrato técnico](v14-drift-contract.md). No se asignan CVSS ni severidades.

## C. Comparabilidad

Se evalúan identidad física/analítica, productor, completitud del contenedor,
paquetes interpretados/no interpretados, fragmentación/truncamiento, linktypes,
timestamps racionales, scope, punto de observación, visibilidad de protocolos,
alineación, modelo, asociaciones, procedencia, scope aprobado y decoder.
Cada dimensión retiene fuentes, motivo y consecuencias de interpretación.

Los estados son `COMPARABLE`, `PARTIALLY_COMPARABLE`, `INDETERMINATE` e
`INCOMPARABLE`. El estado global puede permanecer indeterminado por procedencia
sin impedir una comparación limitada de metadatos. `strict` exige equivalencia
de cobertura/scope de comunicaciones y alineación completa; otros dominios pueden
abstenerse. `qualified` conserva diferencias parciales justificadas; `descriptive`
identifica explícitamente descripciones de datasets. Ningún modo omite validación.

La correspondencia de colecciones es explícita, uno a uno; colecciones no alineadas
generan abstención. Etiquetas coincidentes no autentican sensores. Timestamps se
comparan con fracciones exactas, sin floats, tasas ni tendencias. Los extremos
observados no prueban monitoreo continuo, relojes sincronizados ni ausencia de
tráfico entre paquetes.

## D. Comunicaciones

Se comparan relaciones direccionales de headers: familia IP, IP origen/destino,
transporte, puertos, VLAN y operación ARP cuando corresponda. Se agregan conteos,
estados, flags, evidencia de SYN, hints y metadatos compatibles; no se reconstruyen
sesiones TCP ni roles de cliente/servidor a partir de puertos convencionales.

Se distinguen observaciones comunes, solo referencia, solo candidato, metadatos
distintos y grupos opacos no interpretables. Se preservan hasta ocho referencias
representativas de cada tipo y sus contadores omitidos, junto a identidades exactas
que permiten consultar el soporte original. No observado significa exclusivamente
no identificado en la evidencia finita seleccionada; nunca bloqueo, caída,
desaparición de dispositivo o interrupción del proceso.

## E. Protocolos industriales

Participan Modbus TCP, PROFINET DCP, EtherNet/IP con CIP limitado, S7comm clásico,
IEC-104, OPC UA Binary y DNP3/TCP. Se comparan categorías/header fields permitidos
y contadores positivos, hints, truncados, malformados y no soportados. Se excluyen
payloads de proceso, transacciones efímeras y datos arbitrarios.

Se exige equivalencia exacta de schema, decoder, inventario, límites y semántica
del consumidor. Decoder 1 versus 2 produce interpretación analítica y abstención
de comparación operacional, incluso sobre el mismo PCAP. Un write-type no prueba
escritura ejecutada; CRC DNP3 no autentica origen; OPC UA opaco no revela servicios.
No se amplió ningún decoder ni se adquirieron capturas externas. Los gaps de
interoperabilidad externa Modbus/DCP/IEC-104 mantienen su alcance documentado.

## F. Arquitectura declarada

Se usa el parser/validador nativo y catálogos canónicos de assets, zones,
interfaces, conduits, transport/forwarding edges, services, rules, intents,
scenarios, access points y external dependencies, además de SUC y metadatos raíz.
IDs iguales vinculan declaraciones, sin probar continuidad física. IDs renombrados
se representan como agregado/eliminado, sin heurísticas. Comentarios, espacios y
orden YAML inocuo no generan drift. Cambiar el modelo no demuestra un cambio
desplegado ni un firewall real modificado.

## G. Alcanzabilidad

Consultas explícitas `source_asset_id`/`service_id` usan el motor nativo intacto
y partición común de puertos entre modelos. Se exige semántica equivalente de
SUC, origen/destino, interfaces y servicio; cambios de reglas/edges pueden alterar
el resultado declarado. Se retienen query, intervalos y testigos exactos. Consultas
no equivalentes, incompletas o no soportadas se abstienen; no se tratan como deny.

Los artifacts de reconciliación existentes solo se comparan con modelo exacto
común, asociaciones ACCEPT independientes, relación direccional equivalente y
evidencia soportada IPv4 TCP SYN. UDP, midstream TCP, fragmentos, IPv6, ARP e
identidades pendientes no adquieren conclusiones nativas positivas nuevas.
Alcanzabilidad de modelo no prueba enforcement real ni éxito de aplicación.

## H. Identidades y aprobaciones

Capture SHA identifica colección física; analysis ID identifica interpretación;
baseline/review IDs identifican selecciones y decisiones locales exactas. Una
captura con dos decoders sigue siendo una sola colección. El reporte vincula
baseline completo, scope, miembros seleccionados, aprobación efectiva, frontera
de reviews, snapshots, observaciones, productor y attachments.

Cada operación valida todo el lifecycle fresco, incluyendo objetos no seleccionados.
No existe caché persistente de autoridad, latest-baseline ni aprobación heredada
por candidatos. Revocación/supersesión bloquean uso normal como referencia actual.
El reporte previo conserva bytes y reproduce el grafo registrado, mientras el
verificador informa separadamente `currently_approved_reference: false`.
Reviewers y autoridad organizacional siguen siendo afirmaciones no autenticadas.

Asociaciones entre períodos requieren ACCEPT independiente en ambos lados y
relaciones asset/interface equivalentes dentro del mismo modelo exacto. IP/MAC,
DHCP, NAT, multihoming o etiquetas no bastan para afirmar continuidad de dispositivo.

## I. Persistencia y reproducción

Se publica un JSON standalone `drift_version: 1` fuera del workspace, con identidad
SHA-256 separada por dominio `otarchguard.drift.v1`, versiones de motor/política,
identidades de implementación, inputs/options y resultados. No hay directorio
`drifts/`, migración implícita ni retención de PCAP/payload.

`generate_report` valida una adquisición privada, compara, comprueba nuevamente
bytes originales y publica atómicamente sin reemplazo. `publish` congela una copia
propia del input antes de replay. `verify_report` reconstruye todos los resultados
desde dependencias originales y exige igualdad canónica exacta; rehashear JSON
inventado no otorga validez. Agregar propuestas ajenas posteriores no altera la
reproducción de un reporte anterior. Dependencias ausentes o semánticas de otra
implementación se rechazan. No se autentica fecha de creación ni firma de autor.

## J. Seguridad

La campaña adversarial cubre reportes rehasheados, comparabilidad/conteos/fuentes/
aprobaciones falsas, IDs cambiados, cruces de captura, joins stale, revocación,
supersesión, JSON hostil, Unicode, versiones/keys desconocidas, límites, paths
inseguros, ADS, junction/reparse, sobreescritura e interrupciones.

Se corrigieron antes del freeze: publicación desde objeto mutable del llamador,
tuplas en evidencia nativa que infringían JSON exacto, y contabilidad que hacía
depender replay de propuestas ajenas posteriores. Hay regresiones específicas.
Las comprobaciones de paths mantienen el contrato local de escritor único; no
constituyen sandbox contra un atacante privilegiado que sustituya ancestros.
Metadata original falsa pero autoconsistente no puede autenticarse sin evidencia
externa. El [informe independiente](v14-03-audit.md) evalúa las 22 preguntas y
gates A–N, sin confundir pruebas focales con aceptación completa.

## K. Rendimiento

La adquisición lifecycle permanece una por operación pública. Índices deterministas
evitan productos cartesianos y scans por finding; modelos validados se reutilizan
por operación. Los consumers V14-02P conservan sus bytes.

Budgets nuevos: 64 revisiones seleccionadas/colecciones, 50.000 keys contabilizadas,
20.000 registros, 50.000 registros de protocolo, 200.000 referencias, 32 MiB de
reporte, 128 evaluaciones nativas y 2.000.000 unidades de comparación. Los límites
solo pueden reducirse; se conservan los límites previos del lifecycle y motor.
No se prometen latencia o RSS universal. Las unidades contabilizan operaciones
del comparador y búsquedas/predicados nativos; validación/replay lifecycle,
preprocesamiento del constructor nativo, JSON/hash e I/O tienen límites separados
del contrato histórico. No son un techo de todas las instrucciones CPU. Conteos
y accounting no equivalen a medición física de memoria.

Ocho workloads de drift instalados completaron tres ensayos por caso con igualdad
exacta de outputs, más asignaciones e instrumentación separadas:

| Escala ficticia | Mediana s [mín–máx] | CPU mediana s | Pico trazado MiB | Reporte compacto B | Keys / trabajo contabilizados |
|---|---:|---:|---:|---:|---:|
| 1 | 0,105027 [0,099566–0,108543] | 0,109375 | 0,558 | 92.556 | 21 / 109 |
| 16 | 0,166907 [0,165038–0,167072] | 0,171875 | 1,403 | 188.383 | 81 / 349 |
| 64 | 0,375117 [0,371531–0,385951] | 0,359375 | 4,102 | 495.202 | 273 / 1.117 |

Cada caso cardinal usa una adquisición, 15 lecturas de miembros y 36 parses JSON;
las cinco evaluaciones nativas incluyen replay lifecycle y consultas pareadas.
Con 128 paquetes repetidos por relación se conservan 21 keys y tres registros de
comunicación: mediana 0,262251 s, reporte compacto 113.289 B. Dos pares explícitos
usan tres colecciones distintas y mediana 0,140211 s. También se midieron identidad,
captura incompleta y reinterpretación de decoder sobre una colección.

Timing sin tracemalloc, asignaciones trazadas e instrumentación se ejecutan por
separado. RSS cardinal es 55.316.480 / 59.015.168 / 65.781.760 B de high-water de
proceso con preparación/imports incluidos; no es delta exclusivo del comparador.
Estas escalas finitas no prueban rendimiento universal ni complejidad asintótica.
El caso adicional escala 512 contiene 513 relaciones por captura y 525 registros
(512 soportes comunes, 12 diferencias y una abstención): mediana 2,361868 s
[2,328891–2,381349], CPU 2,375 s, pico trazado 30.907.214 B, RSS de vida del proceso
136.310.784 B y reporte compacto 3.362.130 B. Conserva una adquisición/15 lecturas/
36 parses/cinco evaluaciones. Keys=2.065 y findings=525 pasan como techos reducidos
exactos; 2.064 y 524 fallan con `LIMIT_EXCEEDED`. No se afirma capacidad global
de 20.000 findings ni de 32 MiB a partir de estos ensayos.
Se excluye del recibo final un ensayo preliminar que coincidió con I/O de instalación.

En el bloque original83 V14-02P, las 23 APIs conservan resultados y bytes exactos.
Verificar pasa de 0,683552 a 0,684163 s (+0,09%); listar revisiones, 0,686356 a
0,691477 s (+0,75%); crear revisión, 0,938830 a 0,956977 s (+1,93%). También se
conserva variación: migración +6,13% y revocación +4,32%; no se afirma que cada
operación sea más rápida. Verificación original83, rangos: 0,621061–0,685751 →
0,677614–0,685873 s; pico trazado mediano 2.393.802 → 2.392.659 B y RSS mediano
46.972.928 → 46.755.840 B. El workflow pequeño verifica 0,092088 → 0,098836 s;
se conserva esa medición más lenta (+6,75 ms).

La matriz completa pasó **112 comparaciones pareadas / 672 workers medidos**,
336 pares baseline/candidato comprobados independientemente, con las 23 operaciones
en original83 y workflow más escalas 1/16. NFR nativo pasó cinco workloads (incluye
rechazos previstos dense-policy/interval-heavy); quality pasó tres escenarios con
37/95/308 páginas idénticas; capture pasó nueve, incluyendo 250.000 paquetes en
39,176 s y rechazo de cardinalidad por límite. Todas las muestras, CPU, memoria,
rangos, hashes e inventarios están en el
[recibo público comprobado](../../benchmarks/receipts/v14-03-windows.json).
Son ocho configuraciones iniciales más una cardinalidad adicional; los cinco casos
semánticos repetidos por el segundo runner no se cuentan como casos nuevos.

## L. Pruebas y distribución

El inventario final tiene **3.901 tests únicos**: los 3.764 previos y 137 nuevos.
Las ejecuciones repetidas no aumentan ese conteo. Las suites offline completas
terminaron sin fallos, errores ni skips:

| Entorno real | Resultado | Tiempo pytest | Recibo bajo output/ |
|---|---|---:|---|
| Source Windows 3.14.5 | 3.901 PASS | 796,95 s | v143-source-qa/full-suite.xml |
| Wheel regular Windows 3.14.5 | 3.901 PASS | 799,96 s | v143-wheel-qa/full-suite.xml |
| Sdist regular Windows 3.14.5 | 3.901 PASS | 808,17 s | v143-sdist-qa/full-suite.xml |
| Wheel regular Windows 3.12.14 | 3.901 PASS | 767,19 s | v143-py312-suite.xml |

Estas suites corrieron en paralelo; sus tiempos no atribuyen diferencias de
rendimiento a intérpretes. La medición de benchmarks anterior fue separada y sin
esa carga. Ruff lint/formato (350 archivos), mypy estricto (234 archivos) y pip
check pasan. Los 93 módulos de producción instalados coinciden byte a byte con
source, incluyendo la comprobación posterior de 3.12. Tres reportes producidos
por 3.14 reproducen bajo 3.12, conservando bytes y revocación actual.

Compatibilidad nativa inmutable: 124 archivos capturados iguales; ambos consumers
congelados supported/limited pasan. Ejemplos, corpus sintético y walkthroughs
evidence/history/drift pasan por wheel. Project/Explorer/document/quality/capture/
drift pasan por sdist; las nueve etapas sdist tienen stderr vacío. El primer
recorrido source de 3.787 casos y las pruebas focales anteriores se conservan
como evidencia intermedia, sin sumarlos al inventario final. Un recorrido integrado
intermedio dio 132 PASS/1 fallo de reproducción mientras se editaban fuentes
incluidas en el fingerprint. Se congelaron los bytes y se repitió: 133 PASS y
posteriormente las cuatro suites finales de 3.901 PASS. No se alteraron goldens.
Los logs previos permanecen en `output/v143-integrated-pytest.xml`. Las primeras
instalaciones fallaron por TEMP/cache del sandbox; se resolvieron con directorios
temporales dentro del workspace e instalación offline sin caché, sin cambiar código.

El freeze de implementación auditó 445 archivos públicos y ambas distribuciones.
La entrega documental agrega este handoff, auditoría independiente y recibo,
con 448 archivos públicos, inventarios y archivos finales reauditados. Solo cambia documentación/datos
después del runtime probado. No se agrega captura externa raw al source.

Se conserva la matriz Windows/Ubuntu/macOS por Python 3.12/3.14. V14-02 y V14-02P
sí tienen seis checks hospedados exitosos en sus heads exactos, runs
[40502021558](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40502021558) y
[40502140514](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40502140514).
V14-03 hospedado sigue explícitamente pendiente: no se despachó workflow remoto.

## M. Demostración

Desde la raíz del checkout auditado, con runtime instalado regular y sin red:

```text
python -m tools.drift_walkthrough --output output/my-drift-walkthrough
```

Se crean controller, HMI y engineering workstation ficticios, segmento declarado,
capturas independientes, attachments, mappings revisados y baseline aprobado
por reviewer ficticio. Oracle literal: HMI→PLC común; eng→PLC solo referencia;
endpoint 192.0.2.99→PLC solo candidato e identidad no resuelta; metadato Modbus
read/write distinto; modificación de política declarada y evaluación nativa.

El script compara, reproduce bytes, calcula el digest con oracle independiente,
publica y verifica. También compara captura incompleta y decoder 1/2 sobre la
misma colección, luego revoca aprobación: nuevo compare falla, reporte anterior
reproduce como histórico con autoridad actual falsa. La [guía de uso](../v14-drift.md)
explica contexto exacto y comandos `compare`, `inspect`, `verify`, `summarize`.
El reporte principal instalado es
`drift-98d4db74cd42e65fb321317e73e92fa88f194cd6bcfa70eb94bef043040de95d`:
14 registros, 12 diferencias de dominios separados, un soporte común y una
abstención. El SHA no autentica incidente ni aprobación organizacional.

## N. Git

- Base local/remota verificada: `b25347494a74fb0b2952b11c4cbb69b0a9eb75d6`.
- Rama: `codex/v14-03-historical-drift-analysis`, creada desde V14-02P, no main.
- Implementación congelada: `1750f275b0808380ef942184f40cf6a8ba2d5402`.
- Tag estable v1.3.0: `10d7de6c416ec6f0ee364c671ebe9292ee69e672`.
- Nuevos módulos `drift/*`; integración CLI en `evidence/cli.py`; tests, harness,
  documentación, inventarios públicos y walkthrough CI agregados.
- Cadena preservada: drafts #17→#18→#19→#20; V14-03 depende de #20.
- No push, PR nuevo/editado, merge, tag, release, settings ni workflow dispatch.

El commit de entrega posterior contiene solo documentación, datos de medición e
inventarios; el runtime final probado sigue siendo `1750f27`. El HEAD de entrega,
estado limpio, hashes de paquetes y resultados finales quedan registrados en
`output/v143-final-acceptance.json` y `git log b253474..HEAD`.
El propietario controla publicación y revisión de una futura PR apilada sobre #20.

## O. Próximo hito — V14-04

Interfaces disponibles: `drift.engine.compare`, `reports.generate_report`,
`publish`, `verify_report` e `inspect_report`. Los datos validados incluyen
identidades, dominios independientes, comparabilidad por dimensión, coverage,
queries/witnesses nativos, referencias acotadas/omitidas, conteos y abstenciones.
Un Explorer debe verificar dependencias actuales, distinguir aprobación registrada
de actual y separar registros comunes de diferencias. Debe preservar clocks/gaps,
identidad física no autenticada y ausencia no probada.

No se implementaron Explorer histórico, series temporales automáticas, live
monitoring, detección/alertas, nuevas adquisiciones ni certificación industrial.
La generación exploratoria nueva contra referencias revocadas y series ordenadas
eran opcionales y no se añadieron; replay de reportes históricos sí está soportado.
