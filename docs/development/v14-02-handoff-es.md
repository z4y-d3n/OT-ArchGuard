# V14-02 — Entrega de ingeniería

Fecha de trabajo: 26 de octubre de 2026, America/Santiago.
Distribución probada: `1.4.0.dev1`. Motor nativo preservado: `1.3.0`.
El [registro de aceptación](v14-progress.md) conserva los recibos y checkpoints
históricos. Esta entrega es desarrollo local, no una publicación estable.

## A. Resultado ejecutivo

Implementados workspace-v2, migración explícita desde v1, cuatro clases de
adjuntos validados, revisiones analíticas inmutables, propuestas de baseline de
evidencia/arquitectura y decisiones humanas locales con aprobación, rechazo,
revocación, supersesión y detección de conflictos. El CLI incluye inspección
legible y diagnósticos JSON. Se preservan las tres identidades independientes:
captura física, interpretación analítica y decisión humana.

No se implementaron drift, clasificación de desviaciones, riesgo industrial,
ausencia de tráfico ni Explorer histórico. Tampoco autenticación de revisores,
cadena de custodia o una certificación de seguridad operacional.

## B. Arquitectura

`workspace.json` declara workspace 2 y contratos snapshot/attachment/analysis/
baseline/review 1. Los directorios `snapshots`, `attachments`, `analyses`,
`baselines` y `reviews` contienen objetos JSON inmutables con nombres por hash.
No hay base de datos, índice mutable ni puntero global de baseline vigente.
La pertenencia se deriva del inventario validado; la procedencia migrada fija
además la pertenencia y hashes exactos de los snapshots originales.

Los nuevos IDs usan SHA-256 sobre JSON canónico ASCII con claves ordenadas y
dominio separado por tipo. El ID físico conserva el SHA original del capture.
Una revisión referencia observaciones/componentes por identidad y no duplica
sus observaciones. Etiquetas, rutas, nombres locales y relojes no alteran la
identidad analítica. El [contrato técnico](v14-history-contract.md) fija campos,
canonicalización, límites y políticas de compatibilidad.

## C. Migración

`evidence migrate ORIGEN DESTINO` exige origen v1 válido y destino nuevo,
separado del origen. Valida todo antes de reservar el destino; copia snapshots
sin reserializar; comprueba nuevamente bytes de origen/destino; publica el
manifiesto final únicamente al completar. Conserva IDs, bytes, hashes y etiquetas.
El origen no se modifica. El lector v1 sigue rechazando workspace-v2.

Las pruebas cubren corrupción, versiones desconocidas, duplicidad física,
destino existente, links/reparse points, límites, disco lleno, interrupción y
cambio de fuente. Un destino interrumpido queda sin manifest válido, para
inspección o cuarentena manual; se reintenta en otro destino nuevo. No se borran
ni reparan evidencias automáticamente.

Limitación inherente: el manifiesto v1 no enumeraba snapshots. No puede detectarse
un snapshot eliminado antes de iniciar la validación si lo restante constituye
un workspace v1 válido. V2 fija la pertenencia realmente observada y detecta la
pérdida posterior de cualquiera de esos miembros migrados.

## D. Adjuntos y revisiones

| Adjunto | Validación implementada |
|---|---|
| Enrichment | Esquema 1, decoder 1/2, digest original, capture exacto, joins disponibles de paquetes/interfaces/endpoints, selección de protocolo y allowlists de privacidad. |
| Modelo | Parseo y validación nativa real de schema 1, modelo canónico y SHA nativo; archivo YAML de entrada intacto. |
| Mapping revisado | Modelo exacto, captura/observaciones, candidatos, decisiones, reviewer/rationale y digest completo mediante consumidor nativo. |
| Comparación | Modelo y mapping exactos; replay nativo completo y comparación canónica de todos los resultados. |

`observations_sha256: null` de enrichment V14-01 es válido y se conserva como
ausencia de binding declarado por el productor. El consumidor attachment-v1
también admite un binding explícito solo si coincide exactamente y su digest
original verifica; valida la estructura congelada mediante una copia equivalente
con binding nulo, sin modificar lo almacenado ni el productor original.

