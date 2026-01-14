# FinanceManager - Aplicativo de Finanças Pessoais (Python)

Este projeto é um gerenciador financeiro completo construído em Python, apresentando um backend SQLite e três interfaces de usuário (UIs) diferentes:

1.  **Desktop (CustomTkinter):** Uma aplicação nativa para Windows/Linux/Mac.
2.  **Web App (Streamlit):** Uma aplicação web interativa e baseada em dados.
3.  **Web App (Flask):** Uma aplicação web tradicional com templates Jinja2.

## Funcionalidades

* Adicionar, excluir e listar transações (Receitas/Despesas).
* Associar transações a categorias.
* Filtrar transações por data, categoria e pesquisa de texto.
* Resumo do balanço (Receitas, Despesas, Saldo) que atualiza com os filtros.
* Exportar dados filtrados para Excel (.xlsx) e PDF (.pdf).
* Geração de gráficos de despesas (no app Desktop e Streamlit).
* Paginação (nos apps Flask e Streamlit) para lidar com grandes volumes de dados.

## Estrutura do Projeto