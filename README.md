# NANO Updater

Updates NANO Industries devices from the browser (Chrome or Edge, WebUSB):
https://uranioempobrecido.github.io/NANO-Updater/

- `products.json`: the products, grouped as on the front page, and for each one how it is
  updated: its bootloader (`daisy` or `stm32-rom`), the app address, which reset vectors its
  firmware may have, the chip's memory map (for `stm32-rom`, so another chip is never
  written), and the update-mode instructions. A product with no `bootloader` or `steps` shows
  as "Coming soon".
- `template.html`: the one updater page every product uses. `build.py` copies it into each
  product's folder.
- `<slug>/firmware.json` + `<slug>/firmware/*.bin`: each product's firmware, published by its
  own project (FX-DR2: `NANO-FX-DR/tools/web_updater/publish.sh`).

After editing `products.json` or `template.html`, run `python3 build.py`, then commit and push.
