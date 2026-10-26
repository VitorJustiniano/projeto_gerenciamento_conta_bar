from datetime import datetime
from decimal import Decimal

import crud
import schemas
from models import Lancamento as LancamentoModel


def _cenario(db):
    """categoria Salgado, produto Pastel (9,00) e cliente Teste"""
    cat = crud.create_categoria(db, schemas.CategoriaCreate(nome="Salgado"))
    prod = crud.create_produto(
        db,
        schemas.ProdutoCreate(nome="Pastel", categoria_id=cat.id, preco_atual=Decimal("9.00")),
    )
    cli = crud.create_cliente(db, schemas.ClienteCreate(nome="Teste", apelido="teste"))
    return prod, cli


def _lancar(db, cli, prod, **campos):
    dados = schemas.LancamentoCreate(produto_id=prod.id, **campos)
    return crud.create_lancamento(db, cli.id, prod, dados)


# ---------- categorias ----------
def test_categorias_vem_em_ordem_alfabetica(db):
    for nome in ("Doce", "Bebida", "Salgado"):
        crud.create_categoria(db, schemas.CategoriaCreate(nome=nome))
    assert [c.nome for c in crud.get_categorias(db)] == ["Bebida", "Doce", "Salgado"]


def test_busca_de_categoria_por_nome(db):
    crud.create_categoria(db, schemas.CategoriaCreate(nome="Salgado"))
    assert crud.get_categoria_por_nome(db, "Salgado") is not None
    assert crud.get_categoria_por_nome(db, "Inexistente") is None


# ---------- produtos ----------
def test_get_produtos_traz_so_ativos(db):
    prod, _ = _cenario(db)
    crud.update_produto(db, prod.id, schemas.ProdutoUpdate(ativo=False))
    assert crud.get_produtos(db) == []


def test_busca_de_produto_ignora_maiuscula(db):
    _cenario(db)
    assert len(crud.get_produtos(db, busca="PAST")) == 1
    assert crud.get_produtos(db, busca="coxinha") == []


def test_update_de_produto_parcial_nao_mexe_no_resto(db):
    prod, _ = _cenario(db)
    atualizado = crud.update_produto(
        db, prod.id, schemas.ProdutoUpdate(preco_atual=Decimal("10.00"))
    )
    assert atualizado.preco_atual == Decimal("10.00")
    assert atualizado.nome == "Pastel"
    assert atualizado.ativo is True


def test_update_de_produto_inexistente_devolve_none(db):
    assert crud.update_produto(db, 999, schemas.ProdutoUpdate(nome="X")) is None


# ---------- clientes ----------
def test_busca_de_cliente_por_nome_e_por_apelido(db):
    crud.create_cliente(db, schemas.ClienteCreate(nome="Maria Souza", apelido="Mazinha"))
    assert len(crud.get_clientes(db, busca="souza")) == 1
    assert len(crud.get_clientes(db, busca="MAZI")) == 1
    assert crud.get_clientes(db, busca="joao") == []


def test_cliente_inativo_nao_aparece_na_busca(db):
    _, cli = _cenario(db)
    crud.update_cliente(db, cli.id, schemas.ClienteUpdate(ativo=False))
    assert crud.get_clientes(db) == []


def test_update_de_cliente_parcial(db):
    _, cli = _cenario(db)
    atualizado = crud.update_cliente(
        db, cli.id, schemas.ClienteUpdate(telefone="14999999999")
    )
    assert atualizado.telefone == "14999999999"
    assert atualizado.nome == "Teste"


def test_busca_de_cliente_por_cpf(db):
    crud.create_cliente(db, schemas.ClienteCreate(nome="A", cpf="12345678901"))
    assert crud.get_cliente_por_cpf(db, "12345678901") is not None
    assert crud.get_cliente_por_cpf(db, "00000000000") is None


# ---------- lancamentos ----------
def test_lancamento_usa_preco_do_produto(db):
    prod, cli = _cenario(db)
    item = _lancar(db, cli, prod, quantidade=2)
    assert item.valor_unitario == Decimal("9.00")
    assert item.quantidade == 2
    assert item.deletado_em is None


def test_valor_informado_vence_o_preco_do_produto(db):
    prod, cli = _cenario(db)
    item = _lancar(db, cli, prod, valor_unitario=Decimal("3.50"))
    assert item.valor_unitario == Decimal("3.50")


def test_valor_zero_informado_nao_cai_no_preco_do_produto(db):
    prod, cli = _cenario(db)
    item = _lancar(db, cli, prod, valor_unitario=Decimal("0"))
    assert item.valor_unitario == Decimal("0")


def test_reajuste_do_produto_nao_muda_item_antigo(db):
    prod, cli = _cenario(db)
    item = _lancar(db, cli, prod)
    crud.update_produto(db, prod.id, schemas.ProdutoUpdate(preco_atual=Decimal("10.00")))
    db.refresh(item)
    assert item.valor_unitario == Decimal("9.00")


