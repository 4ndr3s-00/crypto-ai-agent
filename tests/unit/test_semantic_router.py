"""
Pruebas unitarias para el Router Semántico y Filtro de Dominio (US-09).
"""

from backend.app.agent.semantic_router import SemanticRouter


def test_semantic_router_greetings():
    router = SemanticRouter()
    d1 = router.route("Hola")
    d2 = router.route("Buenos días Arca")

    assert d1.kind == "greeting"
    assert "Arca" in d1.response
    assert d2.kind == "greeting"


def test_semantic_router_identity():
    router = SemanticRouter()
    decision = router.route("¿Quién eres?")

    assert decision.kind == "identity"
    assert "Arca" in decision.response
    assert "Andrés" in decision.response


def test_semantic_router_out_of_scope():
    router = SemanticRouter()
    decision = router.route("¿Cómo preparar una receta de pizza?")

    assert decision.kind == "out_of_scope"
    assert "alcance" in decision.response.lower()


def test_semantic_router_analytics():
    router = SemanticRouter()
    d1 = router.route("¿Cuál es el precio actual de Bitcoin?")
    d2 = router.route("Muestra el gráfico y el vwap de Ethereum en 4h")

    assert d1.kind == "analytics"
    assert d2.kind == "analytics"
