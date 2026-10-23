from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas import (
    CategoriaCreate, CategoriaResponse,
    ProdutoCreate, ProdutoResponse, ProdutoUpdate,
    ClienteCreate, ClienteResponse, ClienteUpdate,
    LancamentoCreate, LancamentoResponse, LancamentoUpdate,
    ExtratoCliente,
)
from typing import List, Optional
import crud

router = APIRouter()


# ---------------- CATEGORIAS ----------------

# criar rota de buscar todas as categorias
# sempre 2 atributos obrigatorios, o PATH e o RESPONSE
@router.get("/categorias/", response_model=List[CategoriaResponse])
def read_all_categorias(db: Session = Depends(get_db)):
    categorias = crud.get_categorias(db=db)
    return categorias


# criar rota de adicionar uma categoria
@router.post("/categorias/", response_model=CategoriaResponse)
def create_categoria(categoria: CategoriaCreate, db: Session = Depends(get_db)):
    if crud.get_categoria_por_nome(db=db, nome=categoria.nome):
        raise HTTPException(status_code=409, detail="essa categoria ja existe")
    return crud.create_categoria(db=db, categoria=categoria)


# ---------------- PRODUTOS ----------------

# criar rota de buscar todos os produtos (com busca opcional pelo nome)
@router.get("/produtos/", response_model=List[ProdutoResponse])
def read_all_produtos(busca: Optional[str] = None, db: Session = Depends(get_db)):
    produtos = crud.get_produtos(db=db, busca=busca)
    return produtos


# criar rota de buscar 1 produto
@router.get("/produtos/{produto_id}", response_model=ProdutoResponse)
def read_one_produto(produto_id: int, db: Session = Depends(get_db)):
    db_produto = crud.get_produto(db=db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="voce ta buscando um produto que nao existe")
    return db_produto


# criar rota de adicionar um produto
@router.post("/produtos/", response_model=ProdutoResponse)
def create_produto(produto: ProdutoCreate, db: Session = Depends(get_db)):
    if crud.get_categoria(db=db, categoria_id=produto.categoria_id) is None:
        raise HTTPException(status_code=404, detail="essa categoria nao existe, cadastre ela primeiro")
    if crud.get_produto_por_nome(db=db, nome=produto.nome):
        raise HTTPException(status_code=409, detail="esse produto ja existe")
    return crud.create_produto(db=db, produto=produto)


# criar rota de atualizar um produto (serve tambem para mudar o preco ou desativar: ativo = false)
@router.put("/produtos/{produto_id}", response_model=ProdutoResponse)
def update_produto(produto_id: int, produto: ProdutoUpdate, db: Session = Depends(get_db)):
    if produto.categoria_id is not None:
        if crud.get_categoria(db=db, categoria_id=produto.categoria_id) is None:
            raise HTTPException(status_code=404, detail="essa categoria nao existe")
    if produto.nome is not None:
        existente = crud.get_produto_por_nome(db=db, nome=produto.nome)
        if existente and existente.id != produto_id:
            raise HTTPException(status_code=409, detail="ja existe outro produto com esse nome")

    db_produto = crud.update_produto(db=db, produto_id=produto_id, produto=produto)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="voce ta querendo atualizar um produto que nao existe")
    return db_produto


# ---------------- CLIENTES ----------------

# criar rota de buscar todos os clientes (com busca opcional por nome ou apelido)
@router.get("/clientes/", response_model=List[ClienteResponse])
def read_all_clientes(busca: Optional[str] = None, db: Session = Depends(get_db)):
    clientes = crud.get_clientes(db=db, busca=busca)
    return clientes


# criar rota de buscar 1 cliente
@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
def read_one_cliente(cliente_id: int, db: Session = Depends(get_db)):
    db_cliente = crud.get_cliente(db=db, cliente_id=cliente_id)
    if db_cliente is None:
        raise HTTPException(status_code=404, detail="voce ta buscando um cliente que nao existe")
    return db_cliente


# criar rota de adicionar um cliente
@router.post("/clientes/", response_model=ClienteResponse)
def create_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    if cliente.cpf and crud.get_cliente_por_cpf(db=db, cpf=cliente.cpf):
        raise HTTPException(status_code=409, detail="ja existe um cliente com esse cpf")
    return crud.create_cliente(db=db, cliente=cliente)


# criar rota de atualizar um cliente (serve tambem para desativar: ativo = false)
@router.put("/clientes/{cliente_id}", response_model=ClienteResponse)
def update_cliente(cliente_id: int, cliente: ClienteUpdate, db: Session = Depends(get_db)):
    if cliente.cpf:
        existente = crud.get_cliente_por_cpf(db=db, cpf=cliente.cpf)
        if existente and existente.id != cliente_id:
            raise HTTPException(status_code=409, detail="ja existe outro cliente com esse cpf")

    db_cliente = crud.update_cliente(db=db, cliente_id=cliente_id, cliente=cliente)
    if db_cliente is None:
        raise HTTPException(status_code=404, detail="voce ta querendo atualizar um cliente que nao existe")
    return db_cliente


# ---------------- LANCAMENTOS (FEATURE 1) ----------------

# criar rota de adicionar um item no fiado do cliente
@router.post("/clientes/{cliente_id}/lancamentos/", response_model=LancamentoResponse)
def create_lancamento(cliente_id: int, lancamento: LancamentoCreate, db: Session = Depends(get_db)):
    if crud.get_cliente(db=db, cliente_id=cliente_id) is None:
        raise HTTPException(status_code=404, detail="voce ta lancando fiado pra um cliente que nao existe")

    produto = crud.get_produto(db=db, produto_id=lancamento.produto_id)
    if produto is None or not produto.ativo:
        raise HTTPException(status_code=404, detail="produto nao existe ou esta desativado")

    return crud.create_lancamento(db=db, cliente_id=cliente_id, produto=produto, lancamento=lancamento)


# criar rota de buscar o extrato do cliente (itens + total)
@router.get("/clientes/{cliente_id}/extrato", response_model=ExtratoCliente)
def read_extrato(cliente_id: int, db: Session = Depends(get_db)):
    db_cliente = crud.get_cliente(db=db, cliente_id=cliente_id)
    if db_cliente is None:
        raise HTTPException(status_code=404, detail="voce ta buscando o extrato de um cliente que nao existe")
    return crud.get_extrato(db=db, cliente=db_cliente)


# criar rota de atualizar um item lancado
@router.put("/lancamentos/{lancamento_id}", response_model=LancamentoResponse)
def update_lancamento(lancamento_id: int, lancamento: LancamentoUpdate, db: Session = Depends(get_db)):
    if lancamento.produto_id is not None:
        produto = crud.get_produto(db=db, produto_id=lancamento.produto_id)
        if produto is None or not produto.ativo:
            raise HTTPException(status_code=404, detail="produto nao existe ou esta desativado")

    db_lancamento = crud.update_lancamento(db=db, lancamento_id=lancamento_id, lancamento=lancamento)
    if db_lancamento is None:
        raise HTTPException(status_code=404, detail="voce ta querendo atualizar um item que nao existe")
    return db_lancamento


# criar rota de deletar um item lancado (exclusao logica, so marca deletado_em)
@router.delete("/lancamentos/{lancamento_id}", response_model=LancamentoResponse)
def delete_lancamento(lancamento_id: int, db: Session = Depends(get_db)):
    db_lancamento = crud.delete_lancamento(db=db, lancamento_id=lancamento_id)
    if db_lancamento is None:
        raise HTTPException(status_code=404, detail="voce ta querendo deletar um item que nao existe")
    return db_lancamento