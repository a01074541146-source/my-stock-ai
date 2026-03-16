import streamlit as st
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
import google.generativeai as genai
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="Gammo Stock AI Dashboard")

# 2. 보안 키 설정 (Streamlit Cloud에서 설정할 값)
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    DART_API_KEY = st.secrets["DART_API_KEY"]
except:
    st.error("⚠️ Streamlit Cloud 설정에서 API 키(Secrets)를 입력해주세요.")
    st.stop()

# 3. AI 모델 로드
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 헤더 섹션 ---
st.title("🛡️ Gammo 역추적 호재 분석 시스템")
st.markdown("---")

# --- 사이드바: 설정 영역 ---
with st.sidebar:
    st.header("⚙️ 분석 설정")
    # 날짜 선택 (기본값: 최근 평일)
    target_date = st.date_input("분석 날짜", datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    
    st.subheader("📈 등락률 기준")
    kospi_threshold = st.number_input("KOSPI 기준 (%)", value=7.0)
    kosdaq_threshold = st.number_input("KOSDAQ 기준 (%)", value=10.0)

# --- 메인 로직: 데이터 수집 ---
@st.cache_data # 동일 날짜 중복 로딩 방지
def get_combined_data(date, p_ratio, d_ratio):
    # KOSPI 추출
    df_p = stock.get_market_price_change_by_ticker(date, date, market="KOSPI").reset_index()
    df_p['시장'] = 'KOSPI'
    df_p = df_p[df_p['등락률'] >= p_ratio]
    
    # KOSDAQ 추출
    df_d = stock.get_market_price_change_by_ticker(date, date, market="KOSDAQ").reset_index()
    df_d['시장'] = 'KOSDAQ'
    df_d = df_d[df_d['등락률'] >= d_ratio]
    
    combined = pd.concat([df_p, df_d])
    combined['종목명'] = combined['티커'].apply(lambda x: stock.get_market_ticker_name(x))
    return combined[['시장', '종목명', '등락률', '거래량', '티커']]

# 데이터 실행
data = get_combined_data(target_date, kospi_threshold, kosdaq_threshold)

# --- 화면 레이아웃 분할 ---
col_list, col_main = st.columns([1, 2])

with col_list:
    st.subheader("🔥 급등주 리스트")
    if not data.empty:
        # 선택박스에서 시장 정보를 같이 보여줌
        data['display_name'] = "[" + data['시장'] + "] " + data['종목명'] + " (" + data['등락률'].astype(str) + "%)"
        selected_display = st.selectbox("분석할 종목 선택", data['display_name'].tolist())
        selected_row = data[data['display_name'] == selected_display].iloc[0]
        selected_ticker = selected_row['티커']
        selected_name = selected_row['종목명']
    else:
        st.warning("조건에 맞는 종목이 없습니다.")
        selected_name = None

with col_main:
    if selected_name:
        st.subheader(f"📊 {selected_name} ({selected_ticker}) 분석 리포트")
        
        # 1. 차트 영역 (Plotly 인터랙티브 차트)
        st.write("📈 **주가 흐름 (최근 30일)**")
        # 여기서 간단한 캔들차트나 선차트를 그릴 수 있습니다.
        st.info("차트 데이터 로딩 중... (추후 캔들차트 코드 삽입 예정)")
        
        # 2. AI 호재 분석 영역
        st.write("🤖 **AI 호재 강도 진단**")
        st.success(f"[{selected_name}]에 대한 DART 공시 분석 및 AI 점수 매기기가 진행됩니다.")
        
        # (여기에 이전 4단계에서 만든 AI 분석 함수를 넣으면 완성입니다!)