Los componentes ausentes son null explícitos. Comparison tiene digest separado
de attachment aunque su productor congelado no publique uno propio. El modelo
retenido es canónico: comentarios o formato YAML no inventan otra interpretación.
Mappings no demuestran propiedad física de direcciones.

El manifiesto de semántica vincula contratos, decoder, fuentes exactas del
parser/evaluador/consumidores, límites y opciones realmente verificadas.
Observaciones antiguas no acreditan código/configuración original del productor:
esa procedencia permanece explícitamente no atestiguada. El runtime acepta su
inventario exacto; futuras implementaciones requieren consumidor compatible
explícito, sin reinterpretar silenciosamente revisiones históricas.

## E. Baselines y aprobación

Una propuesta de evidencia selecciona revisiones exactas, como máximo una por
colección física; una propuesta de arquitectura exige un modelo validado. Scope
incluye ambiente, propósito, cobertura declarada, incertidumbres, puntos de
observación y protocolos. Cobertura desconocida sigue siendo desconocida.

La propuesta comienza `PROPOSED`. Solo comandos explícitos de decisión crean
review records con sujeto, scope, reviewer, rationale, referencias y predecessor.
`approve` produce aprobación local; `reject` rechazo terminal; `revoke` desactiva
la aprobación exacta del mismo baseline; `supersede` aprueba otra propuesta del
mismo tipo/scope y conserva la anterior como `SUPERSEDED`. Cada aprobación tiene
como máximo un sucesor. Forks, referencias imposibles y aprobaciones activas
contradictorias bajo el mismo scope fallan. Los relojes no resuelven autoridad.

Un baseline exacto rechazado o revocado es terminal; otra selección requiere una
propuesta distinta. Scopes diferentes pueden tener aprobaciones independientes.
Una revisión nueva nunca hereda aprobación. Los registros históricos no se
reescriben ni eliminan. `baseline review/show --text` expone una síntesis acotada.

Todos los reviewers utilizados automáticamente son ficticios. No se aprobó
evidencia operativa ni artefactos de desarrollo en nombre del propietario.

## F. Seguridad

38 pruebas independientes desafían hashes recalculados, offsets/puertos y
contadores incompatibles, sujetos/scopes falsificados, decisiones obsoletas,
sucesores contradictorios y fallos de publicación. La auditoría corrigió un
rechazo falso de Windows/Python 3.14: `fstat` y `lstat` no exponen necesariamente
el mismo ctime. Las comparaciones actuales usan estadísticas del mismo origen.

Rutas locales portables, rechazo de traversal/UNC/device/ADS/symlink/junction,
lecturas regulares acotadas, inventarios estrictos y publicación sin reemplazo
mantienen el modelo de escritor único. SHA-256 establece integridad, no
autenticidad ni autoridad organizacional. No hay sandbox de sistema operativo
ni protección acreditada frente a un escritor concurrente privilegiado.

Validar metadata no reabre PCAP originales. Referencias muestreadas permiten
joins exactos; referencias no muestreadas solo los invariantes disponibles.
Rationales y topología pueden ser sensibles y deben revisarse antes de compartir.

## G. Pruebas

Aceptación local final: **3.573 pruebas PASS** en wheel instalado (727,32 s) y
**3.573 PASS** en un entorno separado instalado desde sdist (703,12 s), sin
fallos, errores ni skips. Son 193 casos nuevos sobre los 3.380 de V14-01; las
repeticiones de suites no se suman como pruebas únicas. Los procesos hijos
tuvieron operaciones de red Python denegadas, sin `PYTHONPATH=src`, y los
inventarios de módulos instalados coinciden byte a byte con la fuente revisada.
Recibos: `output/v142-wheel-suite.xml`, `output/v142-sdist-suite.xml` y
`output/v142-*-environment.json`.

