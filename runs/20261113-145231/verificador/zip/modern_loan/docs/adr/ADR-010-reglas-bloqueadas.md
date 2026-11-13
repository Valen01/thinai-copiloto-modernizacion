# ADR-010: Reglas bloqueadas (requieren revision)

## Estado
Bloqueada: requiere revision (no aplica en esta entrega).

## Contexto
`validador/reglas_limpias.json` contiene 45 reglas, todas con `estado_revision` `aprobada_po` (43 aprobadas
y 2 mejoradas por el PO); `diferencias_esperadas` esta vacio y no hay reglas rechazadas. No existe ninguna
regla en `requiere_revision_humana`, `pendiente` ni `corregida_pendiente_reaprobacion`.

## Decision
No hay reglas bloqueadas ni rechazadas que documentar. Si en una entrega futura aparecieran, se listarian
aqui sin implementarlas y sin cambiar su `estado_revision`.

## Consecuencias
Todas las reglas aprobadas estan implementadas con marcador `REGLA:` en codigo y pruebas, o justificadas
como no portadas en ADR-004.

## Reglas relacionadas
Ninguna bloqueada.
