import streamlit as st

import api
import utils


def render():
    categorias = utils.carregar(api.listar_categorias)
    produtos = utils.carregar(api.listar_produtos)
    if categorias is None or produtos is None:
        return

    st.subheader("Categorias")
    st.caption(
        "Agrupam os produtos (Salgado, Cerveja, Refrigerante...). "
        "Por enquanto não dá para renomear nem excluir uma categoria."
    )

    col_form, col_lista = st.columns([1, 2], gap="large")

    with col_form:
        s = utils.sufixo("categoria")
        with st.form(f"form_{s}"):
            st.markdown("**Nova categoria**")
            nome = st.text_input("Nome", key=f"nome_{s}", max_chars=60)
            enviar = st.form_submit_button("Cadastrar", type="primary")

        if enviar:
            nome = nome.strip()
            if not nome:
                st.error("Informe o nome da categoria.")
            elif utils.executar(
                api.criar_categoria, nome, sucesso=f"Categoria {nome} cadastrada."
            ):
                utils.limpar("categoria")
                st.rerun()

    with col_lista:
        if not categorias:
            st.info("Nenhuma categoria ainda. Comece cadastrando ao lado.")
            return

        contagem = {}
        for produto in produtos:
            id_categoria = produto["categoria"]["id"]
            contagem[id_categoria] = contagem.get(id_categoria, 0) + 1

        linhas = [
            {"Categoria": c["nome"], "Produtos ativos": contagem.get(c["id"], 0)}
            for c in categorias
        ]
        st.dataframe(linhas, hide_index=True)
        st.caption(f"{len(categorias)} categoria(s)")