Resultados adicionales ejecutados: 193 pruebas nuevas finales PASS en wheel
instalado (30,61 s, `output/v142-new-final.xml`); foco inicial 244 PASS; auditoría independiente final
38 PASS; Ruff y formato PASS; mypy estricto PASS sobre 207 archivos; `pip check`
PASS en los tres entornos; comparación nativa inmutable PASS sobre 124 archivos;
readers congelados supported/limited PASS; walkthroughs instalados de evidencia,
proyecto, Explorer, documentos, calidad y captura PASS; ejemplos PASS.
Inventarios de fuente y archivos wheel/sdist auditados sin bytes externos.
Recibos de entrega documental: `output/v142-delivery-source-checkout.json` y
`output/v142-delivery-archive-audit.json`.

La demostración histórica del CLI instalado se ejecutó dos veces con IDs
idénticos. El oráculo literal independiente está en
`tests/fixtures/evidence-history-v1/identity.json`.

Benchmark finito, Windows 11 / Python 3.14.5: 16 colecciones, 32 revisiones,
16 adjuntos de modelo, nueve baselines y nueve reviews; 83 archivos, 721.436 B.
Snapshot bytes: 390.952 B; mayor objeto: 35.049 B; 486.560 B de observaciones
evitados al no duplicarlas en las 16 revisiones de una colección.

| Operación con tracemalloc | Segundos |
|---|---:|
| Migrar 16 snapshots | 2,982 |
| Adjuntar 16 modelos y crear revisiones de una colección | 167,087 |
| Completar membresía de las 16 colecciones y proponer baseline | 262,707 |
| Cadena de ocho aprobaciones/supersesiones y revocación | 421,685 |
| Listar colecciones / revisiones | 6,496 / 6,584 |
| Tres verificaciones completas | 41,511 |
| Rechazar referencia inválida / techo de recursos | 6,447 / 1,043 |

Pico de asignaciones Python medido: 72.110.561 B; RSS histórico máximo del proceso:
124.932.096 B. Sin tracemalloc, tres verificaciones tardaron 5,979 / 6,196 / 6,025 s
(18,200 s total). Son cargas sintéticas pequeñas y ejecución compartida local,
sin promesa de capacidad productiva. RSS no equivale a asignaciones Python.
La lectura reserva hasta 64 MiB incluso para objetos pequeños y se reiteran
validadores; son optimizaciones medidas pendientes antes de escalar V14-03.

Los ocho captures externos previamente adquiridos verificaron sus SHA/tamaños
fijados e ingresaron como metadata sin reviews/baselines. Se detectó una ficha
anterior inexacta: `cisa-opcua-gap` declara PCAP, pero los bytes hash-pinned son
PCAPNG. El parser detecta correctamente el formato; el verificador de corpus
rechaza esa discrepancia declarativa. Se conserva y documenta como pendiente
del registro externo, sin modificar bytes, redistribuirlos ni atribuir cobertura
industrial adicional. Recibo local: `output/v142-optional-external-lifecycle/receipt.json`.

CI hospedado V14-01: seis configuraciones PASS en head exacto `bdf51dc`, run
`40417348042`. CI hospedado V14-02: pendiente de publicación autorizada; no se
ejecutó ni se hereda del hito previo. La matriz Windows/Ubuntu/macOS × 3.12/3.14
permanece intacta; incorpora el walkthrough histórico en el gate futuro.

## H. Compatibilidad

Conservados schema YAML 1, motor/evaluador nativo 1.3.0, observaciones 2,
capture/association/comparison/catalog 1, snapshot/workspace-v1 y enrichment
schema 1 con decoder 1/2. No cambiaron parser/observaciones/reconciliación nativos,
reachability, snapshots v1, fuentes/goldens congelados ni las identidades previas.
Los nuevos contratos son aditivos y explícitamente versionados. Se mantiene
distribución 1.4.0.dev1; no se publicó distribución estable ni tag.

## I. Demostración

Desde una instalación regular del paquete y la raíz del repositorio:

