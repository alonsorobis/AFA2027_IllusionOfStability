# Proyección de plan de pensiones (42 → 67)

Ejercicio de escenarios sobre la acumulación de un plan de pensiones privado y la
renta que puede pagar desde la jubilación.

## Archivos

- `proyeccion_pension.py` — el modelo. Todos los supuestos están en el bloque
  `PARAMETROS` al principio del archivo; cambiar una constante y volver a ejecutar
  recalcula los tres escenarios, la tabla de sensibilidad y la de duración de la renta.
- `resultados.txt` — salida de la última ejecución.
- `informe_pension.html` — el informe presentable con las mismas cifras.

## Uso

```
python3 personal/pension/proyeccion_pension.py
```

## Supuesto pendiente de confirmar

`APORT_NOMINA_T1` (aportación anual al plan de empleo, empresa + empleado) está
fijada en 3.000 € como supuesto. Es el único dato que debe sustituirse por la
cifra real de la nómina. La tabla de sensibilidad cubre el rango de 0 a 8.500 €.

## Alcance

Cálculo determinista con rentabilidad constante y aportaciones a fin de año.
No incorpora fiscalidad del rescate ni volatilidad de mercado. Es un ejercicio de
proyección, no asesoramiento financiero.
