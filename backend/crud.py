from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

import schemas
from models import Categoria as CategoriaModel
from models import Cliente as ClienteModel
from models import Lancamento as LancamentoModel
from models import Produto as ProdutoModel


# ---------- Categorias ----------

# get all (select * from categorias)
def get_categorias(db: Session):
    """
    essa é a funcao que retorna todas as categorias, em ordem alfabética
    """
    return db.query(CategoriaModel).order_by(CategoriaModel.nome).all()


# get where id = x
def get_categoria(db: Session, categoria_id: int):
    """
    essa é a funcao que retorna somente uma categoria, usando where no id
    """
    return db.query(CategoriaModel).filter(CategoriaModel.id == categoria_id).first()


# get where nome = x
def get_categoria_por_nome(db: Session, nome: str):
    """
    retorna a categoria com esse nome (ou None)
    usada para não deixar cadastrar categoria duplicada
    """
    return db.query(CategoriaModel).filter(CategoriaModel.nome == nome).first()


# insert into
def create_categoria(db: Session, categoria: schemas.CategoriaCreate):
    """
    cria uma categoria nova
    add -> coloca na sessão | commit -> grava no banco | refresh -> recarrega com o id gerado
    """
    db_categoria = CategoriaModel(**categoria.model_dump())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria


# ---------- Produtos ----------

# get all com busca opcional (select * from produtos where ativo and nome ilike)
def get_produtos(db: Session, busca: str | None = None):
    """
    retorna os produtos ativos; se vier 'busca', filtra pelo nome
    ilike = like que ignora maiúscula/minúscula
    """
    query = db.query(ProdutoModel).filter(ProdutoModel.ativo.is_(True))
    if busca:
        query = query.filter(ProdutoModel.nome.ilike(f"%{busca}%"))
    return query.order_by(ProdutoModel.nome).all()


# get where id = x
def get_produto(db: Session, produto_id: int):
    """
    essa é a funcao que retorna somente um produto, usando where no id
    """
    return db.query(ProdutoModel).filter(ProdutoModel.id == produto_id).first()


# get where nome = x
def get_produto_por_nome(db: Session, nome: str):
    """
    retorna o produto com esse nome (ou None), para evitar duplicados
    """
    return db.query(ProdutoModel).filter(ProdutoModel.nome == nome).first()


# insert into
def create_produto(db: Session, produto: schemas.ProdutoCreate):
    """
    cria um produto novo
    """
    db_produto = ProdutoModel(**produto.model_dump())
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto


# update
def update_produto(db: Session, produto_id: int, produto: schemas.ProdutoUpdate):
    """
    atualiza só os campos que foram enviados (exclude_unset=True ignora o que não veio)
    retorna None se o produto não existir
    """
    db_produto = get_produto(db, produto_id)
    if db_produto is None:
        return None

    for campo, valor in produto.model_dump(exclude_unset=True).items():
        setattr(db_produto, campo, valor)

    db.commit()
    db.refresh(db_produto)
    return db_produto


# ---------- Clientes ----------

# get all com busca opcional (nome ou apelido)
def get_clientes(db: Session, busca: str | None = None):
    """
    retorna os clientes ativos; se vier 'busca', procura no nome OU no apelido
    """
    query = db.query(ClienteModel).filter(ClienteModel.ativo.is_(True))
    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            or_(ClienteModel.nome.ilike(termo), ClienteModel.apelido.ilike(termo))
        )
    return query.order_by(ClienteModel.nome).all()


# get where id = x
def get_cliente(db: Session, cliente_id: int):
    """
    essa é a funcao que retorna somente um cliente, usando where no id
    """
    return db.query(ClienteModel).filter(ClienteModel.id == cliente_id).first()


# get where cpf = x
def get_cliente_por_cpf(db: Session, cpf: str):
    """
    retorna o cliente com esse cpf (ou None), para evitar duplicados
    """
    return db.query(ClienteModel).filter(ClienteModel.cpf == cpf).first()


