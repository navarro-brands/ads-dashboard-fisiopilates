#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador del Centro de Comando Meta Ads · FisioPilates (Navarro Brand Builders).

Lee los CSV semanales exportados desde Meta Ads Manager (nivel anuncio, últimos 7 días)
y escribe `assets/data.js` con todo lo que renderizan las páginas HTML.

Uso semanal:
  1. Exportar el CSV de la semana a CSV_DIR con nombre único (NBB-Informe-<rango>.csv).
  2. Añadir la semana a WEEKS con su alcance deduplicado (Meta > Informes) por estrategia.
  3. Actualizar ACC_REACH (acumulado deduplicado por estrategia, hasta el fin de la semana).
  4. python build.py   →  regenera assets/data.js y valida los rollups.
  5. Redactar los comentarios del analista en comments.json y hacer commit.

Reglas de datos (ver README):
  - Aditivas: inversión, impresiones, conversaciones, clics. Derivadas: CPC, CTR, costo/conv.
  - NO aditiva: ALCANCE. El alcance real deduplicado solo viene de Meta Informes y se fija a mano.
    El alcance sumado por sede/anuncio/conjunto se etiqueta "aprox." en las páginas.
  - Conversaciones = columna "Conversaciones con mensajes iniciadas" (WhatsApp). En las campañas
    NBB la columna "Resultados" cuenta "Clientes potenciales" (objetivo distinto), por eso NO se usa.
