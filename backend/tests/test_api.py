"""Testes de integração dos 10 endpoints (HTTP → serviço → banco SQLite em memória)."""

API = "/api/v1"


def atividade(rsc_hashid=None, **extra):
    dados = {
        "rsa_requisito": "II",
        "rsa_descricao": "Coordenação de projeto institucional (2 Por projeto)",
        "rsa_pontos": 10,
        "rsa_observacoes": "Item nº 11 · 5.0 pt/Por projeto",
    }
    if rsc_hashid:
        dados["rsc_hashid"] = rsc_hashid
    return {**dados, **extra}


# ─── Login ───────────────────────────────────────────────────────────────────


async def test_login_ok(client):
    resp = await client.post(
        f"{API}/login", json={"email": "teste@teste.com.br", "password": "123456"}
    )
    corpo = resp.json()
    assert resp.status_code == 200
    assert corpo["success"] is True
    assert corpo["token"]
    assert corpo["name"] == "Servidor Demonstração"
    assert corpo["usu_hashid"]


async def test_login_senha_errada(client):
    resp = await client.post(f"{API}/login", json={"email": "teste@teste.com.br", "password": "x"})
    assert resp.status_code == 401
    assert resp.json() == {"success": False, "message": "E-mail ou senha inválidos."}


async def test_login_campos_obrigatorios(client):
    resp = await client.post(f"{API}/login", json={})
    assert resp.status_code == 401
    assert resp.json()["message"] == "E-mail e senha são obrigatórios."


async def test_login_aceita_hash_do_laravel(client, db):
    from app.models import Usuario

    # Hash "$2y$" gerado pelo PHP (password_hash) para a senha "tae123".
    hash_php = "$2y$10$lo1zUyQDnpN1K5TQb0krGuPRSfosxyg5/ja.oARO8h2gWukAhHcrm"
    db.add(Usuario(name="Legado", email="legado@prorsctae.local", password=hash_php))
    await db.commit()
    resp = await client.post(
        f"{API}/login", json={"email": "legado@prorsctae.local", "password": "tae123"}
    )
    assert resp.status_code == 200


async def test_rotas_rsc_exigem_token(client):
    assert (await client.get(f"{API}/rsc")).status_code == 401
    resp = await client.get(f"{API}/rsc", headers={"Authorization": "Bearer lixo"})
    assert resp.status_code == 401
    assert resp.json() == {"message": "Token inválido."}


# ─── Catálogo ────────────────────────────────────────────────────────────────


async def test_catalogo_agrupado_por_requisito(client, auth):
    corpo = (await client.get(f"{API}/rsc/catalogo", headers=auth)).json()
    assert list(corpo) == ["I", "II", "III", "IV", "V", "VI"]
    assert sum(len(v) for v in corpo.values()) == 60
    item = corpo["I"][0]
    assert set(item) == {
        "item_numero",
        "item_requisito",
        "item_descricao",
        "item_unidade",
        "item_pontos_unidade",
    }
    assert item["item_numero"] == 1


# ─── Requerimentos ───────────────────────────────────────────────────────────


async def test_criar_listar_e_obter(client, auth, rsc_hashid):
    lista = (await client.get(f"{API}/rsc", headers=auth)).json()
    assert len(lista) == 1
    assert lista[0]["rsc_hashid"] == rsc_hashid
    assert lista[0]["rsc_status"] == "rascunho"
    assert lista[0]["total_pontos"] == 0

    dados = (await client.get(f"{API}/rsc/{rsc_hashid}", headers=auth)).json()
    assert dados["rsc_escolaridade"] == "graduacao"
    assert dados["rsc_nome_servidor"] == "Servidor Demonstração"
    assert dados["atividades"] == []
    assert dados["calculos"]["niveis"]["RSC-IV"]["pontos_minimos"] == 30


async def test_criar_com_escolaridade_invalida(client, auth):
    resp = await client.post(f"{API}/rsc", json={"rsc_escolaridade": "xpto"}, headers=auth)
    assert resp.status_code == 422
    assert resp.json()["errors"] == {"rsc_escolaridade": ["Escolaridade inválida."]}


async def test_hashid_invalido_404_e_de_outro_usuario_403(client, auth, auth_outro, rsc_hashid):
    assert (await client.get(f"{API}/rsc/naoexiste", headers=auth)).status_code == 404
    resp = await client.get(f"{API}/rsc/{rsc_hashid}", headers=auth_outro)
    assert resp.status_code == 403
    assert resp.json() == {"message": "Acesso negado."}


