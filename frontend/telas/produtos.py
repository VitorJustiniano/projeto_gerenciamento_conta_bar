import pandas as pd
import streamlit as st

import api
import utils


def _novo_produto(categorias):
    s = utils.sufixo("produto")
    with st.form(f"form_{s}"):
        st.markdown("**Novo produto**")
        nome = st.text_input(
            "Nome", key=f"nome_{s}", max_chars=120, placeholder="Ex.: Coca 600ml"
        )
        categoria = st.selectbox(
            "Categoria",
            categorias,
            format_func=lambda c: c["nome"],
            index=None,
            placeholder="Escolha...",
            key=f"categoria_{s}",
        )
        preco = st.number_input(
            "Preço (R$)", min_value=0.0, step=0.5, format="%.2f", key=f"preco_{s}"
        )
        st.caption(
            "Produto de preço livre (como o Doce)? Cadastre com 0,00 "
            "e informe o valor em cada lançamento."
        )
        enviar = st.form_submit_button("Cadastrar produto", type="primary")

    if not enviar:
        return
    nome = nome.strip()
    if not nome:
        st.error("Informe o nome do produto.")
        return
    if categoria is None:
        st.error("Escolha uma categoria.")
        return

    resposta = utils.executar(
        api.criar_produto,
        nome,
        categoria["id"],
        utils.para_decimal(preco),
        sucesso=f"Produto {nome} cadastrado.",
    )
    if resposta:
        utils.limpar("produto")
        st.rerun()


def _tabela(produtos, categorias, contexto: str):
    """tabela editável: muda nome, categoria e preço direto na célula; 'Desativar' tira da lista"""
    nomes_categorias = [c["nome"] for c in categorias]
    id_por_nome = {c["nome"]: c["id"] for c in categorias}
    originais = {p["id"]: p for p in produtos}

    df = pd.DataFrame(
        [
            {
                "id": p["id"],
                "Nome": p["nome"],
                "Categoria": p["categoria"]["nome"],
                "Preço (R$)": float(p["preco_atual"]),
                "Desativar": False,
            }
            for p in produtos
        ]
    )

    # a chave muda com os filtros e depois de salvar, para a tabela não misturar edições
    chave = utils.sufixo("editor_produtos")
    editado = st.data_editor(
        df,
        hide_index=True,
        key=f"editor_{chave}_{contexto}",
        disabled=["id"],
        column_config={
            "id": None,
            "Nome": st.column_config.TextColumn("Nome", required=True, max_chars=120),
            "Categoria": st.column_config.SelectboxColumn(
                "Categoria", options=nomes_categorias, required=True
            ),
            "Preço (R$)": st.column_config.NumberColumn(
                "Preço (R$)", min_value=0.0, step=0.5, format="%.2f", required=True
            ),
            "Desativar": st.column_config.CheckboxColumn("Desativar"),
        },
    )

    # descobre o que mudou em relação ao que veio da API
    alteracoes, desativar = [], []
    for _, linha in editado.iterrows():
        original = originais[int(linha["id"])]
        if linha["Desativar"]:
            desativar.append(original)
            continue

        campos = {}
        nome = linha["Nome"]
        if isinstance(nome, str) and nome.strip() and nome.strip() != original["nome"]:
            campos["nome"] = nome.strip()

        categoria = linha["Categoria"]
        if categoria in id_por_nome and categoria != original["categoria"]["nome"]:
            campos["categoria_id"] = id_por_nome[categoria]

        preco = linha["Preço (R$)"]
        if not pd.isna(preco):
            novo_preco = utils.para_decimal(preco)
            if novo_preco != utils.para_decimal(original["preco_atual"]):
                campos["preco_atual"] = novo_preco

        if campos:
            alteracoes.append((original, campos))

    pendentes = len(alteracoes) + len(desativar)
    confirmado = True
    if desativar:
        nomes = ", ".join(p["nome"] for p in desativar)
        st.warning(
            f"Serão desativados: {nomes}. Produto desativado some das listas e não "
            "pode mais ser lançado (por enquanto não há como reativar pela tela)."
        )
        confirmado = st.checkbox("Confirmo a desativação", key=f"conf_produtos_{chave}")

    if st.button(
        f"Salvar alterações ({pendentes})",
        type="primary",
        disabled=pendentes == 0 or not confirmado,
        key=f"salvar_produtos_{chave}",
    ):
        operacoes = [
            (original["nome"], api.atualizar_produto, (original["id"],), campos)
            for original, campos in alteracoes
        ] + [
            (original["nome"], api.atualizar_produto, (original["id"],), {"ativo": False})
            for original in desativar
        ]
        utils.aplicar_lote(operacoes)
        utils.limpar("editor_produtos")
        st.rerun()


def render():
    categorias = utils.carregar(api.listar_categorias)
    if categorias is None:
        return

    st.subheader("Produtos")
    if not categorias:
        st.info("Cadastre pelo menos uma categoria na aba Categorias antes de cadastrar produtos.")
        return

    col_form, col_lista = st.columns([1, 2], gap="large")

    with col_form:
        _novo_produto(categorias)

    with col_lista:
        f1, f2 = st.columns([2, 1])
        busca = f1.text_input(
            "Buscar produto", placeholder="Parte do nome", key="busca_produto"
        )
        filtro = f2.selectbox(
            "Categoria", ["Todas"] + [c["nome"] for c in categorias], key="filtro_categoria"
        )

        produtos = utils.carregar(api.listar_produtos, busca or None)
        if produtos is None:
            return
        if filtro != "Todas":
            produtos = [p for p in produtos if p["categoria"]["nome"] == filtro]
        if not produtos:
            st.info("Nenhum produto encontrado.")
            return

        st.caption(
            f"{len(produtos)} produto(s). Edite direto na tabela e clique em Salvar. "
            "Preço novo vale só para lançamentos futuros: o que já foi lançado "
            "mantém o preço da época."
        )
        _tabela(produtos, categorias, contexto=f"{busca}_{filtro}")