# OT-ArchGuard V14-02P — entrega local al propietario

Fecha: 27 de octubre de 2026. Distribución 1.4.0.dev1; motor nativo 1.3.0.

## A. Dictamen ejecutivo

**READY_WITH_NONBLOCKING_LIMITATIONS.** V14-02P implementa y demuestra mejoras
significativas, conservando los resultados, identidades y rechazos del checkpoint
V14-02 dentro del contrato probado. La verificación del caso original mejora
7,47× por API; la creación de revisiones, 6,99×; las propuestas, 9,27×. El pico
trazado de verificación baja 96,54%. Los tres paquetes/entornos probados pasan
3.764 casos únicos, sin fallos, errores ni skips.

La aceptación corresponde a un checkpoint local de desarrollo. Permanecen
pendientes la publicación controlada por el propietario y los seis trabajos de
CI hospedado. No se adelanta drift ni un Explorer histórico.

## B. Resultados antes y después

Baseline exacto: bc3ff41df4fd7c200ec659724aa8c928f549b443. Producción optimizada:
4cb2da9b95fab48c9077696dfcde0ecc60e8adb9. Harness final:
c237f4e8c54ca08a040952e2b74ffd834bad567c. Las versiones de dependencias coinciden;
el inventario completo de módulos instalados verifica esos commits en cada ensayo.

Caso original: 16 colecciones, 32 análisis, 16 modelos, nueve propuestas y nueve
reviews; 83 archivos / 721.436 B. Son tres ensayos alternados por implementación,
sin instrumentación en los tiempos principales. Los casos de escritura agregan
sus prerrequisitos antes del cronómetro y registran la identidad exacta del input.

| API, caso original | Baseline mediana s | Optimizada mediana s | Aceleración | CPU | Pico trazado MiB, antes→después |
|---|---:|---:|---:|---:|---:|
| Migrar | 2,032 | 0,872 | 2,33× | −61,7% | 65,43→1,51 |
| Listar colecciones | 2,830 | 0,735 | 3,85× | −74,9% | 65,76→2,28 |
| Importar adjunto | 7,969 | 1,126 | 7,07× | −86,1% | 67,47→2,44 |
| Crear revisión | 7,690 | 1,100 | 6,99× | −85,9% | 67,47→2,41 |
| Reutilizar revisión exacta | 6,042 | 0,865 | 6,98× | −85,6% | 67,47→2,28 |
| Proponer baseline | 10,791 | 1,164 | 9,27× | −89,2% | 67,45→2,37 |
| Aprobar | 9,708 | 1,025 | 9,47× | −89,5% | 67,45→2,37 |
| Revocar | 9,965 | 1,078 | 9,24× | −89,3% | 67,46→2,37 |
| Verificar completo | 5,708 | 0,764 | 7,47× | −86,6% | 65,87→2,28 |

Verificación API, rangos reales: 5,679–5,854 → 0,738–0,785 s. Consola instalada
en proceso nuevo: 6,191 → 1,588 s, 3,90×. Python 3.12 confirma 7,17× por API y
4,44× por consola; creación 6,92×/4,90× y propuesta 9,42×/6,38×. Son comparaciones
pareadas dentro de cada versión, no una atribución causal entre intérpretes.

La [evidencia técnica completa](v14-02p-performance.md) contiene las tablas de
las 23 operaciones en tres workspaces, consola, rangos, CPU, memoria, crecimiento,
perfil y comandos de reproducción. El [recibo público](../../benchmarks/receipts/v14-02p-windows.json)
preserva todas las muestras. Las seis etapas suman 280 comparaciones / 1.740
workers medidos, más seis pasadas cProfile separadas dentro de workers existentes.

## C. Causas confirmadas

El perfil original mostró dos adquisiciones completas, 64 validaciones nativas
para 16 modelos, 160 validaciones de snapshots para 16 snapshots, 64 inventarios
de implementación y numerosas copias/serializaciones. Las lecturas reservaban
hasta 64 MiB incluso para JSON pequeños. También se repetían joins, construcción
de revisiones y resolución de reviews. El disco por sí solo no explica el costo:
CPU, parsing nativo, consultas de metadata y asignaciones eran materiales.

