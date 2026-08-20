from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="50억 법인 포트폴리오 시뮬레이터", layout="wide"
)

st.title("🏢 50억 법인 자산 운용 및 시뮬레이터")
st.markdown(
    "감리·컨설팅 법인 고정비 방어 및 투자 법인 인컴 수익 최적화 대시보드"
)
st.markdown("---")

# 1. 사이드바: 기본 설정값 입력
st.sidebar.header("⚙️ 시뮬레이터 파라미터 설정")
total_capital = (
    st.sidebar.number_input(
        "총 투자 자금 (원)", value=5000000000, step=100_000_000, format="%d"
    )
    / 100000000
)  # 억 단위

st.sidebar.markdown("### 💸 법인 월 고정 지출 설정")
director_salary = (
    st.sidebar.number_input("사내이사 월 급여 (원)", value=6666666, step=500_000)
    / 10000
)  # 만원
car_expense = (
    st.sidebar.number_input(
        "폴스타 3 리스 및 유지비 (월)", value=2500000, step=200_000
    )
    / 10000
)  # 만원
office_expense = (
    st.sidebar.number_input(
        "사무실 렌탈 및 일반 경비 (월)", value=3000000, step=200_000
    )
    / 10000
)  # 만원

total_monthly_expense_man = director_salary + car_expense + office_expense

# 2. 포트폴리오 구성 데이터 정의
portfolio_data = {
    "Asset_Class": [
        "CD/KOFR 파킹 (안정)",
        "우량 만기채권 (인컴)",
        "국내 고배당 ETF (인컴)",
        "미국 배당/커버드콜 (인컴)",
        "미국 빅테크/AI (성장)",
    ],
    "Ticker": ["357870/423160", "ACE 회사채", "466920", "JEPI / SCHD", "QQQ / SOXX"],
    "Weight": [0.20, 0.20, 0.20, 0.20, 0.20],
    "Target_Yield": [0.036, 0.040, 0.072, 0.075, 0.060],  # 연 수익률
}

actual_capital = total_capital * 100000000  # 원 단위
df_portfolio = pd.DataFrame(portfolio_data)
df_portfolio["Allocated_Capital"] = actual_capital * df_portfolio["Weight"]
df_portfolio["Annual_Income"] = (
    df_portfolio["Allocated_Capital"] * df_portfolio["Target_Yield"]
)
df_portfolio["Monthly_Income"] = df_portfolio["Annual_Income"] / 12

total_annual_income = df_portfolio["Annual_Income"].sum()
weighted_avg_yield = (total_annual_income / actual_capital) * 100
total_annual_expense = (total_monthly_expense_man * 10000) * 12
net_annual_cashflow = total_annual_income - total_annual_expense

# 3. 메인 KPI 지표 카드
col1, col2, col3, col4 = st.columns(4)
col1.metric("총 운용 자금", f"{total_capital:,.1f} 억원")
col2.metric(
    "연간 예상 인컴 수익",
    f"{total_annual_income/100000000:,.2f} 억원",
    f"가중수익률 {weighted_avg_yield:.2f}%",
)
col3.metric(
    "연간 법인 고정비 지출", f"{total_annual_expense/100000000:,.2f} 억원"
)
col4.metric(
    "연간 잉여 현금흐름 (Net)",
    f"{net_annual_cashflow/100000000:,.2f} 억원",
    delta="흑자 구조" if net_annual_cashflow > 0 else "적자 구조",
)

st.markdown("---")

# 4. [복구 완료] 포트폴리오 누적 자산 성장 추이 시뮬레이션 차트
st.subheader("📈 포트폴리오 누적 자산 성장 추이")

# 6개월 기간의 시계열 시뮬레이션 데이터 생성
np.random.seed(42)
dates = pd.date_range(end=datetime.today(), periods=130, freq="B")

# 포트폴리오 일일 변동성 및 추세 생성 (가중평균 수익률 반영)
daily_mean = weighted_avg_yield / 100 / 252
daily_vol = 0.0045
random_returns = np.random.normal(daily_mean, daily_vol, len(dates))

# 자산 가치 시계열 산출
asset_values = actual_capital * np.cumprod(1 + random_returns)
df_trend = pd.DataFrame({"Date": dates, "Portfolio_Value": asset_values})

# Plotly 차트 생성 (원금 기준선 포함)
fig = go.Figure()

# 자산 가치 라인 (파란색 실선)
fig.add_trace(
    go.Scatter(
        x=df_trend["Date"],
        y=df_trend["Portfolio_Value"],
        mode="lines",
        name="포트폴리오 평가액",
        line=dict(color="#0066cc", width=2.5),
    )
)

# 원금 기준선 (빨간색 점선)
fig.add_shape(
    type="line",
    x0=df_trend["Date"].iloc[0],
    y0=actual_capital,
    x1=df_trend["Date"].iloc[-1],
    y1=actual_capital,
    line=dict(color="red", width=2, dash="dash"),
)

# 원금 텍스트 레이블
fig.add_annotation(
    x=df_trend["Date"].iloc[-5],
    y=actual_capital,
    text=f"원금 ({total_capital:,.0f}억)",
    showarrow=False,
    yshift=12,
    font=dict(color="red", size=12),
)

fig.update_layout(
    yaxis=dict(
        title="평가액 (원)",
        tickformat=".2s",  # 4.8B, 5.0B, 5.2B 포맷
        gridcolor="#f0f0f0",
    ),
    xaxis=dict(gridcolor="#f0f0f0"),
    plot_bgcolor="white",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=20, b=20),
    height=450,
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 5. 상세 포트폴리오 테이블
st.subheader("📊 50억 자산 배분 및 종목별 인컴 구조")
display_df = df_portfolio[
    ["Asset_Class", "Ticker", "Weight", "Target_Yield", "Annual_Income"]
].copy()
display_df["Weight"] = display_df["Weight"] * 100
display_df["Target_Yield"] = display_df["Target_Yield"] * 100
display_df.columns = [
    "자산군",
    "대표 티커",
    "비중 (%)",
    "목표 수익률 (%)",
    "연간 예상 수익 (원)",
]
display_df["연간 예상 수익 (원)"] = display_df["연간 예상 수익 (원)"].apply(
    lambda x: f"{x:,.0f} 원"
)

st.dataframe(display_df, use_container_width=True)

st.markdown("---")

# 6. 월별 현금흐름 시뮬레이션
st.subheader("📅 월별 인컴 유입 vs 고정비 지출 시뮬레이션")
div_sim_results = []
for i in range(1, 13):
  div_sim_results.append({
      "Month": f"{i}월",
      "월별 배당/이자 유입": total_annual_income / 12,
      "월별 고정비 지출": total_annual_expense / 12,
  })

df_sim = pd.DataFrame(div_sim_results)
df_sim.set_index("Month", inplace=True)
st.bar_chart(df_sim)