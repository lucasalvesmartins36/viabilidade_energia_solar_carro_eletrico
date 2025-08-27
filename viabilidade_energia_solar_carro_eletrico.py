import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------
# Configuração inicial
# -----------------------------
st.set_page_config(page_title="Simulador EV + Solar", layout="wide")

st.title("🚗⚡ Simulador EV + Solar")
st.write("Compare custos de um veículo a combustão (ICE) com veículo elétrico (EV) com ou sem energia solar.")

# -----------------------------
# Entradas do usuário
# -----------------------------
st.sidebar.header("Parâmetros de Entrada")

km_mes = st.sidebar.slider("Km rodados por mês", 500, 5000, 1300, 100)
preco_gasolina = st.sidebar.slider("Preço da gasolina (R$/L)", 4.0, 10.0, 6.4, 0.1)
consumo_ICE = st.sidebar.slider("Consumo ICE (km/L)", 5.0, 20.0, 12.0, 0.5)
eficiencia_EV = st.sidebar.slider("Eficiência EV (km/kWh)", 3.0, 10.0, 6.0, 0.1)
perdas_pct = st.sidebar.slider("Perdas de carga (%)", 0, 30, 10, 1)
tarifa_kWh = st.sidebar.slider("Tarifa energia (R$/kWh)", 0.5, 2.0, 1.0, 0.05)
producao_kWh_kWp_ano = st.sidebar.slider("Produção anual (kWh/kWp)", 1000, 2000, 1379, 10)

usar_solar = st.sidebar.checkbox("Usar energia solar para EV", True)

# -----------------------------
# Cálculos
# -----------------------------
# ICE
combustivel_ICE_RS = (km_mes / consumo_ICE) * preco_gasolina
total_ICE_RS = combustivel_ICE_RS

# EV
kWh_mes_EV = (km_mes / eficiencia_EV) * (1 + perdas_pct/100)
energia_EV_rede_RS = kWh_mes_EV * tarifa_kWh
total_EV_RS = energia_EV_rede_RS

# Solar dimensionado
if usar_solar:
    kWp_solar = (kWh_mes_EV * 12) / producao_kWh_kWp_ano
else:
    kWp_solar = 0

# -----------------------------
# Resultados principais
# -----------------------------
st.subheader("📊 Resultados")

col1, col2, col3 = st.columns(3)
col1.metric("Custo mensal ICE (R$)", f"{total_ICE_RS:,.2f}")
col2.metric("Custo mensal EV (R$)", f"{total_EV_RS:,.2f}")
col3.metric("Consumo EV (kWh/mês)", f"{kWh_mes_EV:,.1f}")

st.write(f"**kWp Solar necessário:** {kWp_solar:,.2f} kWp")

# -----------------------------
# Simulação de 5 anos
# -----------------------------
meses = 60
dados = []
economia_acumulada = 0

for m in range(1, meses+1):
    custo_ICE = total_ICE_RS
    custo_EV = total_EV_RS
    economia_mensal = custo_ICE - custo_EV
    economia_acumulada += economia_mensal

    dados.append([m, custo_ICE, custo_EV, economia_mensal, economia_acumulada])

df = pd.DataFrame(dados, columns=["Mês", "Custo ICE", "Custo EV", "Economia Mensal", "Economia Acumulada"])

# -----------------------------
# Gráficos
# -----------------------------
st.subheader("📈 Gráficos comparativos")

fig1 = px.line(df, x="Mês", y=["Custo ICE", "Custo EV"], title="Custo mensal ICE vs EV")
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.line(df, x="Mês", y="Economia Acumulada", title="Economia acumulada ao longo do tempo")
st.plotly_chart(fig2, use_container_width=True)
