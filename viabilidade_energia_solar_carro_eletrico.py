import streamlit as st 
import pandas as pd
import plotly.express as px
import numpy as np

# -----------------------------
# Configuração inicial
# -----------------------------
st.set_page_config(page_title="Simulador Veículo elétrico + Solar", layout="wide")

st.title("🚗⚡ Simulador EV + Solar")
st.write("Compare custos de um veículo a combustão (ICE) com veículo elétrico (EV) com ou sem energia solar, considerando financiamento, O&M e inflação.")

# -----------------------------
# Entradas do usuário
# -----------------------------
st.sidebar.header("Parâmetros de Entrada — Uso e Preços Atuais")

km_mes = st.sidebar.slider("Km rodados por mês", 500, 5000, 1300, 100)
preco_gasolina = st.sidebar.slider("Preço da gasolina hoje (R$/L)", 4.0, 10.0, 6.4, 0.1)
consumo_ICE = st.sidebar.slider("Consumo ICE (km/L)", 5.0, 20.0, 12.0, 0.5)

eficiencia_EV = st.sidebar.slider("Eficiência EV (km/kWh)", 3.0, 10.0, 6.0, 0.1)
perdas_pct = st.sidebar.slider("Perdas de carga (%)", 0, 30, 10, 1)
tarifa_kWh = st.sidebar.slider("Tarifa de energia hoje (R$/kWh)", 0.5, 2.0, 1.0, 0.05)
producao_kWh_kWp_ano = st.sidebar.slider("Produção anual (kWh/kWp)", 1000, 2000, 1379, 10)

usar_solar = st.sidebar.checkbox("Usar energia solar para o EV", True)

st.sidebar.header("Parâmetros Econômicos")
inflacao_pct = st.sidebar.slider("Inflação (a.a.) [%]", 0.0, 20.0, 5.0, 0.1)
juros_fin_pct = st.sidebar.slider("Juros financiamento solar (a.a.) [%]", 0.0, 30.0, 15.0, 0.1)
prazo_fin_anos = st.sidebar.slider("Prazo do financiamento (anos)", 0, 15, 5, 1)

# converter percentuais para decimais
inflacao_aa = inflacao_pct / 100
juros_fin_aa = juros_fin_pct / 100

st.sidebar.header("Custos Fixos Mensais dos Veículos (R$)")
manutencao_ICE_mes = st.sidebar.number_input("Manutenção ICE (R$/mês)", min_value=0.0, value=300.0, step=50.0)
seguro_ICE_mes = st.sidebar.number_input("Seguro ICE (R$/mês)", min_value=0.0, value=250.0, step=50.0)

manutencao_EV_mes = st.sidebar.number_input("Manutenção EV (R$/mês)", min_value=0.0, value=150.0, step=50.0)
seguro_EV_mes = st.sidebar.number_input("Seguro EV (R$/mês)", min_value=0.0, value=200.0, step=50.0)


st.sidebar.header("CAPEX do Sistema Solar para o EV")
# Primeiro precisamos calcular o kWp necessário com base nas entradas atuais
kWh_mes_EV_base = (km_mes / eficiencia_EV) * (1 + perdas_pct/100)
kWp_solar_necessario = (kWh_mes_EV_base * 12) / producao_kWh_kWp_ano if usar_solar else 0.0

# Opção de informar CAPEX diretamente ou por custo/kWp
modo_capex = st.sidebar.radio("Como informar o CAPEX?", ["Direto (R$)", "Custo por kWp"], index=1)
if modo_capex == "Direto (R$)":
    CAPEX_solar_EV = st.sidebar.number_input("CAPEX_solar_EV (R$)", min_value=0.0, value=float(round(kWp_solar_necessario*4500, -2)), step=100.0, help="Se usar solar, valor total do sistema dedicado ao EV.")
else:
    custo_kWp = st.sidebar.number_input("Custo por kWp (R$/kWp)", min_value=0.0, value=4500.0, step=100.0)
    CAPEX_solar_EV = custo_kWp * kWp_solar_necessario if usar_solar else 0.0
    st.sidebar.caption(f"CAPEX estimado: R$ {CAPEX_solar_EV:,.2f}")

# -----------------------------
# Cálculos — mês 0 (base) e parâmetros
# -----------------------------
# ICE base (mês 1 sem inflação aplicada ainda)
combustivel_ICE_RS_base = (km_mes / consumo_ICE) * preco_gasolina
total_ICE_RS_base = combustivel_ICE_RS_base

# EV base (sem solar)
kWh_mes_EV = kWh_mes_EV_base
energia_EV_rede_RS_base = kWh_mes_EV * tarifa_kWh
total_EV_RS_rede_base = energia_EV_rede_RS_base

# Conversões anuais -> mensais (efeito composto)
def taxa_mensal_da_anual(t_anual):
    return (1 + t_anual) ** (1/12) - 1

inflacao_am = taxa_mensal_da_anual(inflacao_aa)
juros_fin_am = taxa_mensal_da_anual(juros_fin_aa)