Después: adquisiciones 2→1, cuerpos de validación de adjuntos 64→16 y revisiones
64→32; modelos nativos 64→16. Lecturas lógicas 2.342→117; bytes 20.513.144→1.019.409;
parses JSON 838→211; serializaciones 105.621→16.397; SHA 6.897→1.040; clones 448→80.
Los mismos objetos únicos siguen comprobados. En el caso denso, validaciones
nativas 28→1 y replay 4→1, con los cuatro análisis y todos sus joins presentes.
Los nombres de validadores reemplazados se normalizan por cuerpos/completados
del contexto; cero llamadas a un nombre antiguo no significa cero validaciones.

## D. Mejoras implementadas

- history.py: lectura del tamaño abierto verificado más centinela, límites e
  identidad antes/después; adquisición privada con datos, inventario, tamaño real
  y SHA de bytes. Los buffers se liberan tras decodificar.
- paths.py: un lstat fresco por componente en las dos comprobaciones de lectura;
  rechazo inmediato de metadata insegura; tags bajo su flag REPARSE. Ocho guardas
  por identidad de funciones cubren observadores concretos/OS. Errores y Path
  personalizados delegan a la política congelada; no se cachea el filesystem.
- validation.py: contexto acotado por operación, validación completa de todos
  los objetos, native models/replay exactos reutilizados solo tras completar sus
  comprobaciones. Fallos invalidan el contexto. Preflight iterativo antes de
  copiar entradas directas; copia de mapas para adiciones.
- lifecycle.py: una adquisición/contexto por invocación; selects y precedencia
  de errores compatibles; resultados y resúmenes sobre el estado ya validado.
- reviews.py: constructor privado estricto seguido de validación del grafo
  prospectivo; la API pública mantiene comprobación completa. Índice de historia
  y mapa de estados reutilizados en la presentación.

Antes de publicar se vuelve a adquirir físicamente el inventario y cada archivo,
comparando SHA de sus bytes exactos. No basta tamaño/mtime. La publicación
atómica sin reemplazo y las comprobaciones físicas de migración se conservan.
workspace.py, observations.py, attachments.py y revisions.py, el motor nativo,
los serializadores y los goldens permanecen byte a byte iguales al baseline.

## E. Seguridad y compatibilidad analítica

La campaña adversarial comprueba tampering con igual tamaño/mtime, hashes
recalculados y joins extranjeros, dependencias inválidas no seleccionadas,
alteración tras un éxito, scope/predecesores/conflictos, fallos tras cache válido,
aliasing del llamador/retornos y repetición de replay en operaciones nuevas.
No existe autoridad de validación persistente entre invocaciones. Una revisión
nueva sigue sin aprobación; rechazo/revocación y conflictos conservan su semántica.

La campaña I/O cubre crecimiento, truncamiento, reemplazo, JSON malformado,
claves duplicadas, límites, disco lleno, interrupción y cambios del origen de
migración. Incluye la transición link inseguro→archivo regular: no puede borrarse
una condición insegura ya observada. 292 casos focales pasan en Windows 3.12 y
3.14, incluyendo 45 casos nuevos de paths, con symlinks reales y una junction
existente. La creación de una junction nueva fue denegada; otros flags se prueban
con metadata controlada, sin afirmar haber creado todos esos tipos de objeto.

Tres experimentos incompletos se preservan y excluyen de resultados finales:
un preflight ASCII sobrecargaba snapshots UTF-8 válidos; una integración se detuvo
para incorporar el helper de paths; y el guard del harness detectó que el caso
denso de reutilización pedía una revisión aún inexistente. Se corrigieron el piso
UTF-8 conservador y los prerrequisitos del fixture, con regresiones específicas.
También se cerró el bypass de observador concreto del prototipo antes de integrarlo.
No se normaliza texto ni se cambia el hash para ajustar límites.

El auditor de caché no es el autor del contexto; el autor del grafo revisó los
paths de otro autor. El roll-up final declara su autoría previa del contexto y
se apoya en esas comprobaciones cruzadas, sin llamar independiente a su propia
implementación. Las 20 preguntas del mandato tienen disposición documentada en
output/v142p-final-acceptance-audit.json; no queda un bloqueo local de integridad,
seguridad o corrección. La entrega documental final conserva esos bytes probados.

