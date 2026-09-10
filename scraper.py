#!/usr/bin/env python3
"""
scraper.py — Actualiza products.json a partir del catálogo de callback.vart.com.ar

Qué hace:
1. Descarga la página del catálogo (todas las marcas, todos los productos).
2. Convierte el HTML a texto tipo "markdown" (mismo formato prolijo que se ve al
   leer la página) para poder parsear cada producto con expresiones regulares,
   sin depender de nombres de clases CSS que pueden cambiar.
3. Filtra SOLO calzado: zapatillas, zapatos, ojotas, sandalias, botas, botines,
   zuecos, mocasines, pantuflas, alpargatas, etc. Descarta indumentaria y
   accesorios (mochilas, gorras, billeteras, jibbitz, medias, etc.).
4. Guarda todo en products.json, listo para que lo lea index.html.

Requisitos:
    pip install requests markdownify

Uso manual:
    python scraper.py

Para que el catálogo se actualice solo, programá este script para que corra
cada X tiempo (ver instrucciones al final de README.md).
"""

import json
import re
import sys
from datetime import datetime, timezone

import requests
from markdownify import markdownify as html_to_md

CATALOG_URL = "https://callback.vart.com.ar/catalogo.php?marca=&q=&min_u=&min_t=&orden=marca"
OUTPUT_FILE = "products.json"

# ---------------------------------------------------------------------------
# Clasificación: qué se considera "calzado" y qué se descarta.
# Editá estas listas de palabras clave si ves productos mal clasificados.
# ---------------------------------------------------------------------------

FOOTWEAR_KEYWORDS = [
    "zapatilla", "zapato", "sandalia", "ojota", "bota", "borcego", "borcegui",
    "zueco", "mocasin", "mocasín", "chancla", "chinela", "pantufla",
    "pantuflona", "alpargata", "gomon", "botin", "botín", "slide", "flip",
]

EXCLUDE_KEYWORDS = [
    "mochila", "billetera", "cartera", "gorra", "gorro", "jibbitz", "pin",
    "prendedor", "remera", "campera", "buzo", "media", "calcetin",
    "calcetín", "cinturon", "cinturón", "bolso", "riñonera", "termo",
    "botella", "caja",  # "Caja X" en la lista de marcas suele ser accesorios/embalaje
]


def is_footwear(name: str, desc: str) -> bool:
    text = f"{name} {desc}".lower()
    if any(bad in text for bad in EXCLUDE_KEYWORDS):
        return False
    return any(good in text for good in FOOTWEAR_KEYWORDS)


# ---------------------------------------------------------------------------
# Parseo
# ---------------------------------------------------------------------------

# Cada producto en el texto convertido queda con esta forma:
#
# ![](IMG_URL)
#
# CODIGO
#
# [Nombre del producto](LINK)
#
# Color · Modelo · Genero
#
# **Talle**cant
# **Talle**cant
# ...
#
# N u. ·
#  M talles $ PRECIO

BLOCK_RE = re.compile(
    r"!\[\]\((?P<img>[^)]+)\)\s*"
    r"(?P<code>[A-Za-z0-9\-]+)\s*"
    r"\[(?P<name>[^\]]+)\]\((?P<link>[^)]+)\)\s*"
    r"(?P<desc>[^\n]+)\n"
    r"(?P<body>.*?)"
    r"(?=!\[\]\(|\Z)",
    re.S,
)

SIZE_RE = re.compile(r"\*\*([^*]+)\*\*\s*(\d+)")
PRICE_RE = re.compile(r"\$\s*([\d.]+)")
UNITS_RE = re.compile(r"(\d+)\s*u\.")
TALLES_RE = re.compile(r"(\d+)\s*talles?")


def parse_catalog(markdown_text: str):
    products = []
    for m in BLOCK_RE.finditer(markdown_text):
        name = m.group("name").strip()
        desc = m.group("desc").strip(" ·\n")
        body = m.group("body")

        sizes = {talle.strip(): int(qty) for talle, qty in SIZE_RE.findall(body)}
        price_match = PRICE_RE.search(body)
        units_match = UNITS_RE.search(body)
        talles_match = TALLES_RE.search(body)

        if not is_footwear(name, desc):
            continue

        # desc suele ser "Color · Modelo · Genero" (genero es opcional)
        parts = [p.strip() for p in desc.split("·")]
        color = parts[0] if len(parts) > 0 else ""
        modelo = parts[1] if len(parts) > 1 else name
        genero = parts[2] if len(parts) > 2 else ""

        products.append({
            "codigo": m.group("code").strip(),
            "nombre": name,
            "link": m.group("link").strip(),
            "imagen": m.group("img").strip(),
            "color": color,
            "modelo": modelo,
            "genero": genero,
            "marca": name.split(" ")[0],
            "talles": sizes,
            "unidades": int(units_match.group(1)) if units_match else sum(sizes.values()),
            "cantidad_talles": int(talles_match.group(1)) if talles_match else len(sizes),
            "precio": int(price_match.group(1).replace(".", "")) if price_match else None,
        })
    return products


def main():
    print(f"Descargando {CATALOG_URL} ...")
    resp = requests.get(CATALOG_URL, timeout=60)
    resp.raise_for_status()

    print("Convirtiendo HTML a texto estructurado...")
    text = html_to_md(resp.text)

    print("Parseando productos...")
    products = parse_catalog(text)
    print(f"  -> {len(products)} productos de calzado encontrados")

    data = {
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "total": len(products),
        "productos": products,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Listo: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as e:
        print(f"Error al descargar el catálogo: {e}", file=sys.stderr)
        sys.exit(1)
