import streamlit as st  
import pandas as pd
import plotly.express as px
import numpy as np
from urllib.parse import quote_plus  # montar o link do WhatsApp

# -----------------------------
# Configuração inicial
# -----------------------------
st.set_page_config(page_title="Simulador veículo elétrico + Energia Solar", layout="wide")

st.title("🚗⚡ Simulador Veículo Elétrico + Energia Solar")
st.write("Compare custos de um veículo a gasolina (VG) com veículo elétrico (VE) com ou sem energia solar, considerando financiamento, manutenção e inflação. Clique em >> no canto superior esquerdo para preencher seus dados")

# -----------------------------
# Entradas do usuário
# -----------------------------
st.sidebar.header("Comece por aqui - Seus dados")

km_mes = st.sidebar.slider("Km rodados por mês", 500, 6000, 1300, 100)
preco_gasolina = st.sidebar.slider("Preço da gasolina hoje (R$/L)", 4.0, 10.0, 6.4, 0.1)
consumo_ICE = st.sidebar.slider("Consumo veículo a gasolina (km/L)", 5.0, 20.0, 12.0, 0.5)

eficiencia_EV = st.sidebar.slider("Eficiência veículo elétrico (km/kWh)", 3.0, 10.0, 6.0, 0.1)
perdas_pct = st.sidebar.slider("Perdas de carga (%)", 0, 30, 10, 1)
tarifa_kWh = st.sidebar.slider("Tarifa de energia hoje (R$/kWh)", 0.5, 2.0, 1.0, 0.05)
producao_kWh_kWp_ano = st.sidebar.slider("Produção anual (kWh/kWp)", 1000, 2000, 1379, 10)

usar_solar = st.sidebar.checkbox("Usar energia solar para o VE", True)

st.sidebar.header("Parâmetros Econômicos")

st.sidebar.header("Financiamento do veículo elétrico")
CAPEX_EV = st.sidebar.number_input("Preço do veículo elétrico (R$)", min_value=0.0, value=120000.0, step=1000.0)
entrada_EV = st.sidebar.number_input("Entrada (R$)", min_value=0.0, value=20000.0, step=1000.0)
juros_fin_EV_pct = st.sidebar.slider("Juros financiamento EV (a.a.) [%]", 0.0, 30.0, 15.0, 0.1)
prazo_fin_EV_anos = st.sidebar.slider("Prazo financiamento EV (anos)", 0, 15, 5, 1)

inflacao_pct = st.sidebar.slider("Inflação (a.a.) [%]", 0.0, 20.0, 4.0, 0.1)
juros_fin_pct = st.sidebar.slider("Juros financiamento solar (a.a.) [%]", 0.0, 30.0, 25.0, 0.1)
prazo_fin_anos = st.sidebar.slider("Prazo do financiamento (anos)", 0, 15, 5, 1)

# converter percentuais para decimais
inflacao_aa = inflacao_pct / 100
juros_fin_aa = juros_fin_pct / 100

st.sidebar.header("Custos Fixos Mensais dos Veículos (R$)")
manutencao_ICE_mes = st.sidebar.number_input("Manutenção veículo a gasolina (R$/mês)", min_value=0.0, value=300.0, step=50.0)
seguro_ICE_mes = st.sidebar.number_input("Seguro veículo a gasolina (R$/mês)", min_value=0.0, value=250.0, step=50.0)

manutencao_EV_mes = st.sidebar.number_input("Manutenção veículo elétrico (R$/mês)", min_value=0.0, value=150.0, step=50.0)
seguro_EV_mes = st.sidebar.number_input("Seguro veículo elétrico (R$/mês)", min_value=0.0, value=200.0, step=50.0)

st.sidebar.header("CAPEX do Sistema Solar para o veículo elétrico")
# Primeiro calculamos o kWp necessário
kWh_mes_EV_base = (km_mes / eficiencia_EV) * (1 + perdas_pct/100)
kWp_solar_necessario = (kWh_mes_EV_base * 12) / producao_kWh_kWp_ano if usar_solar else 0.0

# Opção de informar CAPEX diretamente ou por custo/kWp
modo_capex = st.sidebar.radio("Como informar o CAPEX?", ["Direto (R$)", "Custo por kWp"], index=1)
if modo_capex == "Direto (R$)":
    CAPEX_solar_EV = st.sidebar.number_input(
        "CAPEX_solar_EV (R$)", min_value=0.0,
        value=float(round(kWp_solar_necessario*4500, -2)),
        step=100.0, help="Se usar solar, valor total do sistema dedicado ao EV."
    )