async def test_atualizar_escolaridade_recalcula(client, auth, rsc_hashid):
    resp = await client.post(
        f"{API}/rsc/{rsc_hashid}/escolaridade",
        json={"rsc_escolaridade": "doutorado", "rsc_data_ultima_concessao": ""},
        headers=auth,
    )
    corpo = resp.json()
    assert resp.status_code == 200
    assert corpo["success"] is True
    assert not any(n["disponivel"] for n in corpo["calculos"]["niveis"].values())


async def test_escolaridade_obrigatoria(client, auth, rsc_hashid):
    resp = await client.post(f"{API}/rsc/{rsc_hashid}/escolaridade", json={}, headers=auth)
    assert resp.status_code == 422
    assert resp.json()["errors"]["rsc_escolaridade"] == ["A escolaridade é obrigatória."]


async def test_nivel_selecionado(client, auth, rsc_hashid):
    url = f"{API}/rsc/{rsc_hashid}/nivel-selecionado"
    ok = await client.post(url, json={"rsc_nivel_selecionado": "RSC-IV"}, headers=auth)
    assert ok.status_code == 200

    abaixo = await client.post(url, json={"rsc_nivel_selecionado": "RSC-II"}, headers=auth)
    assert abaixo.status_code == 422
    assert "abaixo do indicado" in abaixo.json()["errors"][0]

    invalido = await client.post(url, json={"rsc_nivel_selecionado": "RSC-X"}, headers=auth)
    assert invalido.status_code == 422


# ─── Atividades ──────────────────────────────────────────────────────────────


async def test_ciclo_completo_da_atividade(client, auth, rsc_hashid):
    resp = await client.post(f"{API}/rsc/atividade", json=atividade(rsc_hashid), headers=auth)
    corpo = resp.json()
    assert resp.status_code == 200
    assert corpo["calculos"]["total_pontos"] == 10
    assert corpo["calculos"]["pontos_por_requisito"]["II"] == 10
    rsa_hashid = corpo["rsa_hashid"]

    resp = await client.put(
        f"{API}/rsc/atividade/{rsa_hashid}", json=atividade(rsa_pontos=12.5), headers=auth
    )
    assert resp.json()["calculos"]["total_pontos"] == 12.5

    dados = (await client.get(f"{API}/rsc/{rsc_hashid}", headers=auth)).json()
    assert dados["atividades"][0]["rsa_pontos"] == 12.5

    resp = await client.delete(f"{API}/rsc/atividade/{rsa_hashid}", headers=auth)
    assert resp.json()["calculos"]["total_pontos"] == 0


async def test_item_duplicado_e_bloqueado(client, auth, rsc_hashid):
    await client.post(f"{API}/rsc/atividade", json=atividade(rsc_hashid), headers=auth)
    resp = await client.post(f"{API}/rsc/atividade", json=atividade(rsc_hashid), headers=auth)
    assert resp.status_code == 422
    assert resp.json() == {"errors": ["Este item já foi adicionado neste requisito."]}


async def test_validacao_da_atividade(client, auth, rsc_hashid):
    resp = await client.post(
        f"{API}/rsc/atividade",
        json=atividade(rsc_hashid, rsa_requisito="VII", rsa_pontos="abc"),
        headers=auth,
    )
    erros = resp.json()["errors"]
    assert resp.status_code == 422
    assert erros["rsa_requisito"] == ["Requisito inválido. Use I, II, III, IV, V ou VI."]
    assert erros["rsa_pontos"] == ["A pontuação deve ser um número."]


async def test_atividade_de_outro_usuario_404(client, auth, auth_outro, rsc_hashid):
    resp = await client.post(f"{API}/rsc/atividade", json=atividade(rsc_hashid), headers=auth)
    rsa_hashid = resp.json()["rsa_hashid"]
    outro = await client.delete(f"{API}/rsc/atividade/{rsa_hashid}", headers=auth_outro)
    assert outro.status_code == 404
    # O código de uma atividade não vale como código de requerimento.
    assert (await client.get(f"{API}/rsc/{rsa_hashid}", headers=auth)).status_code == 404


async def test_requerimento_nao_editavel(client, db, auth, rsc_hashid):
    from app.core.hashid import decodificar
    from app.models import RscSaber

    rsc = await db.get(RscSaber, decodificar("rsc", rsc_hashid))
    rsc.rsc_status = "enviado"
    await db.commit()

    resp = await client.post(f"{API}/rsc/atividade", json=atividade(rsc_hashid), headers=auth)
    assert resp.status_code == 422
    assert resp.json()["errors"][0].startswith("O requerimento não pode ser editado")


async def test_documentacao_openapi(client):
    resp = await client.get("/api/openapi.json")
    assert resp.status_code == 200
    assert "/api/v1/rsc/{hashid}" in resp.json()["paths"]
