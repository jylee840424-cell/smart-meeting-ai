import streamlit as st


def render_sidebar():
    """무한상사 테마의 좌측 사이드바를 렌더링합니다."""
    with st.sidebar:
        # [수정 포인트] 브랜드명 color를 #F8FAFC에서 #0F172A로 변경하여 시인성 확보
        st.markdown(
            """
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,1,0" rel="stylesheet" />
        <div style='margin-bottom: 35px; padding-top: 10px;'>
            <div style='display: flex; align-items: center; margin-bottom: 2px;'>
                <span class="material-symbols-outlined" style="font-size: 32px; color: #3B82F6; margin-right: 10px;">
                    domain
                </span>
                <span style='font-size: 36px; font-weight: 900; color: #0F172A; letter-spacing: 2px;'>무한상사</span>
            </div>
            <div style='font-size: 20px; color: #64748B; font-weight: 600; letter-spacing: 0.5px; margin-left: 42px;'>
                Internal Governance System
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.caption("MAIN MENU")
        st.page_link(
            "pages/01_video_upload.py",
            label="Meeting Analysis",
            icon=":material/analytics:",
        )
        st.page_link(
            "pages/02_expert_chat.py", label="Expert Chat", icon=":material/smart_toy:"
        )
        st.page_link(
            "pages/03_action_reports.py",
            label="Action & Reports",
            icon=":material/assignment:",
        )

        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        st.markdown("---")
        st.page_link("app.py", label="Settings", icon=":material/settings:")

        st.markdown(
            """
        <div style='display: flex; align-items: center; margin-top: 10px;'>
            <div style='background-color: #1E293B; border: 1px solid #334155; border-radius: 50%; width: 40px; height: 40px; display: flex; justify-content: center; align-items: center; font-size: 20px;'>👨‍💼</div>
            <div style='margin-left: 12px;'>
                <strong style='font-size: 14px; color: #1E293B;'>Director Morgan</strong><br>
                <span style='font-size: 12px; color: #64748B;'>Strategic Planning Head</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
