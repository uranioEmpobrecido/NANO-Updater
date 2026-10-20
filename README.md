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

- Type: JetBrains Mono (Google Fonts), regular weight only: the brand's choice. `fonts/` holds "NANO Screen", the
  FX-DR2's own screen font (Terminus 10x18), made from the firmware's bitmaps by
  `python3 tools/screen_fonts.py <NANO-FX-DR/src/ui>` and used only where the page shows what
  the device's screen says; keep it at 18 px so its pixels stay sharp. Terminus is under the
  SIL OFL (`fonts/OFL.txt`). A group's `accent` in `products.json` colours its products (NANO
  Modules: the yellow of its panels).

- **Unreleased products and tester mode.** A product with `"unreleased": true` in
  `products.json` is left off the front page, and its own page says it is not available — unless
  the browser is in tester mode. A tester gets there with **Tester**, at the foot of any of those
  pages, and the tester code; the browser remembers it (only the code's salted hash, in
  localStorage) until **Exit**. Set or change the code with `python3 tester_code.py 'the code'`
  (only the salt and hash go into `products.json`; changing it signs every tester out). This
  HIDES products, it does not protect them: the site is static and this repository public, so
  `products.json` and the firmware files can still be read by anyone who looks.

After editing `products.json` or `template.html`, run `python3 build.py`, then commit and push.
