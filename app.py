import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from datetime import datetime
import calendar

# -------------------------------------------------------------
# 1. 페이지 기본 설정
# -------------------------------------------------------------
st.set_page_config(
    page_title="SignalC 법인 포트폴리오",
    page_icon="📈",
    layout="wide"
)

# -------------------------------------------------------------
# 2. 마스터 데이터 정의
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

TICKER_COLORS = {
    "SGOV": "#10B981",
    "TLT": "#6366F1",
    "SCHD": "#F59E0B",
    "O": "#EC4899",
    "JEPI": "#3B82F6",
    "JEPQ": "#8B5CF6",
    "TLTW": "#14B8A6"
}

# -------------------------------------------------------------
# 3. 세션 상태 초기화
# -------------------------------------------------------------
if "custom_portfolios" not in st.session_state:
    st.session_state.custom_portfolios = {
        "내 커스텀 1호": {"JEPI": 40, "JEPQ": 30, "SCHD": 20, "SGOV": 10}
    }

# -------------------------------------------------------------
# 4. 주가 데이터 로드 함수 (최근 1년치 로드)
# -------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_all_prices():
    price_dict = {}
    for t in MASTER_ASSETS.keys():
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="1y")
            if not df.empty and 'Close' in df.columns:
                df = df.reset_index()
                df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
                s = df.set_index('Date')['Close'].dropna()
                if len(s) > 0:
                    price_dict[t] = s
        except Exception:
            pass
    return price_dict

# -------------------------------------------------------------
# 5. 심층 리포트 모달 다이얼로그
# -------------------------------------------------------------
@st.dialog("📊 포트폴리오 심층 성과 리포트", width="large")
def show_portfolio_report(p_name, p_info, prices):
    st.markdown(f"### **[{p_name}] 중장기 성과 리포트**")
    st.caption(f"전략 목표: {p_info['desc']} (목표 배당률: {p_info['target_yield_range']})")
    
    valid_tickers = [t for t in p_info["weights"] if t in prices and len(prices[t]) > 0]
    if len(valid_tickers) == len(p_info["weights"]):
        common_idx = prices[valid_tickers[0]].index
        for t in valid_tickers[1:]:
            common_idx = common_idx.intersection(prices[t].index)
        common_idx = sorted(common_idx)
        
        daily_norm = pd.Series(0.0, index=common_idx)
        for t, w in p_info["weights"].items():
            s = prices[t].reindex(common_idx).ffill().bfill()
            daily_norm += (s / s.iloc[0]) * (w / 100)
        
        tot_days = len(daily_norm)
        ret_1y = ((daily_norm.iloc[-1] / daily_norm.iloc[0]) - 1.0) * 100 if tot_days > 0 else 0
        
        idx_6m = max(0, tot_days - 126)
        ret_6m = ((daily_norm.iloc[-1] / daily_norm.iloc[idx_6m]) - 1.0) * 100 if tot_days > 0 else 0
        
        idx_3m = max(0, tot_days - 63)
        ret_3m = ((daily_norm.iloc[-1] / daily_norm.iloc[idx_3m]) - 1.0) * 100 if tot_days > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("최근 3개월 누적 수익률", f"{ret_3m:+.2f}%")
        m2.metric("최근 6개월 누적 수익률", f"{ret_6m:+.2f}%")
        m3.metric("최근 1년 누적 수익률", f"{ret_1y:+.2f}%")
        
        st.markdown("---")
        st.markdown("#### 📅 월별 수익률 히스토리")
        
        daily_df = pd.DataFrame({'value': daily_norm})
        monthly_resample = daily_df.resample('ME').last() if hasattr(pd, 'Grouper') else daily_df.resample('M').last()
        monthly_rets = monthly_resample.pct_change().dropna() * 100
        
        month_rows = []
        for dt, row in monthly_rets.iterrows():
            m_str = dt.strftime("%Y년 %m월")
            val = row['value']
            month_rows.append({
                "기준 월": m_str,
                "월간 수익률": f"{val:+.2f}%",
                "상태": "▲ 상승" if val > 0 else ("▼ 하락" if val < 0 else "- 보합")
            })
        
        st.dataframe(pd.DataFrame(month_rows).iloc[::-1], hide_index=True, use_container_width=True)
        
        st.markdown("#### 📈 최근 1년 자산 가치 성장 추이 (기준지수 1.0)")
        fig_rep = px.line(daily_df, x=daily_df.index, y='value', labels={'value': '자산 지수 (시작=1.0)', 'index': '날짜'})
        fig_rep.update_traces(line_color="#1E3A8A", hovertemplate="%{x|%Y-%m-%d}: 지수 %{y:.3f}")
        fig_rep.update_layout(height=280, margin=dict(l=5, r=5, t=10, b=5))
        st.plotly_chart(fig_rep, use_container_width=True)
    else:
        st.warning("충분한 과거 데이터가 확보되지 않았습니다.")

