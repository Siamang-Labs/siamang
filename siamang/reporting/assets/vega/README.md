# Vega, Vega-Lite and Vega-Embed, vendored

A report saved with interactive charts (`Report.to_html(..., interactive=True)`,
the Save report node's *Interactive charts in HTML*) draws its charts in the
reader's browser with these three libraries. They are copied into the HTML
document once, inline, from these files: a report is mailed to a client and
opened offline, so nothing is ever loaded from a CDN or any other address.

| File | Package | Version | License |
|---|---|---|---|
| `vega.min.js` | [`vega`](https://www.npmjs.com/package/vega) | 6.4.0 | BSD-3-Clause, `LICENSE-vega` |
| `vega-lite.min.js` | [`vega-lite`](https://www.npmjs.com/package/vega-lite) | 6.4.3 | BSD-3-Clause, `LICENSE-vega-lite` |
| `vega-embed.min.js` | [`vega-embed`](https://www.npmjs.com/package/vega-embed) | 7.3.0 | BSD-3-Clause, `LICENSE-vega-embed` |

The specs the charts write (`SurveyChart.vega_lite()`) are **Vega-Lite 6**
(`https://vega.github.io/schema/vega-lite/v6.json`); `vega-lite` 6 requires
`vega` 6, and `vega-embed` 7 is the release that embeds both.

Each file is the package's own minified browser build (`build/*.min.js` of the
tarball on the npm registry), byte for byte:

```text
8f6a3587cf8d4f42c7e08120e3eb05d067e746d554e39d2dcf52acc0bd5ba28f  vega.min.js
35a9821df838825b05a6a73e9414b58747a1b18321583858ed903c66393a5c7e  vega-lite.min.js
b1455caba2fb1a72fb46025ba0ba1316e2dbc7f0dd40a3f6040172bf9c08ba91  vega-embed.min.js
```

To update, fetch the three tarballs, copy the builds and the licenses, and
update the versions here and in `siamang/reporting/vega.py` (`VERSIONS`):

```bash
npm pack vega@6.4.0 vega-lite@6.4.3 vega-embed@7.3.0
for f in vega-*.tgz; do mkdir -p "${f%.tgz}" && tar xzf "$f" -C "${f%.tgz}"; done
cp vega-6.4.0/package/build/vega.min.js .
cp vega-lite-6.4.3/package/build/vega-lite.min.js .
cp vega-embed-7.3.0/package/build/vega-embed.min.js .
cp vega-6.4.0/package/LICENSE LICENSE-vega   # and the other two
sha256sum *.min.js
```

The tests validate every chart's spec against the JSON Schema of the same
Vega-Lite release (`tests/fixtures/vega-lite-v6.4.3.schema.json`, the tarball's
`build/vega-lite-schema.json`) — replace it with the new one.

What a report does to the files when it copies them in: the last line of
`vega-lite.min.js` and `vega-embed.min.js`, a `//# sourceMappingURL=` comment,
is left out (a browser's developer tools would otherwise ask for a `.map` file
that is not there). Nothing else is changed.

The builds bundle the libraries' own dependencies — the `vega-*` modules, the
`d3-*` modules, `delaunator`, `internmap`, `robust-predicates` and
`topojson-client` in Vega; `vega-util`, `vega-expression` and
`vega-event-selector` in Vega-Lite; `vega-interpreter`, `vega-themes`,
`vega-tooltip`, `vega-schema-url-parser`, `fast-json-patch`,
`json-stringify-pretty-compact`, `semver` and `tslib` in Vega-Embed — as the
Vega project distributes them in these builds, each under its own permissive
license (BSD-3-Clause, ISC, MIT, 0BSD, the Unlicense).

`THIRD-PARTY-NOTICES.txt` holds every one of those licenses verbatim, the
packages with the same text listed together; a report with interactive charts
carries it too, as an HTML comment before the libraries (`vega.notices()`), so
a copy mailed to a client reproduces the notices the licenses ask for. It is
written from the packages npm installs (the command-line tools and type
declarations they depend on are not in the builds, and are left out):

```bash
npm install --ignore-scripts vega@6.4.0 vega-lite@6.4.3 vega-embed@7.3.0
# each node_modules/<package>/LICENSE*, grouped by identical text
```