"""
import csv, io, json, os, sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.environ.get("NBB_CSV_DIR",
    r"C:\Users\nesto\OneDrive\Documentos\Proyectos Marketing\Navarro\FisioPilates")
OUT = os.path.join(HERE, "assets", "data.js")
COMMENTS = os.path.join(HERE, "comments.json")

# ───────────────────────── Configuración semanal ─────────────────────────
# reach = alcance deduplicado de Meta Informes para ese rango, por estrategia.
# "trad" = pauta tradicional (12 campañas por sede), "nbb" = estrategia NBB (3 campañas por audiencia).
# Hasta la semana 9 solo existía la pauta tradicional, por eso trad == cuenta.
# OJO: el informe de alcance de la pauta tradicional debe filtrarse a las campañas «CO |». Las cifras de las
# semanas 10 y 11 llegaron sin filtrar (eran de cuenta completa: 109.335 y 96.342) y se corrigieron el 29 sep.
WEEKS = [
    dict(id="w1",  file="NBB-Informe-sem1.csv",        label="29 jun–5 jul",  start="2026-06-29", end="2026-07-05", reach=dict(trad=61159)),
    dict(id="w2",  file="NBB-Informe-6_12jul.csv",     label="6–12 jul",      start="2026-07-06", end="2026-07-12", reach=dict(trad=75473)),
    dict(id="w3",  file="NBB-Informe-13_19jul.csv",    label="13–19 jul",     start="2026-07-13", end="2026-07-19", reach=dict(trad=90849)),
    dict(id="w4",  file="NBB-Informe-20_26jul.csv",    label="20–26 jul",     start="2026-07-20", end="2026-07-26", reach=dict(trad=70064)),
    dict(id="w5",  file="NBB-Informe-27jul_2ago.csv",  label="27 jul–2 ago",  start="2026-07-27", end="2026-08-02", reach=dict(trad=69807)),
    dict(id="w6",  file="NBB-Informe-3_9ago.csv",      label="3–9 ago",       start="2026-08-03", end="2026-08-09", reach=dict(trad=65333)),
    dict(id="w7",  file="NBB-Informe-10_16ago.csv",    label="10–16 ago",     start="2026-08-10", end="2026-08-16", reach=dict(trad=89993)),
    dict(id="w8",  file="NBB-Informe-17_23ago.csv",    label="17–23 ago",     start="2026-08-17", end="2026-08-23", reach=dict(trad=77852)),
    dict(id="w9",  file="NBB-Informe-24_30ago.csv",    label="24–30 ago",     start="2026-08-24", end="2026-08-30", reach=dict(trad=78596)),
    dict(id="w10", file="NBB-Informe-31ago_6sep.csv",  label="31 ago–6 sep",  start="2026-08-31", end="2026-09-06", reach=dict(trad=86923,  nbb=28736)),
    dict(id="w11", file="NBB-Informe-7_14sep.csv",     label="7–13 sep",      start="2026-09-07", end="2026-09-13", reach=dict(trad=71683,  nbb=31681)),
    # Desde la semana 12 el export llega separado: un CSV con la pauta tradicional y otro con NBB.
    dict(id="w12", files=["NBB-Informe-14_20sep.csv", "Ads NBB/NBB SEM 3 - 14 al 20 SEP 2026.csv"],
         label="14–20 sep", start="2026-09-14", end="2026-09-20", reach=dict(trad=66424, nbb=36232)),
    dict(id="w13", files=["NBB-Informe-21_27sep.csv", "Ads NBB/NBB SEM 4 - 21 al 27 SEP 2026.csv"],
         label="21–27 sep", start="2026-09-21", end="2026-09-27", reach=dict(trad=67905, nbb=46811)),
]
# Alcance deduplicado acumulado (Meta Informes) al cierre de la última semana.
#   trad: 29 jun → fin de la última semana.  nbb: 31 ago → fin de la última semana.
ACC_REACH = dict(trad=358818, nbb=99378)
# Alcance deduplicado de la pauta tradicional SOLO en la ventana común con NBB (31 ago → fin de la última semana).
# Sirve para comparar alcance/frecuencia entre estrategias en el acumulado; opcional.
TRAD_WINDOW_REACH = None
# Registro histórico de acumulados anteriores (solo documental, no se renderiza):
#   trad 29 jun–30 ago: 318722 · 29 jun–6 sep: 357415 (*) · 29 jun–13 sep: 384849 (*) · 29 jun–20 sep: 342719
#   nbb  31 ago–13 sep: 51079 · 31 ago–20 sep: 73076
#   (*) Los cortes del 6 y el 13 de septiembre se tomaron sin filtrar las campañas NBB, así que corresponden a
#       la CUENTA COMPLETA y no a la pauta tradicional sola. No son comparables con los cortes posteriores
#       (20 sep: 342719 y 27 sep: 358818), ya tomados solo sobre las campañas «CO |».

NBB_START = "w10"              # primera semana con la estrategia NBB
PERIODS_SHOWN = ["w12", "w13"] # semanas seleccionables en el toggle (además del acumulado)
CUR = "w13"                    # semana por defecto

# ───────────────────────── Nomenclatura ─────────────────────────
# Campañas de la pauta tradicional → sede canónica. Todo lo que NO esté aquí y empiece por "NBB |"
# se trata como estrategia NBB. Cualquier otra campaña detiene el build (hay que clasificarla).
TRAD_CAMPAIGNS = {
    "CO | Colina - Mazuren | Ventas Whatsapp \u202a- 320 8174583": "Colina - Mazuren",
    "CO | El Contador | Ventas Whatsapp 3204049016":                "El Contador",
    "CO | Salitre | Ventas Whatsapp - 3222415254":                  "Salitre",
    "CO | Bulevar | Ventas Whatsapp  3108633424":                   "Bulevar",
    "CO | Av. El Dorado | Ventas Whatsapp - 3114455348":            "Av. El Dorado",
    "CO | Ventas Whatsapp | Sede Calle 119 3235115682":             "Calle 119",
    "CO | Cedro Golf | Ventas Whatsapp 3204133677":                 "Cedro Golf",
    "CO | Ventas Whatsapp | Santa Bárbara - 3227685819":            "Santa Bárbara",
    "CO | Chicó Norte | Ventas Whatsapp - 3235137959":              "Chicó Norte",
    "CO | Ventas Whatsapp | Remarketing 311 647 7233":              "Remarketing",
    "CO | Cedritos | Ventas Whatsapp \u202a323 5213734\u202c -":    "Cedritos",
    "CO | El Carmel | Ventas Whatsapp - 3204040149":                "El Carmel",
}
# Conjuntos NBB: "Sucursal <Sede> | <edad> | WA <tel>" → sede canónica (misma lista que arriba).
NBB_SEDES = {
    "Colina Mazuren": "Colina - Mazuren", "Colina Mauzuren": "Colina - Mazuren",
    "Contador": "El Contador", "Salitre Oriental": "Salitre", "Bulevar": "Bulevar",
    "Av. El Dorado": "Av. El Dorado", "Calle 119": "Calle 119", "Cedro Golf": "Cedro Golf",
    "Santa Bárbara": "Santa Bárbara", "Chico Norte": "Chicó Norte", "Cedritos": "Cedritos",
    "Carmel": "El Carmel",
}
# Campañas NBB → audiencia. Se clasifica por el 2º segmento del nombre ("NBB | <Audiencia> | ..."), así una
# campaña duplicada con otro objetivo (p. ej. "NBB | Adulto Mayor | Mensajes WhatsApp") cae en la misma audiencia.
NBB_AUDIENCES = {
    "Adulto Mayor":  dict(key="mayor", name="Adulto Mayor",            age="55–85"),
    "Dolor Crónico": dict(key="dolor", name="Dolor Crónico y Post-Q",  age="25–65"),
    "Adulto Joven":  dict(key="joven", name="Adulto Joven Preventivo", age="35–50"),
}
def nbb_audience(campaign):
    parts = [p.strip() for p in campaign.split("|")]
    if len(parts) >= 3 and parts[0] == "NBB" and parts[1] in NBB_AUDIENCES:
        return NBB_AUDIENCES[parts[1]]
    return None
SEDE_ORDER = ["Colina - Mazuren", "El Contador", "Salitre", "Bulevar", "Av. El Dorado", "Calle 119",
              "Cedro Golf", "Santa Bárbara", "Chicó Norte", "Cedritos", "El Carmel", "Remarketing"]

CONV_TYPE = "Conversaciones con mensajes iniciadas"


# ───────────────────────── Lectura ─────────────────────────
def num(v, f=float):
    v = (v or "").strip()
    return f(float(v)) if v not in ("", "-") else 0

def week_files(w):
    """Una semana puede venir en un solo CSV (ambas estrategias) o repartida en varios."""
    return w["files"] if isinstance(w.get("files"), list) else [w["file"]]

def read_week(w):
    raw = []
    for f in week_files(w):
        with open(os.path.join(CSV_DIR, f), encoding="utf-8-sig") as fh:
            part = list(csv.DictReader(io.StringIO(fh.read())))
        # Sanidad: el rango de cada archivo debe coincidir con la semana declarada.
        rng = {(r["Inicio del informe"], r["Fin del informe"]) for r in part}
        if rng != {(w["start"], w["end"])}:
            sys.exit(f"[{f}] El rango del CSV {rng} no coincide con la semana {w['start']}–{w['end']}")
        raw += part
    # Si la misma fila (campaña/conjunto/anuncio) llega por dos archivos, se contaría doble.
    keys = [(r["Nombre de la campaña"], r["Nombre del conjunto de anuncios"], r["Nombre del anuncio"]) for r in raw]
    if len(keys) != len(set(keys)):
        dup = [k for k, n in __import__("collections").Counter(keys).items() if n > 1][:3]
        sys.exit(f"[{w['id']}] Filas duplicadas entre los CSV de la semana: {dup}")
    rows = []
    for r in raw:
        camp = r["Nombre de la campaña"].strip()
        if "Conversaciones con mensajes iniciadas" in r:
            conv = num(r["Conversaciones con mensajes iniciadas"], int)
        else:  # exports antiguos (semana 1): solo "Resultados" tipificados
            conv = num(r["Resultados"], int) if r["Tipo de resultado"] == CONV_TYPE else 0
        row = dict(
            week=w["id"], campaign=camp, adset=r["Nombre del conjunto de anuncios"].strip(),
            ad=r["Nombre del anuncio"].strip(), status=r["Estado de la entrega"],
            spend=num(r["Importe gastado (COP)"]), imp=num(r["Impresiones"], int),
            reach=num(r["Alcance"], int), clicks=num(r["Clics en el enlace"], int), conv=conv,
            q=r.get("Clasificación de calidad", "-"), qctr=r.get("Clasificación del porcentaje de interacción", "-"),
            qcvr=r.get("Clasificación del porcentaje de conversiones", "-"),
        )
        if camp in TRAD_CAMPAIGNS:
            row.update(strategy="trad", sede=TRAD_CAMPAIGNS[camp], audience=None, age=None)
        elif nbb_audience(camp):
            a = nbb_audience(camp)
            parts = [p.strip() for p in row["adset"].split("|")]
            sede_raw = parts[0].replace("Sucursal", "").strip()
            if sede_raw not in NBB_SEDES:
                sys.exit(f"[{w['id']}] Conjunto NBB con sede desconocida: {row['adset']!r}")
            row.update(strategy="nbb", sede=NBB_SEDES[sede_raw], audience=a["key"],
                       age=parts[1].replace("Años", "").strip() if len(parts) > 1 else a["age"])
        else:
            sys.exit(f"[{w['id']}] Campaña no clasificada (¿nueva nomenclatura?): {camp!r}")
        # Se incluyen filas sin entrega/archivadas si tuvieron gasto o resultados (decisión NBB).
        if row["spend"] or row["conv"] or row["imp"]:
            rows.append(row)
    return rows


# ───────────────────────── Agregación ─────────────────────────
def derive(d):
    d["spend"] = round(d["spend"])
    d["cpconv"] = round(d["spend"] / d["conv"]) if d["conv"] else 0
    d["cpc"] = round(d["spend"] / d["clicks"]) if d["clicks"] else 0
    d["ctr"] = round(d["clicks"] / d["imp"] * 100, 2) if d["imp"] else 0
    d["cpm"] = round(d["spend"] / d["imp"] * 1000) if d["imp"] else 0
    d["conv_per_100k"] = round(d["conv"] / d["spend"] * 100000, 1) if d["spend"] else 0
    return d

def blank():
    return dict(spend=0.0, conv=0, imp=0, reach=0, clicks=0)

def add(acc, r):
    for k in ("spend", "conv", "imp", "reach", "clicks"):
        acc[k] += r[k]

def group(rows, keyfn, extra=None):
    """Agrupa filas por keyfn → lista de dicts con métricas derivadas, frecuencia aprox. y conteos."""
    g = OrderedDict()
    for r in rows:
        k = keyfn(r)
        if k not in g:
            g[k] = dict(blank(), _rows=[])
        add(g[k], r); g[k]["_rows"].append(r)
    out = []
    for k, d in g.items():
        rs = d.pop("_rows")
        derive(d)
        d["freq"] = round(d["imp"] / d["reach"], 2) if d["reach"] else 0
        d["ads"] = len({(r["campaign"], r["adset"], r["ad"]) for r in rs})
        d["sets"] = len({(r["campaign"], r["adset"]) for r in rs})
        d["below_q"] = sum(1 for r in rs if "debajo" in r["q"])
        d["tot_q"] = sum(1 for r in rs if r["q"] not in ("", "-"))
        d["below_ctr"] = sum(1 for r in rs if "debajo" in r["qctr"])
        d["below_cvr"] = sum(1 for r in rs if "debajo" in r["qcvr"])
        if extra:
            d.update(extra(k, rs))
        out.append(d)
    return out

def totals(rows, reach):
    t = blank(); [add(t, r) for r in rows]
    derive(t)
    t["reach_sum"] = t["reach"]                    # suma de filas (aprox., doble cuenta)
    t["reach"] = reach                             # deduplicado Meta Informes (puede ser None)
    t["freq"] = round(t["imp"] / reach, 2) if reach else None
    t["campaigns"] = len({r["campaign"] for r in rows})
    t["sets"] = len({(r["campaign"], r["adset"]) for r in rows})
    t["ads"] = len({(r["campaign"], r["adset"], r["ad"]) for r in rows})
    return t

def build_ads(rows, partkey):
    """Agrupa por nombre de anuncio; `partkey(r)` define el desglose (campaña/sede o audiencia)."""
    out = []
    byad = OrderedDict()
    for r in rows:
        byad.setdefault(r["ad"], []).append(r)
    for ad, rs in byad.items():
        d = blank(); [add(d, r) for r in rs]; derive(d)
        d["freq"] = round(d["imp"] / d["reach"], 2) if d["reach"] else 0
        parts = OrderedDict()
        for r in rs:
            k = partkey(r)
            if k not in parts:
                parts[k] = dict(blank(), **{kk: vv for kk, vv in k})
            add(parts[k], r)
        d["parts"] = sorted([derive(p) for p in parts.values()], key=lambda p: -p["spend"])
        d["ad"] = ad; d["campaigns"] = len(parts)
        out.append(d)
    return sorted(out, key=lambda a: -a["spend"])

def period_trad(rows, label, start, end, reach):
    camps = group(rows, lambda r: r["campaign"], lambda k, rs: dict(campaign=k, sede=rs[0]["sede"]))
    camps.sort(key=lambda c: -c["spend"])
    ads = build_ads(rows, lambda r: (("campaign", r["campaign"]), ("sede", r["sede"])))
    return dict(label=label, start=start, end=end, totals=totals(rows, reach), campaigns=camps, ads=ads)

def period_nbb(rows, label, start, end, reach):
    aud_names = {v["key"]: v for v in NBB_AUDIENCES.values()}
    audiences = group(rows, lambda r: r["audience"],
                      lambda k, rs: dict(audience=k, name=aud_names[k]["name"], age=aud_names[k]["age"],
                                         by_sede=[derive(dict(blank_add(rs2), sede=s)) for s, rs2 in by(rs, "sede")],
                                         by_ad=[derive(dict(blank_add(rs2), ad=s)) for s, rs2 in by(rs, "ad")]))
    sedes = group(rows, lambda r: r["sede"],
                  lambda k, rs: dict(sede=k, by_audience=[derive(dict(blank_add(rs2), audience=s, name=aud_names[s]["name"]))
                                                          for s, rs2 in by(rs, "audience")]))
    sedes.sort(key=lambda s: SEDE_ORDER.index(s["sede"]))
    sets = group(rows, lambda r: (r["audience"], r["sede"]),
                 lambda k, rs: dict(audience=k[0], name=aud_names[k[0]]["name"], sede=k[1], age=rs[0]["age"], adset=rs[0]["adset"]))
    for s in sets: s["key"] = f"{s['audience']}|{s['sede']}"
    ads = build_ads(rows, lambda r: (("audience", r["audience"]), ("name", aud_names[r["audience"]]["name"])))
    return dict(label=label, start=start, end=end, totals=totals(rows, reach), audiences=audiences,
                sedes=sedes, sets=sets, ads=ads)

def by(rs, key):
    g = OrderedDict()
    for r in rs: g.setdefault(r[key], []).append(r)
    return sorted(g.items(), key=lambda kv: -sum(r["spend"] for r in kv[1]))

def blank_add(rs):
    d = blank(); [add(d, r) for r in rs]; return d

def slim_trad(p):
    """Semana previa para deltas: totales + campañas indexadas por nombre."""
    return dict(totals=p["totals"], campaigns={c["campaign"]: c for c in p["campaigns"]})

def slim_nbb(p):
    return dict(totals=p["totals"], audiences={a["audience"]: a for a in p["audiences"]},
                sedes={s["sede"]: s for s in p["sedes"]}, sets={s["key"]: s for s in p["sets"]},
                ads={a["ad"]: a for a in p["ads"]})

def trend_point(w, rows, reach):
    t = totals(rows, reach)
    return dict(id=w["id"], label=w["label"], start=w["start"], end=w["end"],
                **{k: t[k] for k in ("spend", "conv", "cpconv", "reach", "clicks", "imp", "ctr", "cpc", "freq", "ads")})


# ───────────────────────── Validaciones ─────────────────────────
def check_rollup(name, tot, groups):
    for k in ("spend", "conv", "imp", "clicks"):
        s = sum(g[k] for g in groups)
        if abs(s - tot[k]) > 1:
            sys.exit(f"[{name}] rollup {k}: grupos={s} vs totales={tot[k]}")

def main():
    weeks = {w["id"]: w for w in WEEKS}
    rows_by_week = {w["id"]: read_week(w) for w in WEEKS}
    ids = [w["id"] for w in WEEKS]
    nbb_ids = ids[ids.index(NBB_START):]

    trad_rows = {i: [r for r in rows_by_week[i] if r["strategy"] == "trad"] for i in ids}
    nbb_rows = {i: [r for r in rows_by_week[i] if r["strategy"] == "nbb"] for i in ids}
    for i in ids[:ids.index(NBB_START)]:
        assert not nbb_rows[i], f"{i}: hay filas NBB antes de {NBB_START}"

    # ── Pauta tradicional ──
    trad = dict(periods=OrderedDict(), trend=[])
    for i in ids:
        trad["trend"].append(trend_point(weeks[i], trad_rows[i], weeks[i]["reach"]["trad"]))
    for i in PERIODS_SHOWN:
        w = weeks[i]
        p = period_trad(trad_rows[i], w["label"], w["start"], w["end"], w["reach"]["trad"])
        prev_id = ids[ids.index(i) - 1]
        wp = weeks[prev_id]
        p["prev"] = slim_trad(period_trad(trad_rows[prev_id], wp["label"], wp["start"], wp["end"], wp["reach"]["trad"]))
        p["prev"]["label"] = wp["label"]
        trad["periods"][i] = p
    all_trad = [r for i in ids for r in trad_rows[i]]
    trad["periods"]["acc"] = period_trad(all_trad, f"Acumulado ({WEEKS[0]['label'].split('–')[0]} – {WEEKS[-1]['label'].split('–')[1]})",
                                         WEEKS[0]["start"], WEEKS[-1]["end"], ACC_REACH["trad"])
    trad["periods"]["acc"]["prev"] = None
    trad["periods"]["acc"]["weeks"] = len(ids)
    trad["periods"]["acc"]["reach_weekly_sum"] = sum(weeks[i]["reach"]["trad"] for i in ids)

    # ── Estrategia NBB ──
    nbb = dict(periods=OrderedDict(), trend=[], start=weeks[NBB_START]["start"], start_label=weeks[NBB_START]["label"])
    for i in nbb_ids:
        nbb["trend"].append(trend_point(weeks[i], nbb_rows[i], weeks[i]["reach"].get("nbb")))
    for i in PERIODS_SHOWN:
        if i not in nbb_ids: continue
        w = weeks[i]
        p = period_nbb(nbb_rows[i], w["label"], w["start"], w["end"], w["reach"].get("nbb"))
        j = nbb_ids.index(i)
        if j > 0:
            wp = weeks[nbb_ids[j - 1]]
            p["prev"] = slim_nbb(period_nbb(nbb_rows[wp["id"]], wp["label"], wp["start"], wp["end"], wp["reach"].get("nbb")))
            p["prev"]["label"] = wp["label"]
        else:
            p["prev"] = None
        nbb["periods"][i] = p
    all_nbb = [r for i in nbb_ids for r in nbb_rows[i]]
    nbb["periods"]["acc"] = period_nbb(all_nbb, f"Acumulado ({weeks[NBB_START]['label'].split('–')[0]} – {WEEKS[-1]['label'].split('–')[1]})",
                                       weeks[NBB_START]["start"], WEEKS[-1]["end"], ACC_REACH.get("nbb"))
    nbb["periods"]["acc"]["prev"] = None
    nbb["periods"]["acc"]["weeks"] = len(nbb_ids)
    nbb["periods"]["acc"]["reach_weekly_sum"] = sum((weeks[i]["reach"].get("nbb") or 0) for i in nbb_ids)

    # ── Comparativa: misma ventana (desde NBB_START) para la pauta tradicional ──
    trad_window_rows = [r for i in nbb_ids for r in trad_rows[i]]
    compare = dict(
        window=dict(start=weeks[NBB_START]["start"], end=WEEKS[-1]["end"], weeks=len(nbb_ids),
                    label=f"{weeks[NBB_START]['label'].split('–')[0]} – {WEEKS[-1]['label'].split('–')[1]}"),
        trad_window=totals(trad_window_rows, TRAD_WINDOW_REACH),
        # línea base histórica: pauta tradicional antes de que arrancara NBB (semanas 1–9)
        trad_baseline=dict(totals([r for i in ids[:ids.index(NBB_START)] for r in trad_rows[i]], None),
                           weeks=ids.index(NBB_START),
                           label=f"{WEEKS[0]['label'].split('–')[0]} – {weeks[ids[ids.index(NBB_START)-1]]['label'].split('–')[1]}"),
        by_sede={},
        account_trend=[],
    )
    # por sede, por período (semanas mostradas + ventana común)
    def sede_split(trows, nrows):
        out = OrderedDict()
        for s in SEDE_ORDER:
            t = derive(blank_add([r for r in trows if r["sede"] == s]))
            n = derive(blank_add([r for r in nrows if r["sede"] == s]))
            if t["spend"] or n["spend"]:
                out[s] = dict(sede=s, trad=t, nbb=n)
        return list(out.values())
    for i in PERIODS_SHOWN:
        if i in nbb_ids:
            compare["by_sede"][i] = sede_split(trad_rows[i], nbb_rows[i])
    compare["by_sede"]["acc"] = sede_split(trad_window_rows, all_nbb)
    for i in ids:
        t = totals(trad_rows[i], weeks[i]["reach"]["trad"]); n = totals(nbb_rows[i], weeks[i]["reach"].get("nbb"))
        both = derive(blank_add(rows_by_week[i]))
        compare["account_trend"].append(dict(id=i, label=weeks[i]["label"],
            spend=both["spend"], conv=both["conv"], cpconv=both["cpconv"],
            trad=dict(spend=t["spend"], conv=t["conv"], cpconv=t["cpconv"], ctr=t["ctr"]),
            nbb=dict(spend=n["spend"], conv=n["conv"], cpconv=n["cpconv"], ctr=n["ctr"]) if n["spend"] else None))

    # ── Validaciones ──
    for i, p in trad["periods"].items():
        check_rollup(f"trad {i} campañas", p["totals"], p["campaigns"])
        check_rollup(f"trad {i} anuncios", p["totals"], p["ads"])
        for a in p["ads"]: check_rollup(f"trad {i} ad {a['ad']}", a, a["parts"])
    for i, p in nbb["periods"].items():
        for grp in ("audiences", "sedes", "sets", "ads"):
            check_rollup(f"nbb {i} {grp}", p["totals"], p[grp])
        for a in p["audiences"]:
            check_rollup(f"nbb {i} aud {a['audience']} sedes", a, a["by_sede"])
            check_rollup(f"nbb {i} aud {a['audience']} ads", a, a["by_ad"])
        for s in p["sedes"]: check_rollup(f"nbb {i} sede {s['sede']}", s, s["by_audience"])
    for i in ids:
        both = derive(blank_add(rows_by_week[i]))
        tt, nn = trad["trend"][ids.index(i)], (nbb["trend"][nbb_ids.index(i)] if i in nbb_ids else None)
        assert abs(tt["spend"] + (nn["spend"] if nn else 0) - both["spend"]) <= 1, f"{i}: trad+nbb != cuenta"
    acc = trad["periods"]["acc"]
    if acc["totals"]["reach"] and acc["reach_weekly_sum"] <= acc["totals"]["reach"]:
        sys.exit("trad: la suma de alcances semanales debería superar el acumulado deduplicado")
    nacc = nbb["periods"]["acc"]
    if nacc["totals"]["reach"] and nacc["reach_weekly_sum"] <= nacc["totals"]["reach"] and len(nbb_ids) > 1:
        sys.exit("nbb: la suma de alcances semanales debería superar el acumulado deduplicado")
    missing = [i for i in nbb_ids if weeks[i]["reach"].get("nbb") is None]
    if missing or ACC_REACH.get("nbb") is None:
        print(f"AVISO: falta alcance deduplicado NBB para {missing or ''} {'y acumulado' if ACC_REACH.get('nbb') is None else ''} → se mostrará como pendiente.")

    comments = json.load(open(COMMENTS, encoding="utf-8")) if os.path.exists(COMMENTS) else {}
    data = dict(
        generated=__import__("datetime").date.today().isoformat(),
        cur=CUR, periods_shown=PERIODS_SHOWN, nbb_start=NBB_START,
        weeks=[dict(id=w["id"], label=w["label"], start=w["start"], end=w["end"]) for w in WEEKS],
        sedes=SEDE_ORDER, audiences=[dict(key=v["key"], name=v["name"], age=v["age"]) for v in NBB_AUDIENCES.values()],
        trad=trad, nbb=nbb, compare=compare, comments=comments,
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("// Generado por build.py — NO editar a mano.\nconst DATA = ")
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    # Resumen en consola
    print(f"OK → {os.path.relpath(OUT, HERE)} ({os.path.getsize(OUT)//1024} KB)")
    for name, strat in (("TRAD", trad), ("NBB", nbb)):
        for i, p in strat["periods"].items():
            t = p["totals"]
            print(f"  {name:4} {i:4} {p['label']:<30} inv {t['spend']:>10,} · conv {t['conv']:>5} · c/conv {t['cpconv']:>6,} · CTR {t['ctr']}% · alcance {t['reach']} · frec {t['freq']}")

if __name__ == "__main__":
    main()
