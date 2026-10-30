# V14-05 — Rendimiento comparado y límites de interpretación

Medición local del 29 de octubre de 2026. Padre `d898516e24dec922179696e4cb50a262b3466a46`;
candidato de implementación `e4d8234acd504ca30d6d0aef66f316b8cf1c86d0`. Los 97 módulos de producción son
idénticos: inventario `e8900197961db578c83aca3576cf4883077b40dce243b4bc9af02553d8759cf2`. No se realizó
optimización de producción. Todas las filas más lentas se conservan y no se
atribuyen causalmente a un cambio de código inexistente.

## Entorno y método

Windows-11-10.0.26100-SP0, AMD64, CPython 3.14.5.
Ambos intérpretes comparten las mismas versiones de dependencias aprobadas:
Typer 0.27.3, PyYAML 6.0.3, Pydantic 2.14.1. Instalaciones regulares, inventarios
comprobados contra sus commits. No hubo suites concurrentes durante los tiempos.
El SO, caché, frecuencia/temperatura y otras aplicaciones no están controlados.

Las tablas muestran **mediana [mínimo–máximo] en segundos**. Protocolo usa tres
ensayos sin tracing, un warmup excluido y un ensayo de allocations separado.
La regresión de siete operaciones conserva cinco ensayos y warmup de su harness.
El histórico alterna procesos padre/candidato: 60 parejas exactas /
120 workers, tres ensayos por lado/fila, latencia y memoria en modos
distintos. Lecturas tienen warmup; cada escritura empieza con copia fresca sin
warmup mutante. Explorer conserva tres ensayos por componente, warmup de
generación y un ensayo de allocations separado. Los otros estudios ejecutan
primero un lado y luego el otro: existe sesgo de orden posible.

RSS es el máximo de vida del proceso, incluye intérprete/imports y, para
protocolo/Explorer, trabajo anterior del mismo proceso. No equivale a memoria
propiedad de una función. Tracing no se mezcla con tiempos primarios. Estas
cargas ficticias finitas no establecen capacidad industrial ni un límite de
latencia/memoria de peor caso hostil.

## Protocolos: escaneo y serialización pretty

Extensión mínima del benchmark original, que sólo medía una observación con
tracemalloc. `benchmarks/protocol_regression.py` conserva sus productores y
frontera de serialización, separa latencia/allocations y valida fuera del tiempo.
Identidades completas de los seis PCAP en `protocol_input_sha256` del recibo
compacto. Cambios de entrada o de salida rechazan un recibo de aceptación.

| Carga fija | Bytes entrada | Registros retenidos | Padre | Candidato | Pico Python separado B, padre → candidato |
|---|---:|---:|---|---|---:|
| malformed-1000.pcap | 80,024 | 1000 | 0.066005 [0.065799–0.066402] | 0.067614 [0.067026–0.068874] | 3,791,489 → 3,791,489 |
| metadata-ceiling.pcap | 1,725,024 | rechazo | 0.778056 [0.771892–0.791508] | 0.786538 [0.759900–0.788331] | 29,474,928 → 29,474,928 |
| mixed-700.pcap | 57,524 | 700 | 0.046859 [0.046402–0.047187] | 0.049354 [0.047270–0.050053] | 2,762,311 → 2,762,311 |
| mixed-7000.pcap | 575,024 | 7000 | 0.487452 [0.476475–0.488819] | 0.455606 [0.450107–0.465784] | 27,794,919 → 27,794,919 |
| supported-unsupported-1400.pcap | 100,924 | 700 | 0.055056 [0.054942–0.055954] | 0.056194 [0.055569–0.056891] | 2,766,843 → 2,766,843 |
| view-ceiling.pcap | 16,479 | 1 | 0.003458 [0.003222–0.003699] | 0.003259 [0.003166–0.003524] | 185,257 → 185,257 |

Las salidas y counters son exactos entre lados. Mixed700/7000 serializan
852.491/8.519.687 bytes. El caso mixto de 1.400 paquetes conserva 700 registros
y cuenta explícitamente 700 saltados por EtherType. Los 21.000 paquetes de
`metadata-ceiling` alcanzan primero `enrichment_metadata_bytes`: rechazo fatal,
sin artefacto parcial exitoso; no es una demostración del techo de 20.000
registros. El view de 16.385 bytes conserva una abstención explícita.

## Historial: verificación, revisiones, propuestas y reviews

