"""Print the OpenAPI schema as JSON (used by the docs CI job)."""

import json

from app.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2))