# -------------------------------------------------------------
# 6. 사이드바 - 자본 설정
# -------------------------------------------------------------
st.sidebar.title("🏢 투자 자본 설정")
inv_capital_man = st.sidebar.number_input("총 투자 자본금 (만원 단위)", min_value=1000, value=50000, step=5000)
total_capital = inv_capital_man * 10000

# -------------------------------------------------------------
# 7. 메인 헤더 & 월 선택 컨트롤러
# -------------------------------------------------------------
st.title("SignalC 법인 포트폴리오")
st.caption("4대 표준 포트폴리오 월별 성과 추이 및 맞춤 진단 시뮬레이터")

main_tab1, main_tab2 = st.tabs(["🏛️ 기본 포트폴리오 (4개 표준 모델)", "⚙️ 커스텀 포트폴리오 (맞춤 진단)"])

prices = load_all_prices()

if prices:
    all_dates = pd.concat([pd.Series(s.index) for s in prices.values() if not s.empty])
    latest_dt = all_dates.max() if not all_dates.empty else datetime.today()
else:
    latest_dt = datetime.today()

curr_year, curr_month = latest_dt.year, latest_dt.month

month_options = []
start_yr, start_mo = 2026, 1

for y in range(start_yr, curr_year + 1):
    m_start = start_mo if y == start_yr else 1
    m_end = curr_month if y == curr_year else 12
    for m in range(m_start, m_end + 1):
        month_options.append(f"{y}년 {m:02d}월")

