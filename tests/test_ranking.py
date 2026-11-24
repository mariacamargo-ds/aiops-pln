from datetime import datetime, timedelta

import pytest

from app.ranking import Event, Params, retrieval_boost, score

NOW = datetime(2026, 11, 3, 12, 0)
P = Params()


def ev(tipo, user="u1", hours_ago=0.0, **kw):
    return Event(tipo, user, NOW - timedelta(hours=hours_ago), **kw)


def test_cold_start_usa_so_o_conteudo():
    s = score(0.6, [], NOW, P, "medio")
    assert s.final == pytest.approx(0.6) and s.alpha == 0 and s.engagement == pytest.approx(0.5)


def test_feedback_positivo_sobe_e_negativo_desce():
    up = score(0.5, [ev("thumbs_up", f"u{i}") for i in range(8)], NOW, P, "medio").final
    down = score(0.5, [ev("thumbs_down", f"u{i}") for i in range(8)], NOW, P, "medio").final
    assert up > 0.5 > down


def test_evento_antigo_pesa_menos():
    novo = score(0.4, [ev("thumbs_up", f"u{i}", 0) for i in range(6)], NOW, P, "baixo").final
    velho = score(0.4, [ev("thumbs_up", f"u{i}", 96) for i in range(6)], NOW, P, "baixo").final
    assert novo > velho > 0.4 - 1e-9


def test_piso_de_seguranca_nunca_esconde_critico():
    evs = [ev("thumbs_down", f"u{i}") for i in range(40)] + [ev("dismiss", f"v{i}") for i in range(40)]
    s = score(0.85, evs, NOW, P, "critico")
    assert s.floor_applied and s.final == P.floors["critico"]
    # o mesmo histórico derruba um alerta não crítico
    assert score(0.85, evs, NOW, P, "alto").final < 0.5


def test_retorno_decrescente_por_usuario():
    um_usuario = score(0.5, [ev("thumbs_up", "spam") for _ in range(30)], NOW, P, "medio")
    varios = score(0.5, [ev("thumbs_up", f"u{i}") for i in range(30)], NOW, P, "medio")
    assert varios.final > um_usuario.final


def test_vies_de_posicao_so_nos_sinais_implicitos():
    alto = score(0.5, [ev("view_logs", f"u{i}", posicao=1) for i in range(5)], NOW, P, "medio").raw
    baixo = score(0.5, [ev("view_logs", f"u{i}", posicao=7) for i in range(5)], NOW, P, "medio").raw
    assert baixo > alto
    a = score(0.5, [ev("thumbs_up", f"u{i}", posicao=1) for i in range(5)], NOW, P, "medio").raw
    b = score(0.5, [ev("thumbs_up", f"u{i}", posicao=7) for i in range(5)], NOW, P, "medio").raw
    assert a == b


def test_dwell_cresce_com_o_tempo_e_tem_teto():
    r = lambda s: score(0.5, [ev("dwell", dwell_s=s)], NOW, P, "medio").raw
    assert r(0) == 0 < r(15) < r(60) == r(600)


def test_evento_desconhecido_gera_erro():
    with pytest.raises(ValueError):
        score(0.5, [ev("curtir")], NOW, P, "medio")


def test_bonus_na_busca_e_simetrico():
    assert retrieval_boost(0.5, P) == 0
    assert retrieval_boost(1.0, P) == pytest.approx(-retrieval_boost(0.0, P)) == pytest.approx(P.retrieval_beta)


def test_positivo_nunca_reduz_e_negativo_nunca_aumenta():
    for c in (0.1, 0.5, 0.88, 0.97):
        assert score(c, [ev("thumbs_up")], NOW, P, "medio").final >= c
        assert score(c, [ev("thumbs_down")], NOW, P, "baixo").final <= c
        assert score(c, [ev("thumbs_up", f"u{i}") for i in range(30)], NOW, P, "medio").final <= 1.0


def test_poucos_votos_movem_pouco_e_muitos_movem_muito():
    um = score(0.4, [ev("thumbs_up")], NOW, P, "baixo").final
    dez = score(0.4, [ev("thumbs_up", f"u{i}") for i in range(10)], NOW, P, "baixo").final
    assert 0.4 < um < dez and dez > 0.6