La corrección pequeña de corpus cambia únicamente cisa-opcua-gap de PCAP a
PCAPNG: magic, tamaño y SHA locales confirman el formato. Los bytes, licencia y
provenance originales no se alteran; el check de corpus pasa. No se agrega decoder.

## F. Recursos y crecimiento

La CPU de verificación baja 5,703→0,766 s. Pico trazado 65,873→2,281 MiB
(−96,54%); RSS de proceso nuevo 108,730→44,660 MiB (−58,93%). RSS incluye importación
y runtime; no equivale al pico trazado de la operación. Las mediciones trazadas
no fundamentan los multiplicadores de latencia.

Con 256 colecciones: 513 archivos / 3.366.721 B, verificación 22,822→2,242 s,
10,18×; listar colecciones/revisiones mejora 5,06×/5,03×. C64/128/256 optimizado
es 0,701/1,196/2,242 s: crecimiento observado 1,71×/1,87×. Se alcanza el límite
de cantidad, no el límite de 256 MiB ni una garantía de capacidad industrial.

A una colección y catálogo idéntico de 128 modelos, R16/64/128 verifica en
10,655/14,917/20,582→2,284/2,548/2,797 s. Profundidad de reviews, cantidad de
propuestas y modelos no referenciados tienen ejes separados y manifests reales
comparados. Fan-out16/32/64 con el mismo modelo/capture: 9,517/18,958/37,795→
0,288/0,508/0,852 s, hasta 44,3× en ese ensayo; mapping/comparison/revision crecen
juntos. No se deduce una ley asintótica general ni throughput de producción.

Cada operación independiente vuelve a validar. Siguen costos necesarios de
parsing por modelo distinto, replay por comparación distinta, canonicalización,
snapshot en dos fronteras de confianza y segunda lectura antes de publicar.
No se introduce un caché persistente para acelerar una secuencia creciente de writes.

## G. Pruebas y paquetes

| Puerta ejecutada | Resultado |
|---|---|
| Wheel instalado Windows / Python 3.14.5 | 3.764 PASS; 720,12 s |
| Sdist separado Windows / Python 3.14.5 | 3.764 PASS; 707,29 s |
| Wheel instalado Windows / Python 3.12.14 | 3.764 PASS; 704,70 s |
| Identidades de test | mismos 3.764 en los tres; 3.573 originales retenidos +191 nuevos |
| Fallos / errores / skips | 0 / 0 / 0 en cada suite |
| Ruff / formato / mypy estricto | PASS; 329 archivos formateados / 217 comprobados |
| pip check e identidad instalada | PASS en los tres entornos probados |
| Compatibilidad nativa histórica | PASS; 124 artefactos bajo la allowlist establecida |
| Consumidores frozen supported/limited | ambos PASS |
| Walkthrough histórico instalado | PASS; dos ejecuciones con IDs canónicos idénticos |
| Evidence/project/Explorer/document/quality/capture | seis walkthroughs PASS |
| Ejemplos offline | 31 comandos instalados validados; runner exit 0 |
| Auditoría de medición independiente | 280 comparaciones / 1.740 workers, PASS |
| Inventarios fuente/wheel/sdist | 423 archivos en el checkpoint medido; 426 en la entrega documental |

Los procesos Python de aceptación tienen operaciones de red denegadas. Son
instalaciones regulares, no editables ni imports desde src. Los tiempos de tests
son ejecución de QA, no un benchmark de rendimiento comparativo. Recibos XML,
logs y comparación exacta de sets: output/v142p-full-suite-summary.json y
output/v142p-full-{wheel,sdist}.*, output/v142p-full312.*.

La auditoría final de source/archive se repite sobre el commit documental. La
entrega prueba igualdad de los módulos, tests, fixtures y tools respecto de c237,
y bytes iguales de cada miembro del wheel medido; el sdist solo agrega/actualiza
documentación, datos/gráfico, inventarios y SOURCES generado. Recibos:
output/v142p-delivery-source-checkout.json, -archive-audit.json y -parity.json.
El entorno .venv del proyecto recibe el wheel optimizado auditado al cierre;
el baseline original permanece preservado. No se distribuyen capturas externas.

## H. Límites y hallazgos negativos