def test_update_de_lancamento_altera_a_quantidade(db):
    prod, cli = _cenario(db)
    item = _lancar(db, cli, prod, quantidade=2)
    atualizado = crud.update_lancamento(db, item.id, schemas.LancamentoUpdate(quantidade=5))
    assert atualizado.quantidade == 5
    assert atualizado.valor_unitario == Decimal("9.00")


def test_troca_de_produto_sem_valor_usa_preco_do_novo(db):
    prod, cli = _cenario(db)
    outro = crud.create_produto(
        db,
        schemas.ProdutoCreate(
            nome="Coxinha", categoria_id=prod.categoria_id, preco_atual=Decimal("6.50")
        ),
    )
    item = _lancar(db, cli, prod)
    atualizado = crud.update_lancamento(
        db, item.id, schemas.LancamentoUpdate(produto_id=outro.id)
    )
    assert atualizado.produto_id == outro.id
    assert atualizado.valor_unitario == Decimal("6.50")


def test_troca_de_produto_com_valor_mantem_o_valor_informado(db):
    prod, cli = _cenario(db)
    outro = crud.create_produto(
        db,
        schemas.ProdutoCreate(
            nome="Coxinha", categoria_id=prod.categoria_id, preco_atual=Decimal("6.50")
        ),
    )
    item = _lancar(db, cli, prod)
    atualizado = crud.update_lancamento(
        db,
        item.id,
        schemas.LancamentoUpdate(produto_id=outro.id, valor_unitario=Decimal("5.00")),
    )
    assert atualizado.valor_unitario == Decimal("5.00")


def test_update_de_lancamento_inexistente_devolve_none(db):
    assert crud.update_lancamento(db, 999, schemas.LancamentoUpdate(quantidade=1)) is None


def test_exclusao_e_logica(db):
    prod, cli = _cenario(db)
    item = _lancar(db, cli, prod)
    crud.delete_lancamento(db, item.id)
    db.refresh(item)  # a linha continua no banco
    assert item.deletado_em is not None
    assert crud.get_lancamento(db, item.id) is None


def test_excluir_duas_vezes_devolve_none(db):
    prod, cli = _cenario(db)
    item = _lancar(db, cli, prod)
    assert crud.delete_lancamento(db, item.id) is not None
    assert crud.delete_lancamento(db, item.id) is None


# ---------- extrato ----------
def test_extrato_soma_os_itens(db):
    prod, cli = _cenario(db)
    _lancar(db, cli, prod, quantidade=2)
    _lancar(db, cli, prod, valor_unitario=Decimal("3.50"))
    extrato = crud.get_extrato(db, cli)
    assert len(extrato["itens"]) == 2
    assert extrato["total"] == Decimal("21.50")


def test_extrato_sem_itens_tem_total_zero(db):
    _, cli = _cenario(db)
    extrato = crud.get_extrato(db, cli)
    assert extrato["itens"] == []
    assert extrato["total"] == Decimal("0")


def test_extrato_ignora_itens_deletados(db):
    prod, cli = _cenario(db)
    item = _lancar(db, cli, prod, quantidade=2)
    _lancar(db, cli, prod, valor_unitario=Decimal("3.50"))
    crud.delete_lancamento(db, item.id)
    extrato = crud.get_extrato(db, cli)
    assert len(extrato["itens"]) == 1
    assert extrato["total"] == Decimal("3.50")


def test_extrato_nao_mistura_clientes(db):
    prod, cli = _cenario(db)
    outro = crud.create_cliente(db, schemas.ClienteCreate(nome="Outro"))
    _lancar(db, cli, prod, quantidade=2)
    _lancar(db, outro, prod)
    assert crud.get_extrato(db, cli)["total"] == Decimal("18.00")
    assert crud.get_extrato(db, outro)["total"] == Decimal("9.00")


def test_extrato_ordenado_por_data_de_compra(db):
    prod, cli = _cenario(db)
    for dia in (3, 1, 2):
        db.add(
            LancamentoModel(
                cliente_id=cli.id,
                produto_id=prod.id,
                quantidade=1,
                valor_unitario=Decimal("9.00"),
                data_compra=datetime(2026, 10, dia),
            )
        )
    db.commit()
    dias = [i.data_compra.day for i in crud.get_extrato(db, cli)["itens"]]
    assert dias == [1, 2, 3]


def test_soma_de_centavos_fecha_exato(db):
    prod, cli = _cenario(db)
    for _ in range(3):
        _lancar(db, cli, prod, valor_unitario=Decimal("0.10"))
    assert crud.get_extrato(db, cli)["total"] == Decimal("0.30")