# Financiamento Price (se houver CAPEX e prazo > 0)
n_meses = prazo_fin_anos * 12
if usar_solar and CAPEX_solar_EV > 0 and n_meses > 0 and juros_fin_am > -1:
    if juros_fin_am == 0:
        parcela_fin = CAPEX_solar_EV / n_meses
    else:
        parcela_fin = CAPEX_solar_EV * (juros_fin_am) / (1 - (1 + juros_fin_am) ** (-n_meses))
else:
    parcela_fin = 0.0

# O&M: 1% a.a. do CAPEX, distribuído por mês e corrigido por inflação mensal
oem_base_mensal = (0.01 * CAPEX_solar_EV) / 12 if usar_solar and CAPEX_solar_EV > 0 else 0.0

# -----------------------------
# Simulação de 25 anos (300 meses)
# -----------------------------
meses_total = 25 * 12
dados = []
economia_acumulada = 0.0
economia_acumulada_5anos = 0.0

for m in range(1, meses_total + 1):
    # Fatores de inflação acumulada até o mês m (mês 1 = fator 1.0)
    fator_inf = (1 + inflacao_am) ** (m - 1)

    # Custos ICE e EV-rede com inflação
    custo_ICE = (total_ICE_RS_base * fator_inf) + (manutencao_ICE_mes + seguro_ICE_mes) * fator_inf
    custo_EV_rede = (total_EV_RS_rede_base * fator_inf) + (manutencao_EV_mes + seguro_EV_mes) * fator_inf
    
    if usar_solar:
        # EV com solar: custo é parcela do financiamento (enquanto durar) + O&M inflacionado + manutenção + seguro
        parcela = parcela_fin if (m <= n_meses) else 0.0
        oem_mes = oem_base_mensal * fator_inf
        custo_EV = parcela + oem_mes + (manutencao_EV_mes + seguro_EV_mes) * fator_inf
    else:
        # EV sem solar: custo de energia da rede (inflacionado) + manutenção + seguro
        custo_EV = custo_EV_rede

    economia_mensal = custo_ICE - custo_EV
    economia_acumulada += economia_mensal

    if m <= 60:
        economia_acumulada_5anos += economia_mensal

    dados.append([
        m, 
        custo_ICE, 
        custo_EV, 
        economia_mensal, 
        economia_acumulada,
        parcela if usar_solar else 0.0,
        (oem_base_mensal * fator_inf) if usar_solar else 0.0,
        fator_inf
    ])

df = pd.DataFrame(dados, columns=[
    "Mês", "Custo ICE (R$)", "Custo EV (R$)", "Economia Mensal (R$)", 
    "Economia Acumulada (R$)", "Parcela Fin (R$)", "O&M (R$)", "Fator Inflação"
])

# -----------------------------
# Resultados principais (mês atual e indicadores)
# -----------------------------
st.subheader("📊 Resultados — Destaques")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Custo mensal ICE hoje (R$)", f"{total_ICE_RS_base:,.2f}")
if usar_solar:
    # Considera mês 1: parcela + O&M base (sem inflação acumulada)
    col2.metric("Custo mensal EV c/ Solar hoje (R$)", f"{(parcela_fin if n_meses>0 else 0) + oem_base_mensal:,.2f}")
else:
    col2.metric("Custo mensal EV s/ Solar hoje (R$)", f"{total_EV_RS_rede_base:,.2f}")

col3.metric("Consumo EV (kWh/mês)", f"{kWh_mes_EV:,.1f}")
col4.metric("kWp Solar necessário", f"{kWp_solar_necessario:,.2f}")

st.subheader("💡 Indicadores do Sistema Solar")

col5, col6 = st.columns(2)

if usar_solar:
    col5.metric("CAPEX Solar (R$)", f"{CAPEX_solar_EV:,.2f}")
    if n_meses > 0:
        col6.metric(
            "Parcela Financiamento (R$)",
            f"{parcela_fin:,.2f}",
            f"{n_meses} meses | {juros_fin_pct:.1f}% a.a."
        )
    else:
        col6.metric("Financiamento", "Sem financiamento")
else:
    col5.metric("Sistema Solar", "Não utilizado")
    col6.metric("Financiamento", "-")


st.success(f"🏆 Economia acumulada em 5 anos: R$ {economia_acumulada_5anos:,.2f}")


# -----------------------------
# Gráficos
# -----------------------------
st.subheader("📈 Gráficos comparativos")

fig1 = px.line(
    df, x="Mês", y=["Custo ICE (R$)", "Custo EV (R$)"], 
    title="Custo mensal — ICE vs EV (com/sem Solar) ao longo de 25 anos"
)
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.line(df, x="Mês", y="Economia Acumulada (R$)", title="Economia acumulada ao longo do tempo (25 anos)")
# marcador visual nos 5 anos
fig2.add_vline(x=60, line_dash="dash", annotation_text="5 anos", annotation_position="top right")
st.plotly_chart(fig2, use_container_width=True)

# -----------------------------
# Tabela (opcional)
# -----------------------------
with st.expander("🔎 Ver tabela detalhada (mensal)"):
    st.dataframe(df, use_container_width=True)
