# Catálogo de calzado

Dos archivos hacen todo el trabajo:

- **`index.html`** — la página del catálogo. Solo lee `products.json` (que
  tiene que estar en la misma carpeta) y muestra los productos con buscador,
  filtro por marca y orden.
- **`scraper.py`** — se conecta a `callback.vart.com.ar`, agarra todos los
  productos, se queda solo con calzado (zapatillas, zapatos, sandalias,
  ojotas, botas, mocasines, etc.) y reescribe `products.json`.

## Probarlo ahora mismo

`products.json` ya tiene 8 productos de ejemplo (reales, sacados del
catálogo) para que puedas abrir `index.html` y ver cómo queda. Ese archivo
se pisa por completo la primera vez que corras `scraper.py`.

## Generar los datos reales

```bash
pip install requests markdownify
python scraper.py
```

Esto descarga el catálogo completo (los ~1.000 productos) y deja
`products.json` actualizado con solo el calzado.

## Cómo lograr que se actualice solo

`index.html` es una página estática: no tiene "motor" propio, así que algo
tiene que volver a correr `scraper.py` cada tanto y reemplazar
`products.json`. Dos formas simples, según dónde termines alojando esto:

**Opción A — Tenés un servidor propio (hosting con cPanel, VPS, etc.)**
Programá una tarea cron que corra el script, por ejemplo cada 6 horas:
```
0 */6 * * * cd /ruta/al/catalogo && python3 scraper.py
```

**Opción B — Vas a alojar esto en GitHub Pages (gratis, sin servidor)**
Subís esta carpeta a un repositorio de GitHub y agregás un workflow de
GitHub Actions programado (por ejemplo cada 6 horas) que corra
`scraper.py` y haga commit del `products.json` nuevo. GitHub Pages sirve
siempre la última versión del archivo automáticamente. Si querés, te armo
ese workflow también — decime en qué vas a alojar la página final y lo
dejamos listo.

## Si algún producto queda mal clasificado

Al principio de `scraper.py` hay dos listas: `FOOTWEAR_KEYWORDS` (palabras
que indican que es calzado) y `EXCLUDE_KEYWORDS` (palabras que lo
descartan aunque coincida). Si ves algo que no debería estar, o algo que
falta, agregás o sacás una palabra ahí y volvés a correr el script.
