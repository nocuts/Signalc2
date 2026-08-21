import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta

# -------------------------------------------------------------
# 1. 페이지 기본 설정
# -------------------------------------------------------------
st.set_page_config(
    page_title="SignalC 법인 포트폴리오",
    page_icon="📈",
    layout="wide"
)

# -------------------------------------------------------------
# 2. 마스터 데이터 정의 (핵심 7대 상품 풀 & 4대 표준 포트폴리오)
# -------------------------------------------------------------
MASTER_ASSETS = {
    "SGOV": {
        "name": "iShares 0-3 Month Treasury Bond ETF",
        "category": "단기채권",
        "payout": "월배당",
        "yield": 5.1,
        "desc": "미국 초단기 국채 투자, 극저변동성 현금성 자산"
    },
    "TLT": {
        "name": "iShares 20+ Year Treasury Bond ETF",
        "category": "장기국채",
        "payout": "월배당",
        "yield": 4.2,
        "desc": "미국 20년 이상 장기국채, 시장 하락 방어용 자산"
    },
    "SCHD": {
        "name": "Schwab U.S. Dividend Equity ETF",
        "category": "배당성장",
        "payout": "분기배당",
        "yield": 3.6,
        "desc": "미국 우량 100개 배당성장 기업 분산투자"
    },
    "O": {
        "name": "Realty Income Corp",
        "category": "부동산(리츠)",
        "payout": "월배당",
        "yield": 5.4,
        "desc": "글로벌 상업용 부동산 월배당 리츠"
    },
    "JEPI": {
        "name": "JPMorgan Equity Premium Income ETF",
        "category": "옵션인컴",
        "payout": "월배당",
        "yield": 7.6,
        "desc": "S&P500 기반 저변동성 + 커버드콜 옵션 프리미엄"
    },
    "JEPQ": {
        "name": "JPMorgan Nasdaq Equity Premium Income ETF",
        "category": "옵션인컴",
        "payout": "월배당",
        "yield": 9.8,
        "desc": "나스닥100 대형 테크주 + 옵션 프리미엄 수취"
    },
    "TLTW": {
        "name": "iShares 20+ Year Treasury Bond BuyWrite ETF",
        "category": "옵션인컴",
        "payout": "월배당",
        "yield": 12.2,
        "desc": "미국 장기국채 기반 커버드콜 고배당 인컴"
    }
}

STANDARD_PORTFOLIOS = {
    "안정형": {
        "target_yield_range": "5.0% ~ 6.0%",
        "weights": {"SGOV": 40, "SCHD": 40, "O": 20},
        "desc": "원금 변동성 최소화, 안전 이자 및 기본 배당 확보"
    },
    "중립형": {
        "target_yield_range": "7.0% ~ 8.0%",
        "weights": {"SCHD": 35, "JEPI": 45, "TLT": 20},
        "desc": "주가 방어력과 월배당 현금흐름 밸런스 유지"
    },
    "투자형": {
        "target_yield_range": "9.0% ~ 10.0%",
        "weights": {"JEPI": 40, "JEPQ": 40, "SCHD": 20},
        "desc": "대표 지수(S&P500/나스닥) 기반 안정적 월 고인컴 창출"
    },
    "공격형": {
        "target_yield_range": "11.0% ~ 12.5%",
        "weights": {"JEPQ": 50, "TLTW": 30, "JEPI": 20},
        "desc": "지수 및 미국채 커버드콜을 활용한 법인 현금흐름 극대화"
    }
}

# -------------------------------------------------------------
# 3. 세션 상태(Session State) 초기화
# -------------------------------------------------------------
if "custom_portfolios" not in st.session_state:
    st.session_state.custom_portfolios = {
        "내 커스텀 1호": {"JEPI": 40, "JEPQ": 30, "SCHD": 20, "SGOV": 10}
    }

# -------------------------------------------------------------
# 4. 데이터 로드 함수 (캐싱 & 타임존 정제)
# -------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_historical_data(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return None
        df = df.reset_index()
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        return df[['Date', 'Close']]
    except Exception:
        return None

# -------------------------------------------------------------
# 5. 사이드바 - 투자금 및 법인 지출 설정
# -------------------------------------------------------------
st.sidebar.title("🏢 법인 자금 및 지출 설정")

# 투자 원금 설정
inv_capital_man = st.sidebar.number_input("총 투자 자본금 (만원 단위)", min_value=1000, value=50000, step=5000)
total_capital = inv_capital_man * 10000

