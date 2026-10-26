from decimal import Decimal

import pytest


# ---------- helpers ----------
def _categoria(client, nome="Salgado"):
    return client.post("/categorias/", json={"nome": nome})


def _produto(client, nome="Pastel", categoria_id=1, preco=9):
    return client.post(
        "/produtos/",
        json={"nome": nome, "categoria_id": categoria_id, "preco_atual": preco},
    )


def _cliente(client, **dados):
    return client.post("/clientes/", json={"nome": "Teste", **dados})


def _lancar(client, cliente_id=1, produto_id=1, **extra):
    return client.post(
        f"/clientes/{cliente_id}/lancamentos/", json={"produto_id": produto_id, **extra}
    )


def _extrato(client, cliente_id=1):
    return client.get(f"/clientes/{cliente_id}/extrato")


def _total(client, cliente_id=1):
    # Decimal(str(...)) funciona tanto se o JSON vier como texto quanto como número
    return Decimal(str(_extrato(client, cliente_id).json()["total"]))


@pytest.fixture()
def base(client):
    """categoria 1 (Salgado), produto 1 (Pastel, 9,00) e cliente 1 (Teste) já cadastrados"""
    assert _categoria(client).status_code == 200
    assert _produto(client).status_code == 200
    assert _cliente(client).status_code == 200
    return client


# ---------- categorias ----------
def test_categoria_criada_aparece_na_lista(client):
    _categoria(client)
    nomes = [c["nome"] for c in client.get("/categorias/").json()]
    assert nomes == ["Salgado"]


def test_categoria_duplicada_da_409(client):
    _categoria(client)
    assert _categoria(client).status_code == 409


@pytest.mark.parametrize("nome", ["", "x" * 61])
def test_categoria_com_nome_invalido_da_422(client, nome):
    assert _categoria(client, nome).status_code == 422


# ---------- produtos ----------
def test_produto_com_categoria_inexistente_da_404(client):
    assert _produto(client, categoria_id=999).status_code == 404


def test_produto_duplicado_da_409(base):
    assert _produto(base).status_code == 409


@pytest.mark.parametrize("preco", [-1, 9.999])
def test_produto_com_preco_invalido_da_422(base, preco):
    assert _produto(base, nome="Coxinha", preco=preco).status_code == 422


def test_busca_de_produto_pelo_nome(base):
    _produto(base, nome="Coxinha", preco=6.5)
    resposta = base.get("/produtos/", params={"busca": "cox"})
    assert [p["nome"] for p in resposta.json()] == ["Coxinha"]


def test_produto_inexistente_da_404(client):
    assert client.get("/produtos/999").status_code == 404


def test_atualizar_preco_do_produto(base):
    resposta = base.put("/produtos/1", json={"preco_atual": 10})
    assert resposta.status_code == 200
    assert Decimal(str(resposta.json()["preco_atual"])) == Decimal("10.00")


def test_produto_desativado_some_da_lista(base):
    base.put("/produtos/1", json={"ativo": False})
    assert base.get("/produtos/").json() == []


def test_renomear_produto_para_nome_de_outro_da_409(base):
    _produto(base, nome="Coxinha", preco=6.5)
    assert base.put("/produtos/2", json={"nome": "Pastel"}).status_code == 409


def test_produto_pode_manter_o_proprio_nome(base):
    assert base.put("/produtos/1", json={"nome": "Pastel"}).status_code == 200


def test_atualizar_produto_inexistente_da_404(client):
    assert client.put("/produtos/999", json={"nome": "X"}).status_code == 404


def test_mover_produto_para_categoria_inexistente_da_404(base):
    assert base.put("/produtos/1", json={"categoria_id": 999}).status_code == 404


# ---------- clientes ----------
def test_cliente_criado_nao_devolve_o_cpf(client):
    resposta = _cliente(client, cpf="12345678901")
    assert resposta.status_code == 200
    assert "cpf" not in resposta.json()


def test_cpf_duplicado_da_409(client):
    _cliente(client, cpf="12345678901")
    assert _cliente(client, nome="Outro", cpf="12345678901").status_code == 409


@pytest.mark.parametrize(
    "dados",
    [{"cpf": "123"}, {"cpf": "123.456.789-01"}, {"nome": ""}, {"apelido": "x" * 61}],
)
def test_cliente_invalido_da_422(client, dados):
    assert _cliente(client, **dados).status_code == 422


def test_busca_de_cliente_por_apelido(client):
    _cliente(client, nome="Maria Souza", apelido="Mazinha")
    resposta = client.get("/clientes/", params={"busca": "mazi"})
    assert [c["nome"] for c in resposta.json()] == ["Maria Souza"]


def test_cliente_inexistente_da_404(client):
    assert client.get("/clientes/999").status_code == 404


