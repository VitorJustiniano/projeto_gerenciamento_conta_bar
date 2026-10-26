from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas import (
    CategoriaCreate,
    ClienteCreate,
    LancamentoCreate,
    LancamentoResponse,
    LancamentoUpdate,
    ProdutoCreate,
    ProdutoUpdate,
)


# ---------- categoria ----------
@pytest.mark.parametrize("nome", ["", "x" * 61])
def test_categoria_com_nome_invalido_e_rejeitada(nome):
    with pytest.raises(ValidationError):
        CategoriaCreate(nome=nome)


# ---------- cliente ----------
@pytest.mark.parametrize(
    "cpf", ["123", "1234567890", "123456789012", "123.456.789-01", "abcdefghijk"]
)
def test_cpf_invalido_e_rejeitado(cpf):
    with pytest.raises(ValidationError):
        ClienteCreate(nome="Teste", cpf=cpf)


def test_cpf_valido_ou_ausente_e_aceito():
    assert ClienteCreate(nome="Teste", cpf="12345678901").cpf == "12345678901"
    assert ClienteCreate(nome="Teste").cpf is None


@pytest.mark.parametrize(
    "campos",
    [{"nome": ""}, {"nome": "x" * 121}, {"apelido": "x" * 61}, {"telefone": "1" * 21}],
)
def test_cliente_com_texto_invalido_e_rejeitado(campos):
    with pytest.raises(ValidationError):
        ClienteCreate(**{"nome": "Teste", **campos})


# ---------- produto ----------
@pytest.mark.parametrize("nome", ["", "x" * 121])
def test_produto_com_nome_invalido_e_rejeitado(nome):
    with pytest.raises(ValidationError):
        ProdutoCreate(nome=nome, categoria_id=1, preco_atual=Decimal("9.00"))


@pytest.mark.parametrize("preco", ["-1", "9.999"])
def test_preco_invalido_e_rejeitado(preco):
    with pytest.raises(ValidationError):
        ProdutoCreate(nome="Pastel", categoria_id=1, preco_atual=Decimal(preco))


@pytest.mark.parametrize("preco", ["0", "9.9", "9.99"])
def test_preco_valido_e_aceito(preco):
    produto = ProdutoCreate(nome="Pastel", categoria_id=1, preco_atual=Decimal(preco))
    assert produto.preco_atual == Decimal(preco)


def test_update_de_produto_vazio_nao_altera_nada():
    assert ProdutoUpdate().model_dump(exclude_unset=True) == {}


def test_update_de_produto_valida_igual_ao_create():
    with pytest.raises(ValidationError):
        ProdutoUpdate(preco_atual=Decimal("-1"))
    with pytest.raises(ValidationError):
        ProdutoUpdate(nome="")


# ---------- lancamento ----------
@pytest.mark.parametrize("quantidade", [0, -1])
def test_quantidade_invalida_e_rejeitada(quantidade):
    with pytest.raises(ValidationError):
        LancamentoCreate(produto_id=1, quantidade=quantidade)


def test_quantidade_padrao_e_1():
    assert LancamentoCreate(produto_id=1).quantidade == 1


def test_valor_negativo_e_rejeitado():
    with pytest.raises(ValidationError):
        LancamentoCreate(produto_id=1, valor_unitario=Decimal("-1"))


def test_valor_vazio_e_aceito():
    # vazio significa "usar o preço do produto"
    assert LancamentoCreate(produto_id=1).valor_unitario is None


def test_update_de_lancamento_valida_igual_ao_create():
    with pytest.raises(ValidationError):
        LancamentoUpdate(quantidade=0)
    with pytest.raises(ValidationError):
        LancamentoUpdate(valor_unitario=Decimal("-1"))


def test_subtotal_e_calculado_sem_erro_de_centavo():
    resposta = LancamentoResponse.model_validate(
        {
            "id": 1,
            "produto": {
                "id": 1,
                "nome": "Pastel",
                "categoria_id": 1,
                "preco_atual": "9.00",
                "ativo": True,
                "categoria": {"id": 1, "nome": "Salgado"},
            },
            "quantidade": 3,
            "valor_unitario": "0.10",
            "data_compra": "2026-10-26T10:00:00",
        }
    )
    assert resposta.subtotal == Decimal("0.30")