# insert into
def create_cliente(db: Session, cliente: schemas.ClienteCreate):
    """
    cria um cliente novo
    """
    db_cliente = ClienteModel(**cliente.model_dump())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente


# update
def update_cliente(db: Session, cliente_id: int, cliente: schemas.ClienteUpdate):
    """
    atualiza só os campos enviados; retorna None se o cliente não existir
    """
    db_cliente = get_cliente(db, cliente_id)
    if db_cliente is None:
        return None

    for campo, valor in cliente.model_dump(exclude_unset=True).items():
        setattr(db_cliente, campo, valor)

    db.commit()
    db.refresh(db_cliente)
    return db_cliente


# ---------- Lançamentos (Feature 1) ----------

# get where cliente_id = x and deletado_em is null
def get_lancamentos_cliente(db: Session, cliente_id: int):
    """
    retorna os itens ativos do cliente (deletado_em vazio), do mais antigo ao mais novo
    """
    return (
        db.query(LancamentoModel)
        .filter(
            LancamentoModel.cliente_id == cliente_id,
            LancamentoModel.deletado_em.is_(None),
        )
        .order_by(LancamentoModel.data_compra)
        .all()
    )


# get where id = x and deletado_em is null
def get_lancamento(db: Session, lancamento_id: int):
    """
    retorna somente um item ativo, usando where no id
    item já deletado (deletado_em preenchido) conta como não encontrado
    """
    return (
        db.query(LancamentoModel)
        .filter(
            LancamentoModel.id == lancamento_id,
            LancamentoModel.deletado_em.is_(None),
        )
        .first()
    )


# insert into
def create_lancamento(
    db: Session,
    cliente_id: int,
    produto: ProdutoModel,
    lancamento: schemas.LancamentoCreate,
):
    """
    lança um item no fiado do cliente
    se não vier valor_unitario, usa o preço atual do produto (guarda o preço da hora da compra)
    """
    valor = (
        lancamento.valor_unitario
        if lancamento.valor_unitario is not None
        else produto.preco_atual
    )

    db_lancamento = LancamentoModel(
        cliente_id=cliente_id,
        produto_id=produto.id,
        quantidade=lancamento.quantidade,
        valor_unitario=valor,
    )
    db.add(db_lancamento)
    db.commit()
    db.refresh(db_lancamento)
    return db_lancamento


# update
def update_lancamento(db: Session, lancamento_id: int, lancamento: schemas.LancamentoUpdate):
    """
    edita um item; só altera o que foi enviado
    se trocar o produto e não mandar valor, usa o preço do novo produto
    retorna None se o item não existir
    """
    db_lancamento = get_lancamento(db, lancamento_id)
    if db_lancamento is None:
        return None

    campos = {
        k: v for k, v in lancamento.model_dump(exclude_unset=True).items() if v is not None
    }

    if "produto_id" in campos and "valor_unitario" not in campos:
        novo_produto = get_produto(db, campos["produto_id"])
        campos["valor_unitario"] = novo_produto.preco_atual

    for campo, valor in campos.items():
        setattr(db_lancamento, campo, valor)

    db.commit()
    db.refresh(db_lancamento)
    return db_lancamento


# delete (exclusão lógica)
def delete_lancamento(db: Session, lancamento_id: int):
    """
    não apaga a linha: só preenche deletado_em com a data/hora atual
    assim o histórico fica e o item some do extrato e do total
    retorna None se o item não existir
    """
    db_lancamento = get_lancamento(db, lancamento_id)
    if db_lancamento is None:
        return None

    db_lancamento.deletado_em = datetime.now()
    db.commit()
    return db_lancamento


# extrato: itens + total
def get_extrato(db: Session, cliente: ClienteModel):
    """
    monta o extrato do cliente: dados dele, itens ativos e o total
    total = soma de (quantidade * valor_unitario) de cada item
    """
    itens = get_lancamentos_cliente(db, cliente.id)
    total = sum((i.quantidade * i.valor_unitario for i in itens), Decimal("0"))
    return {"cliente": cliente, "itens": itens, "total": total}