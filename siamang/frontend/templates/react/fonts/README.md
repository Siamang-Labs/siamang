# The survey's typefaces

The families of the font presets (`UIConfig.font_preset`), shipped with the
package so that a survey serves them from its own host: nothing is requested
from Google Fonts or any other third party when a respondent opens a survey.
`siamang.frontend.theme.fonts` declares them (`@font-face`) in the survey's
stylesheet and puts the files a survey uses, with their license texts, in its
bundle under `fonts/`.

| Family | Files | Axes | Font version | License |
| :--- | :--- | :--- | :--- | :--- |
| Source Serif 4 | `source-serif-4-{latin,latin-ext,cyrillic}-opsz-normal.woff2` | weight 200–900, optical size 8–60 | 4.004 (Google Fonts v14) | `source-serif-4-OFL.txt` |
| Inter | `inter-{latin,latin-ext,cyrillic}-wght-normal.woff2` | weight 100–900 | 4.001 (Google Fonts v20) | `inter-OFL.txt` |
| Nunito | `nunito-{latin,latin-ext,cyrillic}-wght-normal.woff2` | weight 200–1000 | 3.602 (Google Fonts v32) | `nunito-OFL.txt` |

All three are under the SIL Open Font License 1.1, which allows bundling and
redistributing them with software; each copy has to carry the copyright notice
and the license, which is why a survey's bundle ships the `*-OFL.txt` of every
family it uses next to the files.

What the files are: the variable fonts of Google Fonts, cut by Google into the
`latin`, `latin-ext` and `cyrillic` subsets with the unicode ranges Google's
own CSS gives them (the `@font-face` rules keep those ranges, so a browser
fetches only the subsets a page's text needs). Source Serif 4 keeps its
optical-size axis, as the Google Fonts request it replaces asked for
(`opsz,wght@8..60`); Inter and Nunito are the weight-axis cuts, as those
requests were. Upright styles only: italic is synthesized by the browser, as
it was.

Where they come from:

- the woff2 files: the npm packages `@fontsource-variable/source-serif-4`,
  `@fontsource-variable/inter` and `@fontsource-variable/nunito`, version
  5.3.0 each (`files/<name>`), which repackage the Google Fonts files unchanged;
- the license texts: `ofl/sourceserif4/OFL.txt`, `ofl/inter/OFL.txt` and
  `ofl/nunito/OFL.txt` of https://github.com/google/fonts (main, fetched
  2026-09-27). The font files' own copyright notices (name ID 0) read
  "© 2014 - 2021 Adobe Systems Incorporated (http://www.adobe.com/), with
  Reserved Font Name ‘Source’." (Source Serif 4), "Copyright 2016 The Inter
  Project Authors (https://github.com/rsms/inter)" and "Copyright 2014 The
  Nunito Project Authors (https://github.com/googlefonts/nunito)".

SHA-256:

```
f2ea9c12d2fe9bd3a9589b02ad2c0909da88f30938c91adc838c4f4098f9f9e0  source-serif-4-latin-opsz-normal.woff2
155f6e701097cc269cf8d5d7ac86795f263f1afbeb47c14d1d747108c9335389  source-serif-4-latin-ext-opsz-normal.woff2
e553fa829fd9ae0900931584f73c6b894539558b598d5ee7c4907140a1f29f05  source-serif-4-cyrillic-opsz-normal.woff2
3100e775e8616cd2611beecfa23a4263d7037586789b43f035236a2e6fbd4c62  inter-latin-wght-normal.woff2
34b9c504cab7a73e37b746343a449132e56cf7b5481af2cb81dc74dcff25c956  inter-latin-ext-wght-normal.woff2
71d5ee93cc1e9f1d520a3a8b66456de18c7879d8df09d57fcd2eaff75fef0075  inter-cyrillic-wght-normal.woff2
ba344451eab25b217a165363b1982048a5e5830a0daf36577973955a04cac793  nunito-latin-wght-normal.woff2
2c8d792869818ecb253a46bc3c63c7013df7aac2f69291c3c85e5cdc94160960  nunito-latin-ext-wght-normal.woff2
63b14e3ef0966785438b8947380dfbcad178cbd3c6a5ed2172672ca0d8b839ac  nunito-cyrillic-wght-normal.woff2
```

Size: 564,236 bytes of woff2 (Source Serif 4 316,672; Inter 152,072; Nunito
95,492), 13 KB of license texts. A bundle carries only the families its
stylesheet names: the `academic` preset 469 KB, `modern` 152 KB, `humanist`
95 KB. A respondent downloads only the subsets the page's text uses — for an
English survey in the `academic` preset, the two `latin` files (171 KB).

To update: take the same files from a newer `@fontsource-variable/*` release
(or Google Fonts), update the table and the checksums here, and the weight
ranges in `siamang/frontend/theme/fonts.py` if a font's axes changed. A file
whose content changes needs a new name (`BundledFamily.file` makes them):
bundles do not fingerprint font files, and a host caches them long — Studio's
survey host for a year.