st.sidebar.markdown("---")
st.sidebar.subheader("📌 법인 월 고정비")
exp_salary = st.sidebar.number_input("인건비/급여 (원)", min_value=0, value=3000000, step=100000)
exp_rent = st.sidebar.number_input("임대료 / 관리비 (원)", min_value=0, value=1000000, step=100000)
exp_car = st.sidebar.number_input("차량비 (리스/렌트/유류) (원)", min_value=0, value=800000, step=50000)
exp_sub = st.sidebar.number_input("가전 / 가구 구독료 (원)", min_value=0, value=200000, step=10000)

st.sidebar.subheader("📌 법인 월 운영비 및 배당")
exp_op = st.sidebar.number_input("기타 운영비 (세무/SW 등) (원)", min_value=0, value=500000, step=50000)
exp_div = st.sidebar.number_input("목표 법인 배당금 (원)", min_value=0, value=0, step=100000)

monthly_fixed_cost = exp_salary + exp_rent + exp_car + exp_sub
total_monthly_expense = monthly_fixed_cost + exp_op + exp_div
annual_expense = total_monthly_expense * 12

# -------------------------------------------------------------
# 6. 메인 헤더
# -------------------------------------------------------------
st.title("SignalC 법인 포트폴리오")
st.caption("실제 상장 ETF 기반 법인 배당 매출 시뮬레이터 및 투자 성향 진단 시스템")

# 상단 탭 구성
main_tab1, main_tab2 = st.tabs(["🏛️ 기본 포트폴리오 (4개 표준 모델)", "⚙️ 커스텀 포트폴리오 (맞춤 진단)"])