Se reutiliza `benchmarks.history_performance`, sin cambios. El workload original
mantiene sus 83 archivos y 32 revisiones; el otro es el workflow público pequeño
de dos colecciones/dos revisiones. Hash por miembro, digest de inventario,
bytes y resultado exacto están en `historical_workloads` y `historical` del recibo.
Los workers rechazan respuestas inesperadas y requieren ADDED en las escrituras;
ALREADY_PRESENT no puede hacerse pasar por una nueva revisión/review.

También se reconstruyó el original con el comando público
`benchmarks.evidence_history --collections 16 --revisions 16`: sus 83 archivos /
721.436 bytes coinciden exactamente con la carga medida, inventario
`0ab2dd4e667067b1a765495ea68d13d63d01e9a268524ccefa3be030b834c905`.
Recibo: `output/v145/original83-reproduction.json`. Los tiempos de esa preparación
no se incorporan a la comparación primaria.

| Workload / operación | Padre | Candidato | Cambio observado |
|---|---|---|---:|
| original83 / verify | 0.736745 [0.710525–0.744643] | 0.746652 [0.745268–0.748745] | +1.34% |
| original83 / create_revision | 1.087262 [1.037139–1.096249] | 1.080217 [1.070549–1.092645] | -0.65% |
| original83 / propose_baseline | 1.127283 [1.113174–1.151780] | 1.110654 [1.050096–1.128979] | -1.48% |
| original83 / approve | 1.130085 [1.067371–1.160978] | 1.107102 [1.084166–1.152074] | -2.03% |
| original83 / revoke | 1.092223 [1.067336–1.105422] | 1.100491 [1.093393–1.129572] | +0.76% |
| workflow / verify | 0.094717 [0.092092–0.097238] | 0.092998 [0.092136–0.098210] | -1.81% |
| workflow / create_revision | 0.166291 [0.159435–0.182414] | 0.177959 [0.177775–0.187745] | +7.02% |
| workflow / propose_baseline | 0.158918 [0.156980–0.169436] | 0.160520 [0.160095–0.171547] | +1.01% |
| workflow / approve | 0.170157 [0.162822–0.176971] | 0.189429 [0.171287–0.191640] | +11.33% |
| workflow / revoke | 0.171951 [0.162310–0.184037] | 0.186570 [0.173873–0.209844] | +8.50% |

Allocations y RSS se midieron en workers separados de los tiempos anteriores:

| Workload / operación | Pico Python B, padre → candidato | RSS de vida B, padre → candidato |
|---|---:|---:|
| original83/verify | 2,393,475 → 2,393,951 | 47,939,584 → 47,788,032 |
| original83/create_revision | 2,525,613 → 2,526,110 | 48,132,096 → 48,033,792 |
| original83/propose_baseline | 2,480,847 → 2,480,849 | 47,910,912 → 48,238,592 |
| original83/approve | 2,481,596 → 2,481,478 | 48,009,216 → 47,943,680 |
| original83/revoke | 2,485,484 → 2,485,137 | 47,923,200 → 48,152,576 |
| workflow/verify | 474,983 → 475,257 | 42,778,624 → 42,852,352 |
| workflow/create_revision | 544,026 → 544,090 | 42,569,728 → 42,655,744 |
| workflow/propose_baseline | 499,732 → 499,797 | 42,582,016 → 42,307,584 |
| workflow/approve | 501,988 → 502,206 | 42,434,560 → 42,442,752 |
| workflow/revoke | 506,549 → 506,307 | 42,872,832 → 42,754,048 |

## Drift, replay y controles nativos

Los mismos 15 objetos históricos / 1.200.017 bytes y los mismos PCAP/modelos
alimentan ambos lados. El reporte de 495.203 bytes tiene SHA y fuentes exactas
en `regression_inputs`. Se conserva `benchmarks.historical_regression`; los siete
digest de salida coinciden. No se agregaron sus ejecuciones a los casos pytest.

| Operación | Padre | Candidato |
|---|---|---|
| capture_observations | 0.007357 [0.007109–0.007899] | 0.007548 [0.007230–0.008417] |
| drift_comparison | 0.408428 [0.403621–0.408801] | 0.404326 [0.401435–0.409310] |
| native_comparison | 0.029943 [0.029464–0.031953] | 0.030219 [0.029444–0.031735] |
| protocol_enrichment | 0.006806 [0.006451–0.007221] | 0.006641 [0.006433–0.006804] |
| report_reproduction | 0.647109 [0.630313–0.657029] | 0.653268 [0.639878–0.669384] |
| revision_inspection | 0.382742 [0.381751–0.390155] | 0.386029 [0.381285–0.388100] |
| workspace_verification | 0.385674 [0.376060–0.386472] | 0.387173 [0.384617–0.396040] |

