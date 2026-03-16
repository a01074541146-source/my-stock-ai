import streamlit as st
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
import google.generativeai as genai
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 간판 달기
st.set_page_config(layout="wide", page_title="밍쥐네피자가게", page_icon="🍕")

# 2. HF Spaces용 API 키 세팅
API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if not API_KEY:
    st.error("⚠️ 환경변수(Secrets)에 GEMINI_API_KEY를 설정해주세요.")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 탭 분리
tab1, tab2 = st.tabs(["🔥 1. 당일 주도주 & 호재 감별기", "📉 2. 눌림목 추적 및 호재 차트"])

# ==========================================
# 탭 1: 당일 급등 종목 및 호재 요약 (그대로 유지)
# ==========================================
with tab1:
    st.header("🔍 KOSPI/KOSDAQ 주도주 재료 분석")
    st.write("당일 급등 종목을 추출하고, 호재 파급력을 1~5성급으로 분류합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        target_date = st.date_input("검색 날짜", datetime.now() - timedelta(days=1))
    with col2:
        up_ratio = st.number_input("기준 상승률 (X%)", min_value=1.0, value=15.0, step=1.0)
        
    if st.button("🚀 주도주 호재 추출 및 채점"):
        date_str = target_date.strftime("%Y%m%d")
        with st.spinner("시장 데이터를 수집하고 파급력을 계산 중입니다..."):
            try:
                df_kpi = stock.get_market_price_change_by_ticker(date_str, date_str, market="KOSPI").reset_index()
                df_kdq = stock.get_market_price_change_by_ticker(date_str, date_str, market="KOSDAQ").reset_index()
                
                df_all = pd.concat([df_kpi, df_kdq])
                if df_all.empty:
                    st.warning("데이터가 없습니다. 휴장일이거나 아직 장 마감 전일 수 있습니다.")
                else:
                    df_filtered = df_all[df_all['등락률'] >= up_ratio].copy()
                    df_filtered['종목명'] = df_filtered['티커'].apply(lambda x: stock.get_market_ticker_name(x))
                    
                    if df_filtered.empty:
                        st.info(f"{up_ratio}% 이상 상승한 종목이 없습니다.")
                    else:
                        st.dataframe(df_filtered[['종목명', '종가', '등락률', '거래량']].sort_values(by='등락률', ascending=False))
                        
                        top_tickers = df_filtered['종목명'].head(5).tolist()
                        prompt = f"""
                        날짜: {date_str}
                        {up_ratio}% 이상 급등한 주도주: {', '.join(top_tickers)}
                        
                        위 종목들이 당일 어떤 재료로 급등했는지 요약하고, 아래 [실전 별점 가이드라인]을 '참고'하여 호재 강도를 ⭐ 개수로 평가해줘.
                        ⚠️ 주의: 아래 기준은 예시일 뿐이므로, 실제 뉴스의 파급력, 섹터의 중요도를 융통성 있게 판단할 것.
                        
                        [실전 별점 가이드라인 (참고용)]
                        ⭐ (1개): 실체 없는 테마 편승, 단순 MOU, 찌라시
                        ⭐⭐ (2개): 평범한 실적 개선, 소규모 수주
                        ⭐⭐⭐ (3개): 시총 10% 이상 수주, 정책 수혜, 임상 순항
                        ⭐⭐⭐⭐ (4개): 대기업 파트너십, 어닝 서프라이즈, 주도 테마 대장주
                        ⭐⭐⭐⭐⭐ (5개): 글로벌 빅테크 공급망 진입, 초대형 M&A, FDA 승인 등 시장 지배적 호재
                        
                        출력 형식:
                        ### [종목명] (별점: ⭐⭐⭐)
                        - **호재 요약:** (간략히)
                        - **평가 이유:** (설명)
                        """
                        response = model.generate_content(prompt)
                        st.subheader("🤖 AI 호재 강도 채점표")
                        st.markdown(response.text)
            except Exception as e:
                st.error("데이터 수집 중 오류가 발생했습니다.")

# ==========================================
# 탭 2: 눌림목 판별 (Y,Z 수치) + 차트에 호재 마킹
# ==========================================
with tab2:
    st.header("🎯 눌림목 추적 및 차트 호재 마킹")
    st.write("사용자가 지정한 Y~Z% 눌림목 구간인지 확인하고, 차트 위에 당시 터진 호재와 강도를 표시합니다.")
    
    t2_col1, t2_col2 = st.columns(2)
    with t2_col1:
        t2_ticker = st.text_input("종목명 검색", value="")
        lookback = st.slider("역추적 기간 (일)", 5, 20, 14)
    with t2_col2:
        y_val = st.number_input("Y: 최소 하락 조건 (종가 대비 %)", max_value=0.0, value=-7.0, step=1.0)
        z_val = st.number_input("Z: 최대 하락 마지노선 (종가 대비 %)", max_value=0.0, value=-15.0, step=1.0)
        
    if st.button("차트 불러오기 및 호재 체크"):
        if not t2_ticker:
            st.warning("종목명을 입력해주세요.")
        else:
            tickers = stock.get_market_ticker_list(market="ALL")
            target_code = next((t for t in tickers if stock.get_market_ticker_name(t) == t2_ticker), None)
            
            if target_code:
                with st.spinner(f"차트를 불러오고 과거 호재를 마킹 중입니다..."):
                    end_dt = datetime.now()
                    start_dt = end_dt - timedelta(days=lookback + 10) 
                    
                    df_chart = stock.get_market_ohlcv_by_date(start_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d"), target_code)
                    
                    if not df_chart.empty:
                        # 1. 기준봉(슈팅 발생일) 찾기
                        ref_idx = df_chart['종가'].idxmax()
                        ref_close = df_chart.loc[ref_idx, '종가']
                        ref_vol = df_chart.loc[ref_idx, '거래량']
                        ref_date = ref_idx.strftime("%Y-%m-%d")
                        
                        current_close = df_chart['종가'].iloc[-1]
                        
                        # 사용자 지시: 종가 대비 Y, Z 조건 충족 여부 텍스트 출력
                        drop_rate = ((current_close / ref_close) - 1) * 100
                        st.subheader(f"📊 {t2_ticker} 현재 상태")
                        if z_val <= drop_rate <= y_val:
                            st.success(f"현재 하락률 {drop_rate:.2f}% (Y~Z 구간 내 진입 상태)")
                        else:
                            st.warning(f"현재 하락률 {drop_rate:.2f}% (Y~Z 구간 이탈 또는 미달)")
                        
                        # 2. AI에게 '차트에 표시할 짧은 말풍선용 텍스트' 요청
                        mark_prompt = f"""
                        {ref_date} 무렵 {t2_ticker} 주가가 급등했습니다.
                        이때의 핵심 호재를 파악해서 딱 '별점(⭐ 1~5개) + 10자 이내의 짧은 키워드'로만 답해주세요.
                        예시: ⭐⭐⭐⭐ 대규모 공급계약
                        """
                        mark_text = model.generate_content(mark_prompt).text.strip()
                        
                        # 3. 차트 그리기 (호재 마킹 집중)
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                        
                        fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['시가'], high=df_chart['고가'], low=df_chart['저가'], close=df_chart['종가'], name='가격'), row=1, col=1)
                        
                        # 핵심: 기준봉(슈팅일) 위에 AI 호재 텍스트 마킹 달기
                        fig.add_annotation(
                            x=ref_idx,
                            y=df_chart.loc[ref_idx, '고가'],
                            text=f"🔥 {mark_text}",
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1,
                            arrowwidth=2,
                            arrowcolor="red",
                            ax=0,
                            ay=-40,
                            bgcolor="yellow",
                            font=dict(color="black", size=13),
                            row=1, col=1
                        )
                        
                        # 거래량 차트
                        colors = ['red' if row['종가'] >= row['시가'] else 'blue' for index, row in df_chart.iterrows()]
                        fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['거래량'], marker_color=colors, name='거래량'), row=2, col=1)
                        
                        fig.update_layout(title=f"{t2_ticker} 차트 및 호재 마킹 내역", xaxis_rangeslider_visible=False, height=500)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 상세 설명은 하단에 텍스트로 분리
                        detail_prompt = f"종목: {t2_ticker}\n기준일: {ref_date}\n이 날짜의 호재 상세 내용과 현재 거래량 감소 추이에 대한 분석을 짧게 요약해줘."
                        res_detail = model.generate_content(detail_prompt)
                        st.markdown(f"**📝 AI 상세 분석:**\n{res_detail.text}")
                        
            else:
                st.error("정확한 종목명을 입력해주세요.")
