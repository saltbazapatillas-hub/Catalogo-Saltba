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
    "fjallraven", "goorin", "hydro", "cartus", "vilelmo", "jibbitz", "nordik",
    "lah51020", "lab53511", "lab53514", "lab53516", "lab53517", "lab53515",
    "lab51522", "lab51523", "lab51524", "speedo", "thayer", "timberpack",
    "gorra", "luca", "xaff", "capsio", "persa", "by", "aslan", "vart club", "explore", "grow", "friends", 
    "hugo", "morris", "alaska", "esquel", "vancouver", "vr surf", "paraiso", "calavera", "esencial", 
    "pack", "aromatizador", "jogging", "hunter", "logo", "freaky", "calavart", "lima", "freedom",
    "desierto", "landers", "f-you", "cool", "ulises", "valentino", "esteroids", "cava", "bolson",
    "claromeco", "xero", "acid", "piluso", 
   # "Caja X" en la lista de marcas suele ser accesorios/embalaje
   
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

# El código de producto (ej "BK0005-29") es el ancla más confiable: a diferencia
# de la imagen, siempre aparece como texto plano aunque la imagen todavía no se
# haya cargado (muchos catálogos cargan las fotos de a poco al scrollear).
CODE_RE = re.compile(r"(?m)^\s*([A-Za-z]{1,4}\d{3,6}-\d+)\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
SIZE_RE = re.compile(r"\*\*([^*]+)\*\*\s*(\d+)")
PRICE_RE = re.compile(r"\$\s*([\d.]+)")
UNITS_RE = re.compile(r"(\d+)\s*u\.")
TALLES_RE = re.compile(r"(\d+)\s*talles?")


def parse_catalog(markdown_text: str):
    products = []
    codes = list(CODE_RE.finditer(markdown_text))

    for i, code_match in enumerate(codes):
        start = code_match.start()
        end = codes[i + 1].start() if i + 1 < len(codes) else len(markdown_text)
        block = markdown_text[start:end]
        code = code_match.group(1)

        link_match = LINK_RE.search(block)
        if not link_match:
            # Sin nombre/link no hay forma de identificar el producto: se salta.
            continue
        name = link_match.group(1).strip()
        link = link_match.group(2).strip()

        # La descripción (Color · Modelo · Genero) suele estar en la primera
        # línea con contenido, entre el código y el link.
        before_link = block[: link_match.start()]
        desc_candidates = [l.strip() for l in before_link.splitlines() if l.strip()]
        desc = desc_candidates[-1] if desc_candidates else ""
        # A veces la descripción viene DESPUÉS del link en vez de antes.
        if not desc:
            after_link = block[link_match.end():]
            after_lines = [l.strip() for l in after_link.splitlines() if l.strip()]
            desc = after_lines[0] if after_lines else ""

        if not is_footwear(name, desc):
            continue

        # La imagen puede estar en este bloque o, si venía "pegada" al
        # producto anterior en el texto, justo antes del código.
        search_zone = markdown_text[max(0, start - 500):end]
        imgs = IMG_RE.findall(search_zone)
        img = imgs[-1] if imgs else ""

        sizes = {talle.strip(): int(qty) for talle, qty in SIZE_RE.findall(block)}
        price_match = PRICE_RE.search(block)
        units_match = UNITS_RE.search(block)
        talles_match = TALLES_RE.search(block)

        parts = [p.strip() for p in desc.split("·")]
        color = parts[0] if len(parts) > 0 else ""
        modelo = parts[1] if len(parts) > 1 else name
        genero = parts[2] if len(parts) > 2 else ""

        products.append({
            "codigo": code,
            "nombre": name,
            "link": link,
            "imagen": img,
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
    total_codes = len(CODE_RE.findall(text))
    products = parse_catalog(text)
    print(f"  -> {total_codes} códigos de producto detectados en total")
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
