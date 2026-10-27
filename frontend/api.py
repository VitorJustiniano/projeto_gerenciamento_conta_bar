import os
from decimal import Decimal
from typing import Optional

import requests

# dentro do Docker o backend é "http://backend:8000"; rodando local, localhost
API_URL = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT = 10


class ApiError(Exception):
    """erro da API (ou falha de conexão), já com a mensagem pronta para mostrar na tela"""


def _mensagem(resposta: requests.Response) -> str:
    """
    transforma a resposta de erro em texto
    404/409/400 vêm como {"detail": "texto"}; 422 vem como lista de campos inválidos
    """
    try:
        detalhe = resposta.json().get("detail")
    except ValueError:
        return f"Erro {resposta.status_code}"

    if isinstance(detalhe, list):
        problemas = []
        for erro in detalhe:
            campo = ".".join(str(parte) for parte in erro.get("loc", [])[1:])
            problemas.append(f"{campo}: {erro.get('msg')}")
        return "Dados inválidos - " + "; ".join(problemas)

    return detalhe or f"Erro {resposta.status_code}"


def _request(metodo: str, caminho: str, **kwargs):
    try:
        resposta = requests.request(
            metodo, f"{API_URL}{caminho}", timeout=TIMEOUT, **kwargs
        )
    except requests.RequestException:
        raise ApiError("Não consegui falar com o servidor. Ele está ligado?") from None

    if resposta.status_code >= 400:
        raise ApiError(_mensagem(resposta))
    if not resposta.content:
        return None
    return resposta.json()


# ---------- categorias ----------
def listar_categorias():
    return _request("GET", "/categorias/")


def criar_categoria(nome: str):
    return _request("POST", "/categorias/", json={"nome": nome})


# ---------- produtos ----------
def listar_produtos(busca: Optional[str] = None):
    """lista os produtos ativos"""
    params = {"busca": busca} if busca else None
    return _request("GET", "/produtos/", params=params)


def criar_produto(nome: str, categoria_id: int, preco: Decimal):
    corpo = {"nome": nome, "categoria_id": categoria_id, "preco_atual": str(preco)}
    return _request("POST", "/produtos/", json=corpo)


def atualizar_produto(produto_id: int, **campos):
    """campos aceitos: nome, categoria_id, preco_atual (Decimal) e ativo"""
    if "preco_atual" in campos:
        campos["preco_atual"] = str(campos["preco_atual"])
    return _request("PUT", f"/produtos/{produto_id}", json=campos)


# ---------- clientes ----------
def buscar_clientes(busca: Optional[str] = None):
    """lista os clientes ativos; 'busca' procura no nome ou no apelido"""
    params = {"busca": busca} if busca else None
    return _request("GET", "/clientes/", params=params)


def criar_cliente(
    nome: str,
    apelido: Optional[str] = None,
    telefone: Optional[str] = None,
    cpf: Optional[str] = None,
):
    corpo = {"nome": nome}
    if apelido:
        corpo["apelido"] = apelido
    if telefone:
        corpo["telefone"] = telefone
    if cpf:
        corpo["cpf"] = cpf
    return _request("POST", "/clientes/", json=corpo)


def atualizar_cliente(cliente_id: int, **campos):
    """campos aceitos: nome, apelido, telefone, cpf e ativo (None limpa apelido/telefone)"""
    return _request("PUT", f"/clientes/{cliente_id}", json=campos)


# ---------- fiado (Feature 1) ----------
def extrato(cliente_id: int):
    """cliente + itens + total"""
    return _request("GET", f"/clientes/{cliente_id}/extrato")


def lancar(
    cliente_id: int,
    produto_id: int,
    quantidade: int,
    valor_unitario: Optional[Decimal] = None,
):
    """
    lança um item no fiado
    valor_unitario vazio = a API usa o preço cadastrado do produto
    """
    corpo = {"produto_id": produto_id, "quantidade": quantidade}
    if valor_unitario is not None:
        corpo["valor_unitario"] = str(valor_unitario)  # texto: não perde centavo
    return _request("POST", f"/clientes/{cliente_id}/lancamentos/", json=corpo)


def editar_lancamento(
    lancamento_id: int,
    quantidade: Optional[int] = None,
    valor_unitario: Optional[Decimal] = None,
):
    """altera só o que for informado"""
    corpo = {}
    if quantidade is not None:
        corpo["quantidade"] = quantidade
    if valor_unitario is not None:
        corpo["valor_unitario"] = str(valor_unitario)
    return _request("PUT", f"/lancamentos/{lancamento_id}", json=corpo)


def excluir_lancamento(lancamento_id: int):
    """exclusão lógica: o item some do extrato e do total"""
    return _request("DELETE", f"/lancamentos/{lancamento_id}")