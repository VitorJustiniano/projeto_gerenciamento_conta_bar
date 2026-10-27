from decimal import Decimal

import pandas as pd
import streamlit as st

import api
import utils


def _descricao_item(item) -> str:
    quando = utils.data_local(item["data_compra"]).strftime("%d/%m %H:%M")
    return f"{item['quantidade']}x {item['produto']['nome']} ({quando})"


def _chave_valor(produto) -> str:
    # o preço entra na chave: se o preço do produto mudar, o campo volta a sugerir o preço novo
    return f"valor_novo_{produto['id']}_{produto['preco_atual']}"


# =====================================================================
# coluna da esquerda: lista e cadastro de clientes
# =====================================================================
def _novo_cliente():
    s = utils.sufixo("cliente")
    with st.form(f"form_{s}"):
        nome = st.text_input("Nome *", key=f"nome_{s}", max_chars=120)
        apelido = st.text_input("Apelido", key=f"apelido_{s}", max_chars=60)
        telefone = st.text_input("Telefone", key=f"telefone_{s}", max_chars=20)
        cpf = st.text_input("CPF (opcional, só números)", key=f"cpf_{s}", max_chars=11)
        enviar = st.form_submit_button("Cadastrar cliente", type="primary")

    if not enviar:
        return
    nome = nome.strip()
    cpf = cpf.strip()
    if not nome:
        st.error("Informe o nome do cliente.")
        return
    if cpf and not (cpf.isascii() and cpf.isdigit() and len(cpf) == 11):
        st.error("O CPF precisa ter 11 números, sem pontos nem traço.")
        return

    resposta = utils.executar(
        api.criar_cliente,
        nome,
        apelido.strip() or None,
        telefone.strip() or None,
        cpf or None,
        sucesso=f"Cliente {nome} cadastrado.",
    )
    if resposta:
        st.session_state["cliente_id"] = resposta["id"]  # já abre o extrato dele
        utils.limpar("cliente")
        utils.limpar("tabela_clientes")
        st.rerun()


def _lista():
    st.subheader("Clientes")
    busca = st.text_input(
        "Buscar cliente",
        placeholder="Nome ou apelido",
        key="busca_cliente",
        label_visibility="collapsed",
    )
    clientes = utils.carregar(api.buscar_clientes, busca or None)
    if clientes is None:
        return

    with st.expander("➕ Novo cliente", expanded=not clientes and not busca):
        _novo_cliente()

    if not clientes:
        st.info("Nenhum cliente encontrado." if busca else "Nenhum cliente cadastrado ainda.")
        return

    linhas = [
        {"Nome": c["nome"], "Apelido": c["apelido"] or "", "Telefone": c["telefone"] or ""}
        for c in clientes
    ]
    # a busca entra na chave: ao filtrar, a seleção anterior não aponta para outra pessoa
    evento = st.dataframe(
        linhas,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"tabela_{utils.sufixo('tabela_clientes')}_{busca}",
    )
    marcadas = evento.selection.rows
    if marcadas:
        st.session_state["cliente_id"] = clientes[marcadas[0]]["id"]
    st.caption(f"{len(clientes)} cliente(s). Clique numa linha para abrir o extrato.")


