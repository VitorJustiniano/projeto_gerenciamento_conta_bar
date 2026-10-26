from pydantic import BaseModel, Field, computed_field, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional, List


# ---------- Categoria ----------
class CategoriaBase(BaseModel):
    nome: str = Field(min_length=1, max_length=60)

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Produto ----------
class ProdutoBase(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    categoria_id: int
    preco_atual: Decimal = Field(ge=0, max_digits=10, decimal_places=2)

class ProdutoCreate(ProdutoBase):
    pass

class ProdutoResponse(ProdutoBase):
    id: int
    ativo: bool
    categoria: CategoriaResponse

    model_config = ConfigDict(from_attributes=True)
    
class ProdutoUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=120)
    categoria_id: Optional[int] = None
    preco_atual: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    ativo: Optional[bool] = None


# ---------- Cliente ----------
class ClienteBase(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    apelido: Optional[str] = Field(default=None, max_length=60)
    telefone: Optional[str] = Field(default=None, max_length=20)
    cpf: Optional[str] = Field(default=None, pattern=r"^\d{11}$")

class ClienteCreate(ClienteBase):
    pass

class ClienteResponse(BaseModel):
    id: int
    nome: str
    apelido: Optional[str] = None
    telefone: Optional[str] = None
    ativo: bool

    model_config = ConfigDict(from_attributes=True)

class ClienteUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=120)
    apelido: Optional[str] = Field(default=None, max_length=60)
    telefone: Optional[str] = Field(default=None, max_length=20)
    cpf: Optional[str] = Field(default=None, pattern=r"^\d{11}$")
    ativo: Optional[bool] = None


# ---------- Lançamento (Feature 1) ----------
class LancamentoBase(BaseModel):
    produto_id: int
    quantidade: int = Field(default=1, gt=0)

class LancamentoCreate(LancamentoBase):
    # se vier vazio, o crud usa o preço do produto (ex.: Doce informa na hora)
    valor_unitario: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)

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

    model_config = ConfigDict(from_attributes=True)

class LancamentoUpdate(BaseModel):
    produto_id: Optional[int] = None
    quantidade: Optional[int] = Field(default=None, gt=0)
    valor_unitario: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class ExtratoCliente(BaseModel):
    cliente: ClienteResponse
    itens: List[LancamentoResponse]
    total: Decimal
