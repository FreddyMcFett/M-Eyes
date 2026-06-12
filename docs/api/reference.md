# API Reference

The interactive reference below is generated from the live FastAPI OpenAPI schema on
every merge to `main`. A running M-Eyes instance also serves it at `/docs` (Swagger UI)
and `/redoc`.

<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
  window.addEventListener('load', function () {
    SwaggerUIBundle({
      url: './openapi.json',
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis],
      deepLinking: true,
    });
  });
</script>