Inicialización original: API +0,644 ms (+4,57%) y consola +47,048 ms (+5,31%)
en el bloque principal. Los tres pares de esa consola fueron más lentos. Los
otros dos bloques principales de inicialización fueron más rápidos. El seguimiento
con nueve pares conserva API original +0,301 ms (6 más lentos/3 más rápidos),
consola densa +4,662 ms (4/5) y consola workflow +9,054 ms (5/4). La consola
original mejora 13,650 ms en el seguimiento (3/6): no repite la dirección anterior.
Ambos estudios completos se conservan. El código del inicializador/helpers es
igual; eso y el solapamiento de rangos no prueban causa ni insignificancia.

La única mediana RSS mayor del estudio de memoria es inicializar el original:
+88 KiB (+0,222%), los tres pares mayores; queda registrada con rangos completos.
No hay medianas de pico trazado mayores. Son límites no bloqueantes, sin afirmar
que cada fila sea más rápida ni descartar datos negativos como ruido.

Persisten un escritor local, código instalado confiable y afirmaciones humanas
sin autenticación organizacional; los hashes no prueban autenticidad del capture,
verdad, seguridad operacional ni cobertura completa. No se acreditan defensas de
sandbox frente a un escritor privilegiado concurrente. Los límites de trabajo
no son SLA. Las mediciones son finitas, en una máquina Windows con caches de OS,
antivirus, scheduling y frecuencia no forzados. El plan existente Máximo rendimiento
se registró; no se afirma monitoreo continuo. Linux/macOS y los seis jobs hospedados
V14-02P siguen pendientes; el éxito antiguo de V14-01 no se hereda.

## I. Checkpoint Git y publicación

Rama local: codex/v14-02p-history-performance-hardening. Inicio exacto V14-02:
bc3ff41df4fd7c200ec659724aa8c928f549b443; implementación previa V14-02:
3724062639b63c0d37e4b29ea11eabbf25bc4f5f. La rama original y v1.3.0 permanecen
preservados; el tag estable apunta a 10d7de6c416ec6f0ee364c671ebe9292ee69e672.

| Commit local V14-02P | Cambio |
|---|---|
| ca1165456ce1da822e190010d86663e7e69acbfb | Baseline/harness independiente y mantenimiento de corpus |
| ae13d9474564699c271770334c35828f760f7aa1 | Lecturas acotadas y adquisición histórica |
| 59d2d2065c515058b6ff7000d9ac5122ce61c54d | Contexto, lifecycle y reviews integrados |
| 5e82d3628c2799903d852878d0b9bc3f7dc5fdc1 | Compatibilidad UTF-8 y ejes independientes |
| 4cb2da9b95fab48c9077696dfcde0ecc60e8adb9 | Implementación final: metadata fresca eficiente |
| c237f4e8c54ca08a040952e2b74ffd834bad567c | Harness final: prerrequisitos y estados estrictos |

El commit posterior de entrega documental contiene este informe, el registro
técnico, las 1.740 muestras y la figura. Su SHA se entrega en el mensaje final;
no se incrusta un autohash en el archivo que lo determina. El cierre exige Git
limpio. Los archivos funcionales cambiados son cinco módulos históricos
(history/lifecycle/reviews/paths/validation), seis módulos de tests, harness/worker,
la corrección declarativa del corpus y documentación/inventarios/recibos. Los
cuatro productores congelados, nativos y goldens no cambian.

No hubo push, PR, tag, merge, dispatch ni release. Próximo paso del propietario:
revisar los checkpoints locales V14-02 y V14-02P, elegir base/dependencias de
publicación y autorizarla explícitamente; volver a comprobar refs y ejecutar
Windows/Ubuntu/macOS × Python 3.12/3.14 sobre el SHA publicado. Preservar los
baselines y los recibos al publicar; no usar las mediciones como aprobación humana.

## J. Decisión para V14-03

**READY_WITH_NONBLOCKING_LIMITATIONS.** Las APIs públicas de lifecycle entregan
datos completamente validados con referencias exactas y estado de revisión
determinista; el futuro consumidor no necesita cachés persistentes inseguros ni
aprobaciones implícitas. No queda una regresión local de corrección/integridad/
seguridad ni un cuello mayor evitable sin resolver en el alcance medido. Deben
respetarse los límites de H, completar CI hospedado antes de aceptación remota y
definir por separado comparabilidad de cobertura y significado del drift.