## Explorer histórico: publicaciones densas y replay

Se reutiliza `benchmarks.historical_explorer` con escalas 1/64/512. Preparación
fuera de latencia; mismos reportes, inventarios fuente y bundle IDs entre lados.
Los diez manifests por escala (warmup, tres tiempos y allocation por cada lado)
coinciden exactamente; se verificaron además todos sus hashes de archivos.
Replay, render puro y auditoría de enlaces tienen vectores separados en el
recibo compacto; no se suman como latencias independientes de una petición.

| Escala | HTML | Bytes contenido | Generación padre | Generación candidato | Pico Python separado B, padre → candidato |
|---|---:|---:|---|---|---:|
| 1 | 37 | 458,049 | 1.030564 [1.027685–1.059343] | 1.042687 [1.039703–1.100732] | 35,170,584 → 35,169,964 |
| 64 | 44 | 2,320,805 | 3.193673 [3.141020–3.294067] | 3.286069 [3.182541–3.346115] | 41,886,680 → 41,886,117 |
| 512 | 107 | 15,647,378 | 17.802466 [17.560532–17.829126] | 17.521083 [17.499574–17.771772] | 90,011,818 → 90,012,074 |

No se cambiaron layouts ni se exige otra auditoría visual. Los directorios
generados son evidencia de medición de la presentación aprobada existente.

## Interpretación y reproducción

Se retienen todos los rangos y filas más lentas. Con bytes de producción
idénticos, estas muestras no demuestran una mejora ni una regresión causada por
V14-05. No se hizo una optimización especulativa para mejorar un titular. No se
ampliaron ceilings ni se quitaron controles de fuente, aprobación o provenance.

Recibo compacto versionado: `benchmarks/receipts/v14-05-windows.json`.
Recibos completos: `output/v145/protocol-*.json`, `regression-*.json`,
`history-paired/performance.json`, `explorer-parent/benchmark.json` y
`explorer-candidate/benchmark.json`. El compacto conserva vectores primarios,
medianas/rangos, memoria, identidades y limitaciones; los workers/publicaciones
voluminosos permanecen ignorados. No contiene capturas externas.

Reproducir con directorios de salida **nuevos** y dos entornos regulares que
instalen los commits declarados; verificar primero sus inventarios. Usar el
mismo ejecutable CPython, versiones de dependencias y guard offline. En este
checkout ya existen los siguientes entornos; en otro, preparar instalaciones
regulares de esos commits y ajustar las dos variables:

```powershell
$parentPython = (Resolve-Path output/v145/parent-env/Scripts/python.exe).Path
$candidatePython = (Resolve-Path .venv/Scripts/python.exe).Path
$env:OTARCHGUARD_OFFLINE_CHECK = '1'
$env:PYTHONPATH = (Resolve-Path tools/offline).Path
& $parentPython -m benchmarks.protocol_regression --prepare --input output/recheck-protocol-inputs
& $parentPython -m benchmarks.protocol_regression --input output/recheck-protocol-inputs --output output/recheck-protocol-parent.json
& $candidatePython -m benchmarks.protocol_regression --input output/recheck-protocol-inputs --output output/recheck-protocol-candidate.json
# Reconstrucción pública del workload original; preparación fuera del timing pareado:
& $parentPython -m benchmarks.evidence_history --output output/recheck-original83 --collections 16 --revisions 16
& $candidatePython -m benchmarks.history_performance --output output/recheck-history --baseline-python $parentPython --optimized-python $candidatePython --baseline-commit d898516e24dec922179696e4cb50a262b3466a46 --optimized-commit e4d8234acd504ca30d6d0aef66f316b8cf1c86d0 --reference-workspace output/recheck-original83/history --scales --trials 3 --modes timing memory --operations verify create_revision propose_baseline approve revoke
& $parentPython -m benchmarks.historical_explorer --output output/recheck-explorer-parent --scales 1,64,512 --trials 3
& $candidatePython -m benchmarks.historical_explorer --output output/recheck-explorer-candidate --scales 1,64,512 --trials 3
```

`benchmarks.historical_regression` toma la misma selección de
`tools.drift_walkthrough.prepare(scale=64, variations=False)` para ambos lados;
crear su `report.json` con `compare`/`canonical` antes de medir. La selección y
los hashes exactos están en `regression_inputs`. Comparar primero identidades y
resultados antes de interpretar tiempos. La reproducción de nuevas mediciones
no exige que el reloj reproduzca estos números.
