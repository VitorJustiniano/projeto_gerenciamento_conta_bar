import streamlit as st

import utils
from telas import categorias, clientes, produtos

st.set_page_config(page_title="Controle de Fiado", page_icon="🧾", layout="wide")

utils.mostrar_aviso()

st.title("🧾 Controle de Fiado")
st.caption("Cadastros, extrato e histórico dos clientes")

aba_clientes, aba_produtos, aba_categorias = st.tabs(
    ["👤 Clientes", "📦 Produtos", "🏷️ Categorias"]
)

with aba_clientes:
    clientes.render()

with aba_produtos:
    produtos.render()

with aba_categorias:
    categorias.render()