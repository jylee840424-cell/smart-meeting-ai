import streamlit as st

# 1. 글로벌 페이지 설정 (브라우저 탭 이름, 아이콘, 레이아웃 넓게 쓰기)
# 이 설정은 이후 전환될 모든 pages/ 파일들에 공통적으로 적용됩니다.
st.set_page_config(page_title="무한상사 AI 거버넌스 시스템", page_icon="🏢", layout="wide")

# 2. 대시보드를 대신할 우리의 새로운 메인(Landing) 페이지로 즉시 강제 이동!
st.switch_page("pages/01_video_upload.py")
