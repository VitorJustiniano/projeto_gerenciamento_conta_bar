from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import streamlit as st

import api

FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")
CENTAVOS = Decimal("0.01")


# ---------- formatação ----------
def brl(valor) -> str:
    """9.5 -> 'R$ 9,50' | 1234.5 -> 'R$ 1.234,50'"""
    texto = f"{Decimal(str(valor)):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def para_decimal(valor) -> Decimal:
    """número digitado na tela -> Decimal com 2 casas (sem erro de float)"""
    return Decimal(str(valor)).quantize(CENTAVOS)


def data_local(iso: str) -> datetime:
    """
    a API devolve a hora sem fuso (o Postgres do Docker grava em UTC)
    aqui converte para o horário de Brasília
    """
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(FUSO_LOCAL)


def rotulo_cliente(cliente) -> str:
    if cliente.get("apelido"):
        return f"{cliente['nome']} ({cliente['apelido']})"
    return cliente["nome"]


def rotulo_produto(produto) -> str:
    return f"{produto['nome']} — {brl(produto['preco_atual'])}"


# ---------- avisos ----------
def mostrar_aviso():
    """
    mostra (uma vez) o aviso guardado antes do st.rerun()
    o aviso é guardado em session_state porque o rerun apagaria uma mensagem mostrada na hora
    """
    aviso = st.session_state.pop("aviso", None)
    if aviso:
        tipo, texto = aviso
        st.toast(texto, icon="✅" if tipo == "ok" else "⚠️")


# ---------- chamadas à API ----------
def carregar(funcao, *args, **kwargs):
    """chama a API para buscar dados; se falhar, mostra o erro na tela e devolve None"""
    try:
        return funcao(*args, **kwargs)
    except api.ApiError as erro:
        st.error(erro)
        return None


def executar(funcao, *args, sucesso: str, **kwargs):
    """
    roda uma ação na API (criar, editar, excluir)
    deu certo: guarda o aviso de sucesso e devolve a resposta da API
    deu erro: mostra o erro na tela e devolve None
    """
    try:
        resposta = funcao(*args, **kwargs)
    except api.ApiError as erro:
        st.error(erro)
        return None
    st.session_state["aviso"] = ("ok", sucesso)
    return resposta


def aplicar_lote(operacoes):
    """
    operacoes = lista de (descricao, funcao, args, kwargs)
    executa todas, guarda o resumo no aviso e deixa quem chamou recarregar a tela
    """
    feitas, erros = 0, []
    for descricao, funcao, args, kwargs in operacoes:
        try:
            funcao(*args, **kwargs)
            feitas += 1
        except api.ApiError as erro:
            erros.append(f"{descricao}: {erro}")

    if erros:
        st.session_state["aviso"] = (
            "erro",
            f"{feitas} salva(s), {len(erros)} com erro - " + " | ".join(erros),
        )
    else:
        st.session_state["aviso"] = ("ok", f"{feitas} alteração(ões) salva(s).")


# ---------- reset de formulários e tabelas ----------
def sufixo(chave: str) -> str:
    """
    número que muda quando chamamos limpar(chave)
    entra na chave dos campos/tabelas: chave nova = campo novo, vazio e sem seleção
    """
    return f"{chave}_{st.session_state.get(f'_versao_{chave}', 0)}"


def limpar(chave: str):
    st.session_state[f"_versao_{chave}"] = st.session_state.get(f"_versao_{chave}", 0) + 1