def test_no_schema_name_collision(app):
    """A name two modules share becomes `app__modules__...` in OpenAPI and in the client."""
    clashes = [k for k in app.openapi()["components"]["schemas"] if "app__modules__" in k]
    assert clashes == []
