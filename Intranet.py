# --- TELA 6: DASHBOARD GERENCIAL ---
    elif menu == "📊 Dashboard":
        st.markdown("# 📊 Dashboard Gerencial")
        
        # Carregamento das bases de dados
        df_os_dash = carregar_banco_os()
        try:
            df_compras_dash = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
        except Exception:
            df_compras_dash = pd.DataFrame()

        # 1. Tratamento de Datas para Filtros Globais (Dia, Mês, Ano)
        if not df_os_dash.empty:
            # O.S. usa formato %d/%m/%Y %H:%M
            df_os_dash['Dt_Parsed'] = pd.to_datetime(df_os_dash['Data_Criacao'].str.split(' ').str[0], format='%d/%m/%Y', errors='coerce')
            df_os_dash['Ano'] = df_os_dash['Dt_Parsed'].dt.year.fillna(0).astype(int).astype(str)
            df_os_dash['Mes'] = df_os_dash['Dt_Parsed'].dt.month.fillna(0).astype(int).astype(str)
            df_os_dash['Dia'] = df_os_dash['Dt_Parsed'].dt.day.fillna(0).astype(int).astype(str)
            
        if not df_compras_dash.empty:
            # Compras usa formato %Y-%m-%d %H:%M
            df_compras_dash['Dt_Parsed'] = pd.to_datetime(df_compras_dash['Data_Solicitacao'].str.split(' ').str[0], format='%Y-%m-%d', errors='coerce')
            df_compras_dash['Ano'] = df_compras_dash['Dt_Parsed'].dt.year.fillna(0).astype(int).astype(str)
            df_compras_dash['Mes'] = df_compras_dash['Dt_Parsed'].dt.month.fillna(0).astype(int).astype(str)
            df_compras_dash['Dia'] = df_compras_dash['Dt_Parsed'].dt.day.fillna(0).astype(int).astype(str)

        # 2. Configuração dos Filtros Globais
        st.markdown("### 🔍 Filtros Globais de Período")
        col_f1, col_f2, col_f3 = st.columns(3)
        
        todos_anos = set()
        todos_meses = set()
        todos_dias = set()
        
        if not df_os_dash.empty:
            todos_anos.update(df_os_dash['Ano'].unique())
            todos_meses.update(df_os_dash['Mes'].unique())
            todos_dias.update(df_os_dash['Dia'].unique())
        if not df_compras_dash.empty:
            todos_anos.update(df_compras_dash['Ano'].unique())
            todos_meses.update(df_compras_dash['Mes'].unique())
            todos_dias.update(df_compras_dash['Dia'].unique())

        lista_anos = ["Todos"] + sorted([x for x in todos_anos if x != "0"], reverse=True)
        lista_meses = ["Todos"] + sorted([x for x in todos_meses if x != "0"])
        lista_dias = ["Todos"] + sorted([x for x in todos_dias if x != "0"])

        with col_f1:
            f_ano = st.selectbox("Ano", lista_anos)
        with col_f2:
            f_mes = st.selectbox("Mês", lista_meses)
        with col_f3:
            f_dia = st.selectbox("Dia", lista_dias)

        # 3. Aplicação dos Filtros
        if f_ano != "Todos":
            df_os_dash = df_os_dash[df_os_dash['Ano'] == f_ano]
            df_compras_dash = df_compras_dash[df_compras_dash['Ano'] == f_ano]
        if f_mes != "Todos":
            df_os_dash = df_os_dash[df_os_dash['Mes'] == f_mes]
            df_compras_dash = df_compras_dash[df_compras_dash['Mes'] == f_mes]
        if f_dia != "Todos":
            df_os_dash = df_os_dash[df_os_dash['Dia'] == f_dia]
            df_compras_dash = df_compras_dash[df_compras_dash['Dia'] == f_dia]

        # Configuração de Estilo Power BI (Fundos Transparentes)
        layout_powerbi = {
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'font': {'color': 'white'}
        }

        st.markdown("---")
        
        # 4. Divisão em Duas Janelas (Abas)
        aba_dash_os, aba_dash_compras = st.tabs(["🔧 Indicadores de O.S.", "🛒 Indicadores de Compras"])

        with aba_dash_os:
            if df_os_dash.empty:
                st.info("Nenhuma Ordem de Serviço encontrada para o período selecionado.")
            else:
                # Métricas Rápidas
                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric("Total de O.S. Abertas", len(df_os_dash[df_os_dash['Status'] == 'Em Aberto']))
                c_m2.metric("O.S. em Andamento", len(df_os_dash[df_os_dash['Status'] == 'Em Andamento']))
                c_m3.metric("O.S. Finalizadas", len(df_os_dash[df_os_dash['Status'] == 'Finalizada']))
                
                # Gráficos
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    fig_os_status = px.pie(
                        df_os_dash, 
                        names='Status', 
                        title='Distribuição por Status',
                        hole=0.45,
                        color_discrete_sequence=px.colors.sequential.Teal
                    )
                    fig_os_status.update_layout(**layout_powerbi)
                    st.plotly_chart(fig_os_status, use_container_width=True)
                    
                with col_g2:
                    df_setor = df_os_dash['Setor'].value_counts().reset_index()
                    df_setor.columns = ['Setor', 'Quantidade']
                    fig_os_setor = px.bar(
                        df_setor, 
                        x='Setor', 
                        y='Quantidade', 
                        title='O.S. Solicitadas por Setor',
                        color='Setor',
                        template='plotly_dark'
                    )
                    fig_os_setor.update_layout(**layout_powerbi, showlegend=False)
                    st.plotly_chart(fig_os_setor, use_container_width=True)

        with aba_dash_compras:
            if df_compras_dash.empty:
                st.info("Nenhuma Solicitação de Compra encontrada para o período selecionado.")
            else:
                # Métricas Rápidas
                c_mc1, c_mc2, c_mc3 = st.columns(3)
                c_mc1.metric("Total de Itens Solicitados", len(df_compras_dash))
                c_mc2.metric("Compras Pendentes", len(df_compras_dash[df_compras_dash['Status'] == 'Compra em Aberta']))
                c_mc3.metric("Compras Realizadas", len(df_compras_dash[df_compras_dash['Status'] == 'Compra Realizada']))
                
                # Gráficos
                col_gc1, col_gc2 = st.columns(2)
                with col_gc1:
                    fig_comp_status = px.pie(
                        df_compras_dash, 
                        names='Status', 
                        title='Status das Solicitações',
                        hole=0.45,
                        color_discrete_sequence=px.colors.sequential.Burg
                    )
                    fig_comp_status.update_layout(**layout_powerbi)
                    st.plotly_chart(fig_comp_status, use_container_width=True)
                    
                with col_gc2:
                    df_cat = df_compras_dash['Categoria'].value_counts().reset_index()
                    df_cat.columns = ['Categoria', 'Quantidade']
                    fig_comp_cat = px.bar(
                        df_cat, 
                        x='Categoria', 
                        y='Quantidade', 
                        title='Volume de Compras por Categoria',
                        color='Categoria',
                        template='plotly_dark'
                    )
                    fig_comp_cat.update_layout(**layout_powerbi, showlegend=False)
                    st.plotly_chart(fig_comp_cat, use_container_width=True)
