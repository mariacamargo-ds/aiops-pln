import math

from app.embeddings import HashEmbedder


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def test_deterministico_e_normalizado():
    e = HashEmbedder()
    v1, v2 = e.embed_docs(["db-primary WARN connections=490/500"] * 2)
    assert v1 == v2 and math.isclose(math.sqrt(sum(x * x for x in v1)), 1.0, rel_tol=1e-9)
    assert len(v1) == e.dim


def test_texto_relacionado_fica_mais_perto():
    e = HashEmbedder()
    q = e.embed_query("o banco está lento?")
    perto, longe = e.embed_docs(["db-primary WARN slow_query duration=8421ms", "cdn-edge INFO purge issued paths=10"])
    assert cos(q, perto) > cos(q, longe)
