# V15-01 — Entrega al propietario

Documento de trabajo de desarrollo; v1.4.0 continúa como versión pública estable.
El veredicto y los resultados definitivos se completarán después de ejecutar la
verificación y la auditoría independiente. Esta nota provisional no declara
ningún control pendiente como aprobado.

## Identidades y alcance

Base limpia: `c5ada13871043ed52cd43557bc7b222399f7b7eb`, `main` con upstream
`origin/main`. Fuente publicada v1.4.0:
`7d6b158f863308dfcd7d10b673bfbe2692f29b8b`. Rama local:
`codex/v15-01-product-consolidation-foundation`. Distribución/CLI `1.4.0`, motor
nativo `1.3.0`, esquema YAML `1`. No se modifica la versión porque el verificador
actual fija los 97 módulos y sólo admite la transición histórica ya aprobada.
V15-02 deberá revisar expresamente una nueva transición antes de cambiar runtime.

## Cambios y auditorías

| Cambio | Motivo | Verificación |
|---|---|---|
| Preflight compartido de tres tutoriales históricos | Padre inexistente/destino ocupado producía traceback | Regresiones de salida 2, mensaje útil y preservación de datos |
| Requisitos de tutoriales y guía de instalación actual | Comandos incompletos desde sdist limpio y referencia 1.3.0 desactualizada | Revisión de enlaces y recorrido con paquete instalado |
| Trigger `codex/v15-*` | Publicar esta rama no activaría CI de push | YAML real, patrón de rama y matriz de seis jobs |

Agente A: arquitectura, contratos y fallo doble de E/S. Agente B: cuatro
recorridos, documentación y seis reproducciones de UX. Agente C: línea base
repetida con fixtures deterministas. Agente D: paquetes e instalaciones nuevas.
Agente E: revisión crítica independiente después de integrar. Sus conclusiones
y límites se detallan en los documentos del dossier.

## Contratos, límites y diferidos

No se cambian módulos de runtime, decodificadores, renderizadores, límites de
recursos, hashes históricos ni aprobaciones. Se conserva la operación pasiva,
offline y sin reensamblado TCP. No se han tocado assets publicados ni registros
de aceptación históricos.

La auditoría A reprodujo mediante inyección de fallos que un error al borrar un
temporal puede ocultar el diagnóstico de sustitución de reporte; el reporte
anterior se conserva. Es P2, diferido por el contrato de fuente congelada, sin
atribuir pérdida ordinaria de datos. El acoplamiento entre helpers privados
merece revisión posterior; no justifica un refactor general en este gate.

Las mediciones separan tiempo sin tracing, asignaciones de Python y RSS del
proceso. No hay optimización implementada ni promesa de aceleración.

## Revisión del propietario y Git

1. Inspeccionar el diff y este dossier; revisar los receipts y límites reales.
2. Abrir el primer reporte y los Explorers de captura/historia offline; comprobar
   teclado/foco, zoom 200%, ancho reducido, textos largos/IPv6 e impresión.
3. Publicar sólo la rama revisada si se acepta el trabajo; ejecutar los seis jobs
   del SHA exacto y exigir resultados reales antes de integrar.
4. Mantener entornos históricos compatibles y decisiones de aprobación separadas.

```powershell
git status --short --branch
git rev-parse HEAD
git log --oneline main..HEAD
git diff --stat main...HEAD
git diff main...HEAD
# Sólo el propietario, después de revisar:
git push -u origin codex/v15-01-product-consolidation-foundation
```

[Comparación para crear PR contra main](https://github.com/z4y-d3n/OT-ArchGuard/compare/main...codex/v15-01-product-consolidation-foundation?expand=1).
No se requiere GitHub CLI. Ninguna operación remota se ejecutará en este trabajo.

Objetivo recomendado V15-02: aprobar una transición de identidad/fuente de
desarrollo que conserve oráculos inmutables y límites de replay histórico,
antes de corregir runtime o introducir una versión 1.5 de desarrollo.