# =====================================================================
# coluna da direita: painel do cliente selecionado
# =====================================================================
def _aba_extrato(cliente, itens, total):
    if not itens:
        st.info("Esse cliente não tem nada no fiado.")
        return

    originais = {i["id"]: i for i in itens}
    df = pd.DataFrame(
        [
            {
                "id": i["id"],
                "Data": utils.data_local(i["data_compra"]).strftime("%d/%m/%Y %H:%M"),
                "Item": i["produto"]["nome"],
                "Qtd": i["quantidade"],
                "Valor unit. (R$)": float(i["valor_unitario"]),
                "Subtotal": utils.brl(i["subtotal"]),
                "Excluir": False,
            }
            for i in itens
        ]
    )

    # a chave muda depois de salvar ou lançar item: a tabela recarrega com os dados novos
    chave = utils.sufixo(f"editor_{cliente['id']}")
    editado = st.data_editor(
        df,
        hide_index=True,
        key=f"editor_{chave}",
        disabled=["id", "Data", "Item", "Subtotal"],
        column_config={
            "id": None,
            "Qtd": st.column_config.NumberColumn(
                "Qtd", min_value=1, step=1, required=True
            ),
            "Valor unit. (R$)": st.column_config.NumberColumn(
                "Valor unit. (R$)", min_value=0.0, step=0.5, format="%.2f", required=True
            ),
            "Excluir": st.column_config.CheckboxColumn("Excluir"),
        },
    )
    st.caption(
        "Edite Qtd e Valor direto na tabela, ou marque Excluir. "
        "Subtotal e total atualizam depois de salvar."
    )
    st.markdown(f"**Total em aberto: {utils.brl(total)}**")

    # descobre o que mudou em relação ao que veio da API
    alteracoes, exclusoes = [], []
    for _, linha in editado.iterrows():
        original = originais[int(linha["id"])]
        if linha["Excluir"]:
            exclusoes.append(original)
            continue

        campos = {}
        qtd = linha["Qtd"]
        if not pd.isna(qtd) and int(qtd) != original["quantidade"]:
            campos["quantidade"] = int(qtd)

        valor = linha["Valor unit. (R$)"]
        if not pd.isna(valor):
            novo_valor = utils.para_decimal(valor)
            if novo_valor != utils.para_decimal(original["valor_unitario"]):
                campos["valor_unitario"] = novo_valor

        if campos:
            alteracoes.append((original, campos))

    pendentes = len(alteracoes) + len(exclusoes)
    confirmado = True
    if exclusoes:
        resumo = ", ".join(_descricao_item(i) for i in exclusoes)
        st.warning(f"Serão excluídos: {resumo}.")
        confirmado = st.checkbox("Confirmo a exclusão", key=f"conf_{chave}")

    if st.button(
        f"Salvar alterações ({pendentes})",
        type="primary",
        disabled=pendentes == 0 or not confirmado,
        key=f"salvar_{chave}",
    ):
        operacoes = [
            (_descricao_item(o), api.editar_lancamento, (o["id"],), campos)
            for o, campos in alteracoes
        ] + [
            (_descricao_item(o), api.excluir_lancamento, (o["id"],), {})
            for o in exclusoes
        ]
        utils.aplicar_lote(operacoes)
        utils.limpar(f"editor_{cliente['id']}")
        st.rerun()

    with st.expander("Resumo por dia"):
        por_dia = {}
        for i in itens:
            dia = utils.data_local(i["data_compra"]).date()
            por_dia[dia] = por_dia.get(dia, Decimal("0")) + Decimal(str(i["subtotal"]))
        st.dataframe(
            [
                {"Dia": dia.strftime("%d/%m/%Y"), "Total do dia": utils.brl(valor)}
                for dia, valor in sorted(por_dia.items(), reverse=True)
            ],
            hide_index=True,
        )


def _adicionar_item(cliente_id: int, produto: dict, preco: Decimal):
    """
    roda ANTES da tela recarregar (on_click), por isso pode limpar os campos
    se o valor digitado for igual ao preço cadastrado, não manda valor (a API usa o do produto)
    """
    qtd = st.session_state["qtd_novo"]
    chave = _chave_valor(produto)
    valor = utils.para_decimal(st.session_state[chave])

    try:
        api.lancar(cliente_id, produto["id"], qtd, None if valor == preco else valor)
    except api.ApiError as erro:
        st.session_state["aviso"] = ("erro", str(erro))
        return

    st.session_state["aviso"] = ("ok", f"{qtd}x {produto['nome']} lançado.")
    st.session_state["qtd_novo"] = 1
    st.session_state[chave] = float(preco)
    utils.limpar(f"editor_{cliente_id}")


def _aba_lancar(cliente):
    produtos = utils.carregar(api.listar_produtos)
    if produtos is None:
        return
    if not produtos:
        st.info("Nenhum produto cadastrado. Cadastre na aba Produtos.")
        return

    produto = st.selectbox(
        "Produto",
        produtos,
        format_func=utils.rotulo_produto,
        index=None,
        placeholder="Digite para buscar o produto...",
        key=f"produto_novo_{cliente['id']}",
    )
    if produto is None:
        return

    preco = Decimal(str(produto["preco_atual"]))
    chave = _chave_valor(produto)
    st.session_state.setdefault("qtd_novo", 1)
    st.session_state.setdefault(chave, float(preco))

    c1, c2 = st.columns(2)
    qtd = c1.number_input("Quantidade", min_value=1, step=1, key="qtd_novo")
    valor = c2.number_input(
        "Valor unitário (R$)", min_value=0.0, step=0.5, format="%.2f", key=chave
    )

    st.caption(f"Subtotal: {utils.brl(Decimal(str(valor)) * qtd)}")
    if valor == 0:
        st.warning("Informe o valor deste item (produto de preço livre).")

    st.button(
        "Adicionar ao fiado",
        type="primary",
        disabled=valor == 0,
        on_click=_adicionar_item,
        args=(cliente["id"], produto, preco),
        key=f"adicionar_{cliente['id']}",
    )