```console
python -m tools.evidence_history_walkthrough --output output/new-history-demo
python -m benchmarks.evidence_history --output output/new-history-benchmark
```

Ambos destinos deben ser nuevos. La primera orden crea dos capturas ficticias,
migra snapshots originales sin modificar el origen, adjunta enrichment y genera
interpretaciones alternativas; adjunta modelo, mapping revisado y comparison
nativa; propone baselines de evidencia/arquitectura; aprueba, supersede y revoca
con reviewer ficticio. Rechaza adjuntos cruzados y aprobación obsoleta/conflictiva.
Repite todo y compara IDs mediante consumidor canónico independiente.

Resultado final instalado: dos colecciones, dos snapshots, cuatro adjuntos,
cuatro revisiones, tres propuestas, tres decisiones; un baseline supersedido,
uno revocado y ninguna aprobación activa. El historial permanece íntegro.
Recibo: `output/v142-installed-history-walkthrough/walkthrough.json`.
La [guía operativa](../v14-history.md) documenta cada comando individual.

## J. Estado Git

- Rama local: `codex/v14-02-evidence-revisions-and-baselines`.
- Inicio exacto: `bdf51dc54f991ab9edc1a09176b5e55b2ad0df6e`, árbol limpio.
- `e714771`: workspace-v2 y migración; etapa verificada antes del commit.
- `acb139f`: contratos de adjuntos/revisiones; 83 pruebas focales PASS.
- `3724062`: baselines, CLI, auditoría, fixtures, guías e inventarios; fuente de
  implementación utilizada para los paquetes y suites de aceptación.
- El commit documental que contiene esta entrega añade resultados/limitaciones;
  no modifica código runtime, tests ni fixtures. `git log -4 --oneline` identifica
  la entrega exacta; el resumen final al propietario informa su hash.

Estado de entrega: árbol limpio después del commit documental. Los resultados,
entornos y fuentes externas permanecen ignorados. Se repiten las auditorías de
fuente y paquetes sobre ese árbol documental; los bytes runtime/tests/fixtures
siguen siendo los de la implementación probada. El inventario público final
incluye 412 archivos, sin packet bytes de terceros.

La lista completa de archivos cambiados se obtiene con
`git diff --name-only bdf51dc54f991ab9edc1a09176b5e55b2ad0df6e..HEAD`.
Incluye módulos de evidence, seis archivos de pruebas, fixture de identidad,
walkthrough, benchmark, documentación e inventarios; no captures externos.
La dependencia sigue siendo Draft PR #18 sobre Draft PR #17, ambos sin merge.
No se realizó push, PR nuevo, merge, tag, release ni cambio remoto.

Próxima operación controlada por el propietario: revisar esta rama y autorizar,
si corresponde, su publicación y verificación hospedada sobre el head exacto.
La integración remota o release exige esa decisión separada.

## K. Pendientes para V14-03

Consumir `lifecycle.load_state`, `show_object`, `list_revisions` y
`verify_lifecycle`, que validan semántica y joins completos; no conferir autoridad
analítica a `history.read_history` o al hash genérico sin el consumidor lifecycle.
Están disponibles colecciones originales, componentes validados, manifiestos de
semántica, revisiones exactas, propuestas y estado determinista de reviews.

V14-03 debe definir comparabilidad de cobertura, alcance, interpretación y
ventanas antes de calcular drift; no inferir bloqueo por observaciones ausentes.
Debe respetar revocaciones/supersesiones y no trasladar aprobación a entradas
nuevas. Optimizar lecturas/validación repetida usando las mediciones antes de
elevar escala; no se justifica introducir una base de datos sin otro análisis.

Siguen separados: interoperabilidad externa de Modbus/DCP/IEC-104; linktypes
NULL/SLL no soportados; corrección de la ficha externa PCAP/PCAPNG indicada;
consumidores explícitos para futuras implementaciones; CI hospedado V14-02,
freeze de release y decisión de publicación. El Explorer histórico corresponde
a V14-04 y no forma parte de esta entrega.
