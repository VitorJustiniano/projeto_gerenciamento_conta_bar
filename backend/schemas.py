from pydantic import BaseModel, Field, computed_field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List


# ---------- Categoria ----------
class CategoriaBase(BaseModel):
    nome: str

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id: int

    class Config:
        from_attributes = True


# ---------- Produto ----------
class ProdutoBase(BaseModel):
    nome: str
    categoria_id: int
    preco_atual: Decimal = Field(ge=0)

class ProdutoCreate(ProdutoBase):
    pass

class ProdutoResponse(ProdutoBase):
    id: int
    ativo: bool
    categoria: CategoriaResponse

    class Config:
        from_attributes = True

class ProdutoUpdate(BaseModel):
    nome: Optional[str] = None
    categoria_id: Optional[int] = None
    preco_atual: Optional[Decimal] = Field(default=None, ge=0)
    ativo: Optional[bool] = None


# ---------- Cliente ----------
class ClienteBase(BaseModel):
    nome: str
    apelido: Optional[str] = None
    telefone: Optional[str] = None
    cpf: Optional[str] = Field(default=None, pattern=r"^\d{11}$")

class ClienteCreate(ClienteBase):
    pass

class ClienteResponse(BaseModel):
    id: int
    nome: str
    apelido: Optional[str] = None
    telefone: Optional[str] = None
    ativo: bool

    class Config:
        from_attributes = True

class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    apelido: Optional[str] = None
    telefone: Optional[str] = None
    cpf: Optional[str] = Field(default=None, pattern=r"^\d{11}$")
    ativo: Optional[bool] = None


# ---------- Lançamento (Feature 1) ----------
class LancamentoBase(BaseModel):
    produto_id: int
    quantidade: int = Field(default=1, gt=0)

class LancamentoCreate(LancamentoBase):
    # se vier vazio, o crud usa o preço do produto (ex.: Doce informa na hora)
    valor_unitario: Optional[Decimal] = Field(default=None, ge=0)

class LancamentoResponse(BaseModel):
    id: int
    produto: ProdutoResponse
    quantidade: int
    valor_unitario: Decimal
    data_compra: datetime

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        return self.quantidade * self.valor_unitario

    class Config:
        from_attributes = True

class LancamentoUpdate(BaseModel):
    produto_id: Optional[int] = None
    quantidade: Optional[int] = Field(default=None, gt=0)
    valor_unitario: Optional[Decimal] = Field(default=None, ge=0)


class ExtratoCliente(BaseModel):
    cliente: ClienteResponse
    itens: List[LancamentoResponse]
    total: Decimal
