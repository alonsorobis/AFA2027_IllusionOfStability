"""
Proyeccion de plan de pensiones privado: acumulacion 42 -> 67 y renta desde 67.

Todos los supuestos estan en el bloque PARAMETROS. Cambia UNA linea y se
recalcula todo. En particular APORT_NOMINA_T1 es el hueco donde va la
aportacion real que figure en la nomina (empresa + empleado).
"""

# ------------------------- PARAMETROS -------------------------
EDAD_HOY, EDAD_JUB = 42, 67
ANOS = EDAD_JUB - EDAD_HOY                 # 25 anos

SALDO_T1 = 115_000.0                       # saldo actual titular 1
SALDO_T2 = 5_500.0                         # saldo actual titular 2

APORT_NOMINA_T1 = 3_000.0                  # SUPUESTO: aportacion via nomina (empresa+empleado)/ano
APORT_VOL_T1 = 2_500.0                     # aportacion voluntaria extra /ano
APORT_VOL_T2 = 2_500.0                     # aportacion voluntaria titular 2 /ano

CREC_APORT = 0.02                          # las aportaciones suben 2%/ano (IPC/salario)
INFLACION = 0.02

RENT = {"Prudente": 0.03, "Central": 0.05, "Optimista": 0.07}
RENT_JUB = 0.03                            # rentabilidad del fondo ya jubilado (mas conservador)

PENSION_SS_MES = 2_500.0                   # pension publica estimada, 12 pagas equivalentes
EDAD_AGOTA = 90                            # la renta se consume hasta esta edad
# --------------------------------------------------------------


def acumular(saldo, aportacion, r, anos, crec=CREC_APORT):
    """Aportacion a fin de ano, creciente al ritmo `crec`."""
    for t in range(anos):
        saldo = saldo * (1 + r) + aportacion * (1 + crec) ** t
    return saldo


def renta_mensual(capital, r_anual, anos):
    """Renta financiera constante que agota el capital en `anos`."""
    i = (1 + r_anual) ** (1 / 12) - 1
    n = anos * 12
    return capital * i / (1 - (1 + i) ** -n)


def real(valor, anos, infl=INFLACION):
    return valor / (1 + infl) ** anos


anos_renta = EDAD_AGOTA - EDAD_JUB
ap_t1 = APORT_NOMINA_T1 + APORT_VOL_T1
ap_t2 = APORT_VOL_T2

print(f"Horizonte: {ANOS} anos de aportacion ({EDAD_HOY} -> {EDAD_JUB}), "
      f"renta durante {anos_renta} anos ({EDAD_JUB} -> {EDAD_AGOTA})")
print(f"Aportacion anual T1: {ap_t1:,.0f} EUR ({APORT_NOMINA_T1:,.0f} nomina + {APORT_VOL_T1:,.0f} voluntaria), "
      f"creciendo {CREC_APORT:.0%}/ano")
print(f"Aportacion anual T2: {ap_t2:,.0f} EUR\n")

filas = []
for nombre, r in RENT.items():
    c1 = acumular(SALDO_T1, ap_t1, r, ANOS)
    c2 = acumular(SALDO_T2, ap_t2, r, ANOS)
    tot = c1 + c2

    m1 = renta_mensual(c1, RENT_JUB, anos_renta)
    m2 = renta_mensual(c2, RENT_JUB, anos_renta)
    mt = m1 + m2

    aportado = SALDO_T1 + SALDO_T2 + sum(
        (ap_t1 + ap_t2) * (1 + CREC_APORT) ** t for t in range(ANOS))

    filas.append((nombre, r, c1, c2, tot, m1, m2, mt, aportado))

    print(f"--- Escenario {nombre} ({r:.0%} anual nominal) ---")
    print(f"  Capital T1 a los 67 : {c1:12,.0f} EUR   (en euros de hoy: {real(c1, ANOS):,.0f})")
    print(f"  Capital T2 a los 67 : {c2:12,.0f} EUR   (en euros de hoy: {real(c2, ANOS):,.0f})")
    print(f"  CAPITAL CONJUNTO    : {tot:12,.0f} EUR   (en euros de hoy: {real(tot, ANOS):,.0f})")
    print(f"  Total aportado      : {aportado:12,.0f} EUR  ->  rendimiento generado: {tot - aportado:,.0f}")
    print(f"  Renta mensual bruta hasta los {EDAD_AGOTA}: {mt:,.0f} EUR/mes "
          f"(T1 {m1:,.0f} + T2 {m2:,.0f})")
    print(f"     equivalente en euros de hoy        : {real(mt, ANOS):,.0f} EUR/mes")
    print(f"  INGRESO TOTAL JUBILADO (SS {PENSION_SS_MES:,.0f} + renta): "
          f"{PENSION_SS_MES + mt:,.0f} EUR/mes brutos\n")

print("=" * 78)
print("SENSIBILIDAD: capital conjunto a los 67 segun aportacion de nomina de T1")
print("=" * 78)
print(f"{'Nomina/ano':>12} | " + " | ".join(f"{n:>14}" for n in RENT))
for nom in (0, 1_500, 3_000, 4_500, 6_000, 8_500):
    fila = []
    for _, r in RENT.items():
        c = acumular(SALDO_T1, nom + APORT_VOL_T1, r, ANOS) + acumular(SALDO_T2, ap_t2, r, ANOS)
        fila.append(f"{c:14,.0f}")
    print(f"{nom:>12,} | " + " | ".join(fila))

print("\n" + "=" * 78)
print("DURACION DE LA RENTA (escenario Central) segun horizonte elegido")
print("=" * 78)
c_central = acumular(SALDO_T1, ap_t1, RENT["Central"], ANOS) + acumular(SALDO_T2, ap_t2, RENT["Central"], ANOS)
for edad_fin in (82, 85, 90, 95):
    n = edad_fin - EDAD_JUB
    m = renta_mensual(c_central, RENT_JUB, n)
    print(f"  Agotar a los {edad_fin} ({n:2d} anos): {m:8,.0f} EUR/mes brutos "
          f"({real(m, ANOS):6,.0f} en euros de hoy)  -> total con SS: {PENSION_SS_MES + m:,.0f}")
perp = c_central * RENT_JUB / 12
print(f"  Renta perpetua (solo rendimientos, capital intacto): {perp:,.0f} EUR/mes")