# -------------------------------------------------------------
# TAB 1: 기본 포트폴리오
# -------------------------------------------------------------
with main_tab1:
    st.subheader("1. 4개 표준 모델 통합 비교")
    
    # 4개 모델 비교 카드 (카드형 UI 개선 적용)
    summary_cols = st.columns(4)
    for idx, (p_name, p_info) in enumerate(STANDARD_PORTFOLIOS.items()):
        avg_yield = sum(MASTER_ASSETS[t]["yield"] * (w / 100) for t, w in p_info["weights"].items())
        annual_rev = total_capital * (avg_yield / 100)
        monthly_rev = annual_rev / 12
        net_monthly = monthly_rev - total_monthly_expense
        coverage = (monthly_rev / total_monthly_expense * 100) if total_monthly_expense > 0 else 100

        with summary_cols[idx]:
            with st.container(border=True):
                # 헤더
                st.markdown(f"<h4 style='margin:0; padding:0; text-align:center;'>{p_name}</h4>", unsafe_allow_html=True)
                st.markdown(f"<p style='color:gray; font-size:12px; text-align:center; margin-bottom:12px;'>목표: {p_info['target_yield_range']}</p>", unsafe_allow_html=True)
                
                # 예상 연 배당수익률
                st.markdown(f"""
                <div style='background-color:#F8F9FA; border-radius:8px; padding:10px; text-align:center; margin-bottom:10px;'>
                    <span style='font-size:12px; color:#555;'>예상 연 배당수익률</span><br>
                    <span style='font-size:22px; font-weight:bold; color:#1E3A8A;'>{avg_yield:.2f}%</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 월 예상 배당 매출
                st.markdown(f"""
                <div style='text-align:center; margin-bottom:12px;'>
                    <span style='font-size:12px; color:#666;'>월 예상 배당매출</span><br>
                    <span style='font-size:24px; font-weight:800; color:#0F172A;'>{monthly_rev / 10000:,.0f} <span style='font-size:15px; font-weight:normal;'>만원</span></span>
                </div>
                """, unsafe_allow_html=True)
                
                # 월 순이익 & 커버리지 상태
                net_color = "#16A34A" if net_monthly >= 0 else "#DC2626"
                badge_bg = "#DCFCE7" if net_monthly >= 0 else "#FEE2E2"
                badge_text_color = "#15803D" if net_monthly >= 0 else "#B91C1C"
                prefix = "+" if net_monthly > 0 else ""

                st.markdown(f"""
                <div style='border-top:1px solid #E2E8F0; padding-top:10px; margin-bottom:12px; text-align:center;'>
                    <span style='font-size:12px; color:#666;'>월 잉여금 (손익)</span><br>
                    <span style='font-size:18px; font-weight:bold; color:{net_color};'>{prefix}{net_monthly / 10000:,.0f} 만원</span>
                    <div style='margin-top:4px;'>
                        <span style='background-color:{badge_bg}; color:{badge_text_color}; font-size:11px; font-weight:600; padding:2px 8px; border-radius:12px;'>
                            지출 커버 {coverage:.1f}%
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 종목 구성 비중
                weight_badges = " ".join([
                    f"<span style='background-color:#EDE9FE; color:#5B21B6; font-size:10px; padding:2px 6px; border-radius:4px; margin:2px;'>{t} {w}%</span>" 
                    for t, w in p_info["weights"].items()
                ])
                st.markdown(f"<div style='line-height:1.8; text-align:center;'>{weight_badges}</div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # 세부 분석
    st.subheader("2. 표준 모델 상세 분석")
    selected_std = st.selectbox("상세 조회할 포트폴리오 선택", list(STANDARD_PORTFOLIOS.keys()))
    std_info = STANDARD_PORTFOLIOS[selected_std]
    
    col_pie, col_breakdown = st.columns([1, 1])
    with col_pie:
        pie_df = pd.DataFrame([
            {"Ticker": t, "Weight": w, "Name": MASTER_ASSETS[t]["name"]}
            for t, w in std_info["weights"].items()
        ])
        fig_pie = px.pie(pie_df, values="Weight", names="Ticker", title=f"[{selected_std}] 자산 배분 비중", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_breakdown:
        st.markdown(f"**전략 설명**: {std_info['desc']}")
        calc_rows = []
        for t, w in std_info["weights"].items():
            alloc_cap = total_capital * (w / 100)
            item_yield = MASTER_ASSETS[t]["yield"]
            ann_div = alloc_cap * (item_yield / 100)
            calc_rows.append({
                "티커": t,
                "종목명": MASTER_ASSETS[t]["name"],
                "비중": f"{w}%",
                "투자금액": f"{alloc_cap/10000:,.0f} 만원",
                "연 배당률": f"{item_yield}%",
                "월 예상 배당": f"{ann_div/12/10000:,.0f} 만원"
            })
        st.dataframe(pd.DataFrame(calc_rows), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("3. 투자 상품 탐색 및 개별 추이")
    
    # 사용된 포트폴리오 플래그 매핑
    asset_table_rows = []
    for ticker, info in MASTER_ASSETS.items():
        used_types = []
        for p_name, p_data in STANDARD_PORTFOLIOS.items():
            if ticker in p_data["weights"]:
                used_types.append(f"{p_name}({p_data['weights'][ticker]}%)")
        
        asset_table_rows.append({
            "티커": ticker,
            "종목명": info["name"],
            "카테고리": info["category"],
            "배당주기": info["payout"],
            "연 배당수익률": f"{info['yield']}%",
            "적용 포트폴리오 플래그": ", ".join(used_types)
        })
    st.dataframe(pd.DataFrame(asset_table_rows), hide_index=True, use_container_width=True)

    # 개별 종목 차트 조회
    chart_col1, chart_col2 = st.columns([1, 3])
    with chart_col1:
        selected_ticker = st.selectbox("과거 추이 조회 종목", list(MASTER_ASSETS.keys()))
        selected_period = st.radio("조회 기간", ["3mo", "6mo", "1y", "3y"], index=2)
    
    with chart_col2:
        hist_data = load_historical_data(selected_ticker, period=selected_period)
        if hist_data is not None and not hist_data.empty:
            fig_hist = px.line(
                hist_data,
                x='Date',
                y='Close',
                title=f"{selected_ticker} 주가 추이 ({selected_period})",
                labels={'Close': '주가 ($)', 'Date': '날짜'}
            )
            fig_hist.update_traces(hovertemplate='%{x|%Y-%m-%d}<br>종가: $%{y:.2f}')
            fig_hist.update_layout(xaxis_title="", yaxis_title="주가 (USD)")
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.warning("데이터를 불러오는 중이거나 종목 시세를 가져올 수 없습니다.")

# -------------------------------------------------------------
# TAB 2: 커스텀 포트폴리오 (진단 & 시뮬레이션)
# -------------------------------------------------------------
@st.dialog("🛠️ 커스텀 포트폴리오 생성/수정")
def custom_portfolio_dialog():
    p_name_input = st.text_input("포트폴리오 명칭", value="내 맞춤 포트폴리오")
    st.write("각 상품의 투자 비중(%)을 설정해 주세요 (합계: 100% 필수)")
    
    weights_input = {}
    cols = st.columns(2)
    for idx, ticker in enumerate(MASTER_ASSETS.keys()):
        col = cols[idx % 2]
        weights_input[ticker] = col.slider(
            f"{ticker} ({MASTER_ASSETS[ticker]['category']})",
            min_value=0, max_value=100, value=0, step=5
        )
    
    total_w = sum(weights_input.values())
    if total_w == 100:
        st.success(f"비중 합계: {total_w}% (정상)")
        if st.button("저장하기", type="primary"):
            filtered_weights = {k: v for k, v in weights_input.items() if v > 0}
            st.session_state.custom_portfolios[p_name_input] = filtered_weights
            st.rerun()
    else:
        st.error(f"현재 비중 합계: {total_w}% (반드시 100%로 맞춰주세요)")

with main_tab2:
    col_custom_head, col_custom_btn = st.columns([3, 1])
    with col_custom_head:
        st.subheader("내가 조합하는 커스텀 포트폴리오 & 성향 진단")
    with col_custom_btn:
        if st.button("➕ 새 커스텀 포트폴리오 구성"):
            custom_portfolio_dialog()

    if not st.session_state.custom_portfolios:
        st.info("우측 상단의 버튼을 눌러 나만의 커스텀 포트폴리오를 만들어보세요.")
    else:
        active_custom_name = st.selectbox("분석할 커스텀 포트폴리오 선택", list(st.session_state.custom_portfolios.keys()))
        custom_weights = st.session_state.custom_portfolios[active_custom_name]
        
        c_avg_yield = sum(MASTER_ASSETS[t]["yield"] * (w / 100) for t, w in custom_weights.items())
        c_ann_rev = total_capital * (c_avg_yield / 100)
        c_month_rev = c_ann_rev / 12
        c_net_month = c_month_rev - total_monthly_expense
        c_coverage = (c_month_rev / total_monthly_expense * 100) if total_monthly_expense > 0 else 100

        if c_avg_yield < 6.5:
            type_badge = "🛡️ 안정형 성향"
        elif c_avg_yield < 8.5:
            type_badge = "⚖️ 중립형 성향"
        elif c_avg_yield < 10.5:
            type_badge = "🚀 투자형 성향"
        else:
            type_badge = "🔥 공격형 성향"

        st.markdown("---")
        st.success(f"🎯 **투자 성향 진단 결과**: 기획자님이 구성하신 포트폴리오는 **[{type_badge}]**에 해당합니다. (연 예상 배당률: **{c_avg_yield:.2f}%**)")

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("연간 예상 배당 매출", f"{c_ann_rev/10000:,.0f} 만원")
        m_col2.metric("월 환산 배당 매출", f"{c_month_rev/10000:,.0f} 만원")
        m_col3.metric("법인 월 총 지출", f"{total_monthly_expense/10000:,.0f} 만원")
        m_col4.metric("월 잉여 현금흐름", f"{c_net_month/10000:,.0f} 만원", delta=f"커버리지 {c_coverage:.1f}%")

        c_col_chart, c_col_table = st.columns([1, 1])
        with c_col_chart:
            c_pie_df = pd.DataFrame([
                {"Ticker": t, "Weight": w, "Name": MASTER_ASSETS[t]["name"]}
                for t, w in custom_weights.items()
            ])
            fig_custom_pie = px.pie(c_pie_df, values="Weight", names="Ticker", title=f"[{active_custom_name}] 비중 구조", hole=0.4)
            st.plotly_chart(fig_custom_pie, use_container_width=True)

        with c_col_table:
            st.write("**편입 상품별 매출 기여도**")
            c_calc_rows = []
            for t, w in custom_weights.items():
                alloc_cap = total_capital * (w / 100)
                item_yield = MASTER_ASSETS[t]["yield"]
                ann_div = alloc_cap * (item_yield / 100)
                c_calc_rows.append({
                    "티커": t,
                    "종목명": MASTER_ASSETS[t]["name"],
                    "비중": f"{w}%",
                    "연 배당률": f"{item_yield}%",
                    "월 예상 배당": f"{ann_div/12/10000:,.0f} 만원"
                })
            st.dataframe(pd.DataFrame(c_calc_rows), hide_index=True, use_container_width=True)
            
            if st.button("🗑️ 이 커스텀 포트폴리오 삭제"):
                del st.session_state.custom_portfolios[active_custom_name]
                st.rerun()