# -------------------------------------------------------------
# TAB 1: 기본 포트폴리오 (2x2 그리드 & BEST 뱃지 & 리포트)
# -------------------------------------------------------------
with main_tab1:
    col_title, col_sel = st.columns([3, 1])
    with col_sel:
        selected_month_str = st.selectbox(
            "조회 월 선택",
            options=month_options,
            index=len(month_options) - 1,
            label_visibility="collapsed"
        )
    
    sel_year = int(selected_month_str.split("년")[0])
    sel_month = int(selected_month_str.split("년")[1].replace("월", "").strip())
    
    with col_title:
        st.subheader(f"📊 {sel_year}년 {sel_month:02d}월 포트폴리오 성과 추이")

    _, last_day_num = calendar.monthrange(sel_year, sel_month)
    target_start_of_month = datetime(sel_year, sel_month, 1)
    target_end_of_month = datetime(sel_year, sel_month, last_day_num)
    target_prev_month_end = target_start_of_month - pd.Timedelta(days=1)

    perf_records = {}
    calculated_data = {}

    for p_name, p_info in STANDARD_PORTFOLIOS.items():
        valid_tickers = [t for t in p_info["weights"] if t in prices and len(prices[t]) > 0]
        if len(valid_tickers) == len(p_info["weights"]):
            all_month_dates = []
            for t in valid_tickers:
                s_m = prices[t][(prices[t].index >= target_prev_month_end) & (prices[t].index <= target_end_of_month)]
                if not s_m.empty:
                    all_month_dates.extend(s_m.index)
            month_dates = sorted(list(set(all_month_dates)))
            
            if len(month_dates) > 0:
                p_values = pd.Series(0.0, index=month_dates)
                item_series_dict = {}
                item_changes = {}

                for t, w in p_info["weights"].items():
                    s = prices[t]
                    prev_close = s[s.index <= target_start_of_month]
                    prev_val = float(prev_close.iloc[-1]) if not prev_close.empty else float(s.iloc[0])
                    
                    s_in_m = s[(s.index >= target_start_of_month) & (s.index <= target_end_of_month)]
                    curr_val = float(s_in_m.iloc[-1]) if not s_in_m.empty else prev_val
                    
                    chg_pct = ((curr_val - prev_val) / prev_val) * 100 if prev_val != 0 else 0.0
                    item_changes[t] = chg_pct

                    s_aligned = s.reindex(month_dates).ffill().bfill()
                    base_val = s_aligned.iloc[0] if s_aligned.iloc[0] != 0 else 1.0
                    norm_single = (s_aligned / base_val - 1.0) * 100
                    item_series_dict[t] = norm_single
                    p_values += (norm_single * (w / 100))

                final_pct = p_values.iloc[-1]
                perf_records[p_name] = final_pct
                calculated_data[p_name] = {
                    "p_values": p_values,
                    "item_series_dict": item_series_dict,
                    "item_changes": item_changes,
                    "final_pct": final_pct
                }

    best_portfolio = max(perf_records, key=perf_records.get) if perf_records else None

    grid_row1_col1, grid_row1_col2 = st.columns(2)
    grid_row2_col1, grid_row2_col2 = st.columns(2)
    grid_cells = [grid_row1_col1, grid_row1_col2, grid_row2_col1, grid_row2_col2]

    for idx, (p_name, p_info) in enumerate(STANDARD_PORTFOLIOS.items()):
        cell = grid_cells[idx]
        with cell:
            with st.container(border=True):
                if p_name in calculated_data:
                    cdata = calculated_data[p_name]
                    current_perf_pct = cdata["final_pct"]
                    current_perf_krw = total_capital * (current_perf_pct / 100)

                    if current_perf_pct > 0:
                        symbol = "▲"
                        color_style = "color:#DC2626;"
                    elif current_perf_pct < 0:
                        symbol = "▼"
                        color_style = "color:#2563EB;"
                    else:
                        symbol = "-"
                        color_style = "color:#4B5563;"

                    h_col1, h_col2 = st.columns([3, 2])
                    with h_col1:
                        if p_name == best_portfolio and current_perf_pct > 0:
                            st.markdown(f"<div style='display:flex; align-items:center; gap:6px;'>"
                                        f"<h3 style='margin:0;'>{p_name}</h3>"
                                        f"<span style='background-color:#FEF3C7; color:#B45309; font-size:11px; font-weight:bold; padding:2px 8px; border-radius:12px; border:1px solid #FDE68A;'>🏆 BEST 1위</span>"
                                        f"</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<h3 style='margin:0;'>{p_name}</h3>", unsafe_allow_html=True)
                        st.caption(f"목표 배당률: {p_info['target_yield_range']}")

                    with h_col2:
                        if st.button(f"📊 {p_name} 리포트", key=f"btn_rep_{p_name}", use_container_width=True):
                            show_portfolio_report(p_name, p_info, prices)

                    st.markdown(f"""
                    <div style='margin: 6px 0;'>
                        <span style='font-size:13px; color:#555;'>전월 대비 수익률:</span> 
                        <strong style='font-size:19px; {color_style}'>{symbol} {current_perf_pct:+.2f}%</strong>
                        <span style='font-size:13px; margin-left:6px; {color_style}'>({current_perf_krw/10000:+,.0f} 만원)</span>
                    </div>
                    """, unsafe_allow_html=True)

                    fig = go.Figure()
                    fig.add_hline(y=0, line_dash="dot", line_color="#D1D5DB", line_width=1)

                    for t, s_data in cdata["item_series_dict"].items():
                        t_color = TICKER_COLORS.get(t, "#9CA3AF")
                        fig.add_trace(go.Scatter(
                            x=s_data.index,
                            y=s_data,
                            mode='lines',
                            name=f"{t} ({p_info['weights'][t]}%)",
                            line=dict(color=t_color, width=1.5),
                            opacity=0.85,
                            hovertemplate=f'<b>{t}</b>: %{{y:+.2f}}%<extra></extra>'
                        ))

                    fig.add_trace(go.Scatter(
                        x=cdata["p_values"].index,
                        y=cdata["p_values"],
                        mode='lines+markers',
                        name='포트폴리오 합계',
                        line=dict(color='#1E293B', width=3.0),
                        marker=dict(size=4),
                        hovertemplate='<b>포트폴리오 합계</b>: %{y:+.2f}%<extra></extra>'
                    ))

                    fig.update_layout(
                        height=240,
                        margin=dict(l=5, r=5, t=10, b=5),
                        xaxis=dict(
                            range=[target_start_of_month, target_end_of_month],
                            tickformat="%d일",
                            dtick=86400000.0 * 5,
                            showgrid=True,
                            gridcolor="#F3F4F6"
                        ),
                        yaxis=dict(
                            tickformat="+.1f%",
                            showgrid=True,
                            gridcolor="#F3F4F6"
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1,
                            font=dict(size=10)
                        ),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    badge_htmls = []
                    for t, chg in cdata["item_changes"].items():
                        sym = "▲" if chg > 0 else ("▼" if chg < 0 else "-")
                        bg = "#FEE2E2" if chg > 0 else ("#DBEAFE" if chg < 0 else "#F3F4F6")
                        tc = "#991B1B" if chg > 0 else ("#1E40AF" if chg < 0 else "#374151")
                        badge_htmls.append(
                            f"<span style='background-color:{bg}; color:{tc}; font-size:11px; padding:3px 6px; border-radius:4px; margin-right:4px; font-weight:600;'>"
                            f"{t} ({p_info['weights'][t]}%) {sym}{chg:+.1f}%</span>"
                        )
                    st.markdown("<div style='margin-top:2px; line-height:1.9;'>" + "".join(badge_htmls) + "</div>", unsafe_allow_html=True)
                else:
                    st.info("데이터를 집계 중입니다.")

    st.markdown("---")
    st.subheader("📋 포트폴리오 편입 상품 종합 정보")
    asset_rows = []
    for ticker, info in MASTER_ASSETS.items():
        used_types = [f"{p_name}({p_data['weights'][ticker]}%)" for p_name, p_data in STANDARD_PORTFOLIOS.items() if ticker in p_data["weights"]]
        asset_rows.append({
            "티커": ticker,
            "종목명": info["name"],
            "카테고리": info["category"],
            "배당주기": info["payout"],
            "연 배당수익률": f"{info['yield']}%",
            "적용 포트폴리오": ", ".join(used_types)
        })
    st.dataframe(pd.DataFrame(asset_rows), hide_index=True, use_container_width=True)

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

        c_col_chart, c_col_table = st.columns([1, 1])
        with c_col_chart:
            c_pie_df = pd.DataFrame([
                {"Ticker": t, "Weight": w, "Name": MASTER_ASSETS[t]["name"]}
                for t, w in custom_weights.items()
            ])
            fig_custom_pie = px.pie(c_pie_df, values="Weight", names="Ticker", title=f"[{active_custom_name}] 비중 구조", hole=0.4)
            st.plotly_chart(fig_custom_pie, use_container_width=True)

        with c_col_table:
            st.write("**편입 상품별 예상 연 배당 기여도**")
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
                    "연간 예상 배당": f"{ann_div/10000:,.0f} 만원"
                })
            st.dataframe(pd.DataFrame(c_calc_rows), hide_index=True, use_container_width=True)
            
            if st.button("🗑️ 이 커스텀 포트폴리오 삭제"):
                del st.session_state.custom_portfolios[active_custom_name]
                st.rerun()