def _aba_dados(cliente, total):
    s = utils.sufixo(f"dados_{cliente['id']}")
    with st.form(f"form_{s}"):
        nome = st.text_input("Nome *", value=cliente["nome"], key=f"nome_{s}", max_chars=120)
        apelido = st.text_input(
            "Apelido", value=cliente.get("apelido") or "", key=f"apelido_{s}", max_chars=60
        )
        telefone = st.text_input(
            "Telefone", value=cliente.get("telefone") or "", key=f"telefone_{s}", max_chars=20
        )
        cpf = st.text_input(
            "CPF (deixe em branco para manter o atual)",
            key=f"cpf_{s}",
            max_chars=11,
            help="Por segurança, o CPF cadastrado não é exibido.",
        )
        enviar = st.form_submit_button("Salvar dados", type="primary")

    if enviar:
        nome = nome.strip()
        cpf = cpf.strip()
        if not nome:
            st.error("Informe o nome do cliente.")
        elif cpf and not (cpf.isascii() and cpf.isdigit() and len(cpf) == 11):
            st.error("O CPF precisa ter 11 números, sem pontos nem traço.")
        else:
            campos = {
                "nome": nome,
                "apelido": apelido.strip() or None,
                "telefone": telefone.strip() or None,
            }
            if cpf:
                campos["cpf"] = cpf
            if utils.executar(
                api.atualizar_cliente, cliente["id"], sucesso="Dados atualizados.", **campos
            ):
                utils.limpar(f"dados_{cliente['id']}")
                utils.limpar("tabela_clientes")
                st.rerun()

    st.divider()
    st.markdown("**Desativar cliente**")
    if total > 0:
        st.warning(
            f"Este cliente tem {utils.brl(total)} em aberto. "
            "Desativar não apaga a dívida, mas ele some da lista."
        )
    st.caption(
        "Cliente desativado some da lista e não recebe novos lançamentos. "
        "Por enquanto não há como reativar pela tela."
    )
    confirmar = st.checkbox(
        "Confirmo que quero desativar este cliente", key=f"conf_desativar_{cliente['id']}"
    )
    if st.button(
        "Desativar cliente", disabled=not confirmar, key=f"desativar_{cliente['id']}"
    ):
        if utils.executar(
            api.atualizar_cliente, cliente["id"], sucesso="Cliente desativado.", ativo=False
        ):
            st.session_state.pop("cliente_id", None)
            utils.limpar("tabela_clientes")
            st.rerun()


def _painel(cliente_id: int):
    extrato = utils.carregar(api.extrato, cliente_id)
    if extrato is None:
        st.session_state.pop("cliente_id", None)
        return

    cliente = extrato["cliente"]
    itens = extrato["itens"]
    total = Decimal(str(extrato["total"]))

    topo, fechar = st.columns([5, 1])
    topo.subheader(utils.rotulo_cliente(cliente))
    if fechar.button("Fechar", key="fechar_painel"):
        st.session_state.pop("cliente_id", None)
        utils.limpar("tabela_clientes")
        st.rerun()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total em aberto", utils.brl(total))
    m2.metric("Itens lançados", len(itens))
    ultima = max((utils.data_local(i["data_compra"]) for i in itens), default=None)
    m3.metric("Última compra", ultima.strftime("%d/%m/%Y") if ultima else "—")

    aba_extrato, aba_lancar, aba_dados = st.tabs(
        ["📋 Extrato e histórico", "➕ Lançar item", "✏️ Dados do cliente"]
    )
    with aba_extrato:
        _aba_extrato(cliente, itens, total)
    with aba_lancar:
        _aba_lancar(cliente)
    with aba_dados:
        _aba_dados(cliente, total)


def render():
    col_lista, col_painel = st.columns([1, 2], gap="large")

    with col_lista:
        _lista()

    with col_painel:
        cliente_id = st.session_state.get("cliente_id")
        if cliente_id is None:
            st.info("Selecione um cliente na lista para ver o extrato e o histórico.")
        else:
            _painel(cliente_id)