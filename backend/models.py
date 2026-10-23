from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship
from database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(60), unique=True, nullable=False)


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), unique=True, nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    preco_atual = Column(Numeric(10, 2), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    categoria = relationship("Categoria")


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False, index=True)
    apelido = Column(String(60), index=True)
    telefone = Column(String(20))
    cpf = Column(String(11), unique=True)
    ativo = Column(Boolean, default=True, nullable=False)

    lancamentos = relationship("Lancamento", back_populates="cliente")


class Lancamento(Base):
    __tablename__ = "lancamentos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, default=1, nullable=False)
    valor_unitario = Column(Numeric(10, 2), nullable=False)
    data_compra = Column(DateTime, server_default=func.now(), nullable=False)
    deletado_em = Column(DateTime, nullable=True)

    cliente = relationship("Cliente", back_populates="lancamentos")
    produto = relationship("Produto")