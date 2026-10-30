# V14-06 — Alcance de la confirmación de rendimiento

La comparación se ancla al padre
`ac893bc3174f0a7ace67454d19ad6e61116425af`. No se realizó optimización de producción.
La inspección independiente de los 97 módulos encuentra exactamente un cambio:
el literal `DISTRIBUTION_VERSION` de `1.4.0.dev1` a `1.4.0` en `__init__.py`.

| Identidad | SHA-256 |
|---|---|
| `__init__.py` del padre | `970f736133968e77bee8b8675d01c70465c8fe441c368e6750d0cdf76e311525` |
| `__init__.py` con literal estable | `dfea43564e1416d2996e5007a29da17f2d97603f5883c48c9c3aec9f70a8289c` |

Los otros 96 módulos, incluidos parsers, motor nativo, lifecycle, drift y renderers,
conservan sus bytes. Los hashes completos y la clausura de dependencias están en
`output/v146/packaging-source-notices.json`, comparados con el snapshot inicial
inmutable. El integrador debe vincular esa observación al commit congelado y a
los módulos realmente instalados.

Por la regla de alcance del apartado 21 de la directiva, repetir toda la matriz
de benchmarks no reduce un riesgo adicional demostrado cuando sólo cambia la
identidad de distribución. Se conserva la evidencia comparada V14-05 y se limita
el ensayo nuevo a startup/versión, una evaluación nativa pequeña y un PCAP ficticio
con metadatos industriales. Las identidades de salida nativa deben ser exactas;
la salida `--version` debe diferir sólo en la distribución esperada.

## Ensayo acotado ejecutado

Freeze del candidato: `ab1ff34a7b7653ea3887f9db340b56666032e49f`.
Ambos paquetes están instalados regularmente y sus 97 hashes se comparan con un
`git archive` de su SHA explícito antes de medir. La clausura de 14 dependencias
de ejecución tiene exactamente las mismas versiones en ambos entornos.
El único módulo diferente es el literal de distribución indicado arriba.

La ventana se ejecutó después del freeze y la instalación, sin suites concurrentes,
en Windows 11 / CPython 3.14.5. Se excluye un warmup por fila; se registran cinco
muestras y mediana/rango mediante el harness existente `benchmarks.profile.measure`.
La observación de memoria usa una ejecución separada con tracemalloc. Startup
ejecuta la consola realmente instalada; no se mide memoria del hijo mediante
tracing del padre. Las mediciones terminan antes de iniciar las suites completas.

| Operación | Padre: mediana [mín–máx], s | Candidato: mediana [mín–máx], s | Pico Python separado, B padre → candidato | Bytes de salida |
|---|---|---|---|---:|
| Startup y `--version` | 0,726442 [0,723338–0,772349] | 0,729308 [0,717253–0,778482] | No medido en el hijo | Cambia sólo a `1.4.0` |
| Check nativo pequeño, lectura incluida | 0,011564 [0,011288–0,012273] | 0,011779 [0,011643–0,012775] | 5.375.322 → 5.375.322 | 8.879 |
| Observaciones PCAP ficticio | 0,004901 [0,004789–0,004982] | 0,005171 [0,004948–0,005387] | 190.316 → 190.316 | 22.158 |
| Enrichment del mismo PCAP | 0,005088 [0,004989–0,005324] | 0,005170 [0,004970–0,005591] | 187.246 → 187.246 | 25.669 |

Las tres salidas analíticas son idénticas por SHA-256 entre lados; check conserva
1 consulta atómica, 4 visitas de estado/arista y 1 comprobación regla/arista/átomo.
El modelo tiene hash `7eaeff84a657ddfb5b41ed81f74067bd3db86a310a16d83fee923e355ea2ce73`;
el PCAP V14-05, `9035464f34c6d2b45c528678b1f1d2af87b4d428b6707c395564239bfe0de3c2`.
El recibo conserva hashes exactos de salidas, tamaños, cinco muestras wall/CPU y
fuentes instaladas. Los límites y los contadores restantes conservan el código
del padre; no se repite aquí el estudio completo de techos o escalabilidad.

Los pequeños aumentos medidos se conservan en la tabla. No se atribuyen a una
regresión causal sin cambio de código analítico ni se presenta una mejora
universal. Los entornos se midieron secuencialmente, padre primero, con posible
sesgo de orden/caché. No se controlan frecuencia, temperatura ni otras aplicaciones.
El revisor independiente notificó una posible superposición con un sondeo de
metadatos en memoria de unos 1,5 segundos; no era una suite completa. Se conserva
esta actividad incidental como limitación de la ventana, sin atribuir diferencias
pequeñas al código ni presentar las cifras como un experimento aislado del SO.
El ensayo no mide una planta real, un peor caso hostil ni un límite universal
de RSS. Las muestras son una confirmación acotada, no una nueva garantía de capacidad.

## Recibos y reproducción

`output/v146/performance-parent.json`,
`output/v146/performance-candidate.json` y
`output/v146/performance-comparison.json` conservan la evidencia completa.
SHA-256 de los dos primeros recibos:
`2e7a893cde68466a9f72579a02becf77728c493cdf9ab3c0f1db0654ce7b5271` y
`390f37afd051bc8ca661b2a288b58b677a51604498508908a38e84b30cca0204`.
El worker acotado queda en `output/v146/performance_worker.py`; reutiliza
`benchmarks.profile.measure` y `tools.history_performance_worker.package_identity`.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'tools/offline')
$env:OTARCHGUARD_OFFLINE_CHECK = '1'
.venv/Scripts/python.exe -m output.v146.performance_worker `
  output/v146/performance-parent.json ac893bc3174f0a7ace67454d19ad6e61116425af
.venv-v146-wheel/Scripts/python.exe -m output.v146.performance_worker `
  output/v146/performance-candidate.json ab1ff34a7b7653ea3887f9db340b56666032e49f
```

Estos datos corresponden al freeze indicado. Una entrega documental posterior
puede conservar el resultado sólo si vuelve a demostrar igualdad de payload
ejecutable y dependencias; sus artefactos finales necesitan otra vinculación
exacta de fuente y paquete.