else:
    custo_kWp = st.sidebar.number_input("Custo por kWp (R$/kWp)", min_value=0.0, value=3032.0, step=100.0)
    CAPEX_solar_EV = custo_kWp * kWp_solar_necessario if usar_solar else 0.0
    st.sidebar.caption(f"CAPEX estimado: R$ {CAPEX_solar_EV:,.2f}")

# -----------------------------
# Cálculos — mês 0 (base) e parâmetros
# -----------------------------
# VG base (mês 1 sem inflação aplicada ainda)
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

juros_fin_EV_aa = juros_fin_EV_pct / 100
juros_fin_EV_am = taxa_mensal_da_anual(juros_fin_EV_aa)
n_meses_EV = prazo_fin_EV_anos * 12
valor_financiado_EV = CAPEX_EV - entrada_EV

# Financiamento Price da energia solar (se houver)
n_meses = prazo_fin_anos * 12
if usar_solar and CAPEX_solar_EV > 0 and n_meses > 0 and juros_fin_am > -1:
    if juros_fin_am == 0:
        parcela_fin = CAPEX_solar_EV / n_meses
    else:
        parcela_fin = CAPEX_solar_EV * (juros_fin_am) / (1 - (1 + juros_fin_am) ** (-n_meses))
else:
    parcela_fin = 0.0
    
if valor_financiado_EV > 0 and n_meses_EV > 0 and juros_fin_EV_am > -1:
    if juros_fin_EV_am == 0:
        parcela_fin_EV = valor_financiado_EV / n_meses_EV
    else:
        parcela_fin_EV = valor_financiado_EV * (juros_fin_EV_am) / (1 - (1 + juros_fin_EV_am) ** (-n_meses_EV))
else:
    parcela_fin_EV = 0.0
    
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
    fator_inf = (1 + inflacao_am) ** (m - 1)

    # Custo ICE
    custo_ICE = (total_ICE_RS_base * fator_inf) + (manutencao_ICE_mes + seguro_ICE_mes) * fator_inf

    # Custo EV rede (sem solar)
    custo_EV_rede = (total_EV_RS_rede_base * fator_inf) + (manutencao_EV_mes + seguro_EV_mes) * fator_inf
    parcela_EV = parcela_fin_EV if (m <= n_meses_EV) else 0.0

    if usar_solar:
        parcela = parcela_fin if (m <= n_meses) else 0.0
        oem_mes = oem_base_mensal * fator_inf
        custo_EV = parcela_EV + parcela + oem_mes + (manutencao_EV_mes + seguro_EV_mes) * fator_inf
    else:
        custo_EV = parcela_EV + custo_EV_rede

    # Economia
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
        fator_inf,
        parcela_EV
    ])

df = pd.DataFrame(dados, columns=[
    "Mês", "Custo VG (R$)", "Custo VE (R$)", "Economia Mensal (R$)", 
    "Economia Acumulada (R$)", "Parcela Solar (R$)", "O&M (R$)", 
    "Fator Inflação", "Parcela EV (R$)"
])

# -----------------------------
# Resultados principais
# -----------------------------
st.subheader("📊 Resultados")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Custo mensal VG hoje (R$)", f"{total_ICE_RS_base:,.2f}")
if usar_solar:
    col2.metric("Custo mensal VE c/ Solar hoje (R$)", f"{(parcela_fin if n_meses>0 else 0) + oem_base_mensal:,.2f}")
else:
    col2.metric("Custo mensal VE s/ Solar hoje (R$)", f"{total_EV_RS_rede_base:,.2f}")

col3.metric("Consumo VE (kWh/mês)", f"{kWh_mes_EV:,.1f}")
col4.metric("kWp Solar necessário", f"{kWp_solar_necessario:,.2f}")

st.subheader("☀️ Indicadores do Sistema Solar ")

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

st.subheader("🔋 Financiamento do veículo elétrico")

col7, col8 = st.columns(2)
col7.metric("Valor financiado EV (R$)", f"{valor_financiado_EV:,.2f}")
if n_meses_EV > 0:
    col8.metric(
        "Parcela financiamento EV (R$)",
        f"{parcela_fin_EV:,.2f}",
        f"{n_meses_EV} meses | {juros_fin_EV_pct:.1f}% a.a."
    )
