<!doctype html>
<html lang="${language}" class="density-${density} qstyle-${qstyle}" data-theme="${theme}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>${title}</title>

  <link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="${google_fonts_url}">

  <link rel="stylesheet" href="style.css">

  <!-- Preload critical resources. React UMD is shipped inside the bundle
       (vendor/react*.production.min.js) so there is no CDN dependency
       on first paint — important for slow Colab proxies and offline use. -->
  <link rel="preload" as="style" href="style.css">
  <link rel="preload" as="script" href="vendor/react.production.min.js">
  <link rel="preload" as="script" href="vendor/react-dom.production.min.js">

  <!-- Vercel Analytics (injected only when deployed to Vercel) -->
  ${analytics_script}
</head>
<body>
  <div id="root"></div>

  <script>
    window.SURVEY = ${survey_json};
    window.PAGES  = ${pages_json};
  </script>

  <script src="vendor/react.production.min.js"></script>
  <script src="vendor/react-dom.production.min.js"></script>

  <script src="env.js"></script>
  ${scripts_block}
</body>
</html>
