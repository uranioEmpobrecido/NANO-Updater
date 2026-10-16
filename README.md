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
- `<slug>/firmware.json` + `<slug>/firmware/*.bin`: each product's firmware. A product with
  several models (Performance Mixer) lists them under `variants`, and its page asks which one
  the device is before anything can be flashed.
  - FX-DR2: published by its own project, `NANO-FX-DR/tools/web_updater/publish.sh`.
  - The rest: the release builds in `STM32-Dev/NANO Release Firmware`, listed in
    `releases.json` (file, model name, version if it has one; otherwise the page shows the
    file's date). `python3 release.py` copies them here, checks each one against its product
    and writes its `firmware.json`; `python3 release.py fum` does one product.

- `fonts/`: the look of our products' screens. Web fonts made from the firmware's own bitmap
  fonts (Terminus 10x18 and 8x14 as "NANO Screen", the 5x7 of the big numbers as "NANO Big") by
  `python3 tools/screen_fonts.py <NANO-FX-DR/src/ui>`; Terminus is under the SIL OFL
  (`fonts/OFL.txt`). Keep each font at a whole multiple of its cell (18 px, 14 px, 8 px) and
  each line height an even number of pixels away, or the pixels blur. A group's `accent` in
  `products.json` colours its products (NANO Modules: the yellow of its panels).

After editing `products.json` or `template.html`, run `python3 build.py`, then commit and push.
