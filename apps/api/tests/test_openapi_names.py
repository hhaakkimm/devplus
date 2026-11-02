def test_no_schema_name_collision(app):
    """A name two modules share becomes `app__modules__...` in OpenAPI and in the client."""
    clashes = [k for k in app.openapi()["components"]["schemas"] if "app__modules__" in k]
    assert clashes == []


def test_simulator_schemas_have_the_sim_prefix(app):
    """A simulator schema named like another module's (`TaskOut`) renames a client type."""
    spec = app.openapi()

    def refs(node) -> set[str]:
        if isinstance(node, dict):
            found = {node["$ref"].rsplit("/", 1)[1]} if "$ref" in node else set()
            return found.union(*map(refs, node.values())) if node else found
        if isinstance(node, list):
            return set().union(*map(refs, node)) if node else set()
        return set()

    schemas = spec["components"]["schemas"]
    todo = set().union(
        *(
            refs(op)
            for path, item in spec["paths"].items()
            if "/simulator/" in path
            for op in item.values()
        )
    )
    seen: set[str] = set()
    while todo:
        name = todo.pop()
        seen.add(name)
        todo |= refs(schemas[name]) - seen
    own = seen - {"HTTPValidationError", "ValidationError"}
    assert own and all(n.startswith("Sim") for n in own)
