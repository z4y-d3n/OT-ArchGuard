# V15-05 — Entrega de instalación y distribución

Estado inicial: candidato documental preparado; pendiente cerrar los resultados
locales de paquetes antes de emitir el veredicto de aceptación.

Inicio: `b62f816a88d8cf61e2798c368e8b277621b5d5bc`, árbol
`e2c4d35f57c4a2e8c0b6cf09f3aa93301ae9b8e4`. SHA/árbol finales y hashes de
archivos: recibo externo `output/v15-05/final/freeze.json`. Rama local:
`codex/v15-05-installation-distribution-docs`. Sin operaciones remotas de escritura.

Se corrigen la identidad dev1 obsoleta de instalación, el encabezado actual de
testing y la ambigüedad histórica del changelog. Se documentan build/audit e
instalación regular dev3, primer Explorer con ejemplo del sdist, recuperación,
wheelhouse por destino y límites del replay histórico. Se preservan Quick Start,
screenshot y assets estables v1.4.0. Cambian nueve Markdown y dos inventarios;
la [aceptación](v15-05-acceptance.md) enumera el alcance exacto.

Distribución/CLI `1.5.0.dev3`, motor `1.3.0`, schema `1`, 97 módulos y políticas
anteriores deben conservarse idénticos. Renderer separado:
`1.5.0.dev1-historical-explorer.1`. Documentación distinta cambia el sdist, no el
productor analítico. No se migran revisiones ni aprobaciones. Conservar runtime,
fuente y workspace originales para replay compatible; integridad portable no
autentica autoría ni prueba reproducción analítica.

Ver [matriz de instalación](v15-05-installation-matrix.md). El CI post-merge
V15-04 pasó las seis configuraciones ([run 41918807010](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/41918807010));
el CI del nuevo SHA queda pendiente. No confundir revisión estática POSIX con
ejecución, resolución local sin índice con desconexión física, ni guía estable
con una reinstalación estable recién realizada.

## Revisión y publicación de rama por el propietario

- Revisar diff, identidades finales, hashes y recibos; confirmar 97 módulos y
  verificadores sin cambios, inventarios completos y cero defectos bloqueantes.
- Revisar instrucciones y abrir el primer reporte ficticio local.
- Después de aceptar, publicar la rama y crear el PR desde GitHub en el navegador.
- Exigir las seis configuraciones del SHA exacto antes de integrar; ningún tag
  ni Release estable pertenece a este gate.

```powershell
Set-Location -LiteralPath 'C:\Users\PC\Desktop\OT-ArchGuard-CLEAN'
git status --short --branch
git diff --check
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git fetch --no-tags origin main
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
# Comparar SHA/árbol y archivos con output/v15-05/final/freeze.json.
# Si main avanzó, revisar integración y repetir los checks afectados.
git push --set-upstream origin codex/v15-05-installation-distribution-docs
```

Crear después el PR en [GitHub Compare](https://github.com/z4y-d3n/OT-ArchGuard/compare/main...codex/v15-05-installation-distribution-docs)
con base `main`, título «V15-05: Installation, packaging and documentation» y
descripción del alcance documental, verificaciones locales, límites y CI pendiente.
No se necesita GitHub CLI. Estos pasos son instrucciones para el propietario;
el agente no ejecutó push ni creó PR.

## Requisitos exactos de V15-06

Autorizar explícitamente el cambio estable a `1.5.0` y sus fuentes/versiones;
aceptar la fuente integrada exacta, las identidades de productor/replay y notas
finales. Verificar wheel/sdist completos e instalaciones regulares; revisar el
procedimiento de assembly estable y generar manifiesto/checksums. El guard
histórico v1.4.0 de `tools/prepare_release.py` permanece intacto en V15-05:
no habilitar dev3 debilitándolo. Completar CI de seis jobs del SHA final,
revisión del propietario y autorización independiente de publicación. Después
verificar tag y assets publicados. Documentar integridad frente a autenticidad;
ningún hash por sí solo autentica evidencia ni autoriza una Release.