def test_atualizar_cpf_para_o_de_outro_cliente_da_409(client):
    _cliente(client, cpf="11111111111")
    _cliente(client, nome="Outro", cpf="22222222222")
    assert client.put("/clientes/2", json={"cpf": "11111111111"}).status_code == 409


def test_cliente_desativado_some_da_busca(base):
    base.put("/clientes/1", json={"ativo": False})
    assert base.get("/clientes/").json() == []


def test_atualizar_cliente_inexistente_da_404(client):
    assert client.put("/clientes/999", json={"nome": "X"}).status_code == 404


# ---------- lancamentos (Feature 1) ----------
def test_fluxo_completo_da_feature_1(base):
    assert _lancar(base, quantidade=2).status_code == 200

    extrato = _extrato(base).json()
    item = extrato["itens"][0]
    assert item["produto"]["nome"] == "Pastel"
    assert Decimal(str(item["valor_unitario"])) == Decimal("9.00")
    assert Decimal(str(item["subtotal"])) == Decimal("18.00")
    assert item["data_compra"]
    assert Decimal(str(extrato["total"])) == Decimal("18.00")


def test_valor_informado_vence_o_preco_do_produto(base):
    resposta = _lancar(base, valor_unitario=3.5)
    assert Decimal(str(resposta.json()["valor_unitario"])) == Decimal("3.50")


def test_produto_de_preco_livre_usa_o_valor_informado(base):
    _produto(base, nome="Doce", preco=0)
    _lancar(base, produto_id=2, valor_unitario=2.5)
    assert _total(base) == Decimal("2.50")


def test_lancar_para_cliente_inexistente_da_404(base):
    assert _lancar(base, cliente_id=999).status_code == 404


def test_lancar_para_cliente_desativado_da_400(base):
    base.put("/clientes/1", json={"ativo": False})
    assert _lancar(base).status_code == 400


def test_lancar_produto_inexistente_da_404(base):
    assert _lancar(base, produto_id=999).status_code == 404


def test_lancar_produto_desativado_da_404(base):
    base.put("/produtos/1", json={"ativo": False})
    assert _lancar(base).status_code == 404


@pytest.mark.parametrize(
    "extra",
    [{"quantidade": 0}, {"quantidade": -2}, {"valor_unitario": -1}, {"valor_unitario": 1.999}],
)
def test_lancamento_invalido_da_422(base, extra):
    assert _lancar(base, **extra).status_code == 422


def test_editar_item_atualiza_o_extrato(base):
    _lancar(base, quantidade=2)
    assert base.put("/lancamentos/1", json={"quantidade": 3}).status_code == 200
    assert _total(base) == Decimal("27.00")


def test_editar_item_inexistente_da_404(client):
    assert client.put("/lancamentos/999", json={"quantidade": 1}).status_code == 404


def test_editar_item_para_produto_desativado_da_404(base):
    _produto(base, nome="Coxinha", preco=6.5)
    base.put("/produtos/2", json={"ativo": False})
    _lancar(base)
    assert base.put("/lancamentos/1", json={"produto_id": 2}).status_code == 404


@pytest.mark.parametrize("extra", [{"quantidade": 0}, {"valor_unitario": -1}])
def test_editar_item_com_dado_invalido_da_422(base, extra):
    _lancar(base)
    assert base.put("/lancamentos/1", json=extra).status_code == 422


def test_excluir_item_tira_do_extrato_e_do_total(base):
    _lancar(base, quantidade=2)
    _lancar(base, valor_unitario=3.5)
    assert _total(base) == Decimal("21.50")

    assert base.delete("/lancamentos/1").status_code == 200

    extrato = _extrato(base).json()
    assert len(extrato["itens"]) == 1
    assert Decimal(str(extrato["total"])) == Decimal("3.50")


def test_excluir_duas_vezes_da_404(base):
    _lancar(base)
    assert base.delete("/lancamentos/1").status_code == 200
    assert base.delete("/lancamentos/1").status_code == 404


def test_editar_item_ja_excluido_da_404(base):
    _lancar(base)
    base.delete("/lancamentos/1")
    assert base.put("/lancamentos/1", json={"quantidade": 5}).status_code == 404


def test_reajuste_de_preco_nao_altera_o_extrato(base):
    _lancar(base, quantidade=2)
    base.put("/produtos/1", json={"preco_atual": 10})
    assert _total(base) == Decimal("18.00")


def test_extrato_de_cliente_inexistente_da_404(client):
    assert _extrato(client, 999).status_code == 404


def test_extrato_vazio_tem_total_zero(base):
    extrato = _extrato(base).json()
    assert extrato["itens"] == []
    assert Decimal(str(extrato["total"])) == Decimal("0")


def test_extrato_nao_mistura_clientes(base):
    _cliente(base, nome="Outro")
    _lancar(base, cliente_id=1, quantidade=2)
    _lancar(base, cliente_id=2, quantidade=1)
    assert _total(base, 1) == Decimal("18.00")
    assert _total(base, 2) == Decimal("9.00")