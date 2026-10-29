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

La ventana de medición se reserva después del freeze y de la instalación regular
del candidato, sin suites concurrentes. Hasta disponer del recibo específico no
se afirma una nueva cifra de latencia, memoria, mejora o ausencia medida de
regresión. El ensayo acotado usa el mismo host y CPython 3.14.5, dependencias
equivalentes, inputs con hash, warmup excluido, cinco muestras y mediana/rango;
la memoria Python se observa en una ejecución separada. No mide una planta real,
un peor caso hostil ni memoria del hijo a partir del tracing del proceso padre.

El recibo definitivo y su lectura se incorporan aquí cuando el integrador abre
esa ventana. La comprobación de igualdad de fuentes ya está ejecutada; el ensayo
temporal queda explícitamente **pendiente**, no PASS.