else:
    col8.metric("Financiamento EV", "Sem financiamento")

st.markdown(
    f"""
    <div style="background-color:#d4edda; padding:15px; border-radius:8px">
        <h2 style="color:#155724; font-size:32px;">🏆 Economia acumulada em 5 anos: R$ {economia_acumulada_5anos:,.2f}</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Gráficos
# -----------------------------
st.subheader("📈 Gráficos comparativos")

fig1 = px.line(
    df, x="Mês", y=["Custo VG (R$)", "Custo VE (R$)"], 
    title="Custo mensal — VG vs VE (com/sem Solar) ao longo de 25 anos"
)
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.line(df, x="Mês", y="Economia Acumulada (R$)", title="Economia acumulada ao longo do tempo (25 anos)")
fig2.add_vline(x=60, line_dash="dash", annotation_text="5 anos", annotation_position="top right")
st.plotly_chart(fig2, use_container_width=True)

# -----------------------------
# Tabela (opcional)
# -----------------------------
with st.expander("🔎 Ver tabela detalhada (mensal)"):
    st.dataframe(df, use_container_width=True)

# -----------------------------
# CTA — Sticky Footer (R$ 49,00)
# -----------------------------
# Mensagem com números atuais
msg = (
    "Olá! Quero uma simulação personalizada do veículo elétrico + energia solar (R$ 49,00). "
    f"Parâmetros atuais: kWp estimado ≈ {kWp_solar_necessario:.2f} kWp; "
    f"CAPEX solar ≈ R$ {CAPEX_solar_EV:,.2f}; "
    f"Economia acumulada em 5 anos ≈ R$ {economia_acumulada_5anos:,.2f}. "
    "Meu nome é ______ e posso enviar minha conta de energia/uso do veículo."
)
wa_link = f"https://wa.me/5527996939054?text={quote_plus(msg)}"

# CSS do footer (ajuste os hex para a paleta Vinci)
footer_css = """
<style>
.vinci-cta {
  position: fixed;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  width: min(780px, 94vw);
  z-index: 9999;
  color: #ffffff;
  background: linear-gradient(135deg, #0E9F6E 0%, #16A34A 45%, #22C55E 100%);
  border-radius: 16px;
  box-shadow: 0 10px 28px rgba(0,0,0,0.28);
  padding: 16px 18px;
  border: 0px solid rgba(255,255,255,0.15);
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Arial, 'Apple Color Emoji', 'Segoe UI Emoji';
}
.vinci-cta h3 { margin: 0 0 6px 0; font-size: 1.05rem; }
.vinci-cta .vinci-grid {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: center;
}
.vinci-cta .vinci-points {
  margin: 0; padding-left: 18px; line-height: 1.4; font-size: 0.95rem;
}
.vinci-cta a.vinci-btn {
  display: inline-block;
  text-decoration: none;
  padding: 12px 16px;
  border-radius: 10px;
  background: #ffffff;
  color: #0B3B2E;
  font-weight: 800;
  border: 2px solid rgba(255,255,255,0.25);
  text-align: center;
  min-width: 260px;
}
.vinci-cta .vinci-note {
  margin: 8px 0 0 0; font-size: 12px; opacity: 0.93;
}
@media (max-width: 640px) {
  .vinci-cta .vinci-grid { grid-template-columns: 1fr; }
  .vinci-cta a.vinci-btn { width: 100%; }
}
</style>
"""
st.markdown(footer_css, unsafe_allow_html=True)

footer_html = f"""
<div class="vinci-cta">
  <div class="vinci-grid">
    <div>
      <h3>📣 Simulação personalizada por <b>R$ 49,00</b></h3>
      <ul class="vinci-points">
        <li>Dimensionamento específico (kWp) para seu uso</li>
        <li>Cenários de financiamento e payback</li>
        <li>Economia projetada com seus dados reais</li>
      </ul>
      <div class="vinci-note">Envie sua conta de luz (PDF/foto) e dados do veículo. Atendimento prioritário.</div>
    </div>
    <div style="display:flex; align-items:center; justify-content:center;">
      <a class="vinci-btn" href="{wa_link}" target="_blank">💬 WhatsApp (27 99693-9054)</a>
    </div>
  </div>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)

# Spacer para o footer não cobrir conteúdo ao final da página
st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True)
