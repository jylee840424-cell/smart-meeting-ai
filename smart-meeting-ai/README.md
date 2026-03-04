Markdown
# 🏢 무한상사 AI 거버넌스 시스템 (Smart Meeting AI)

사내 회의 영상을 AI로 분석하고, RAG 기반 전문가 챗봇을 통해 의사결정을 검증 및 자문하는 엔터프라이즈 하이브리드 AI 시스템입니다.

---

## 🚀 시작하기 (Getting Started)

본 프로젝트는 백엔드(FastAPI)와 프론트엔드(Streamlit)가 독립적으로 구성된 아키텍처를 따릅니다. 의존성 충돌을 막기 위해 패키지가 분리되어 있습니다. (Python 3.10+ 권장)

### 1. 환경 설정 및 패키지 설치
프로젝트 최상단(Root)에서 가상환경을 생성하고, 양쪽 모듈의 필수 패키지를 모두 설치합니다.

```bash
# 1-1. 가상환경 생성 및 활성화
python -m venv .venv
source .venv/Scripts/activate  # Windows 환경: .venv\Scripts\activate

# 1-2. 백엔드 & 프론트엔드 패키지 독립 설치
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
2. 환경 변수 (.env) 세팅
프로젝트 최상단 폴더(Root)에 .env 파일을 생성하고 아래의 인증 키를 입력하세요.

코드 스니펫
OPENAI_API_KEY="sk-당신의-오픈AI-API-키"
3. 서버 실행 (Local Development)
터미널을 2개 열어 백엔드와 프론트엔드를 각각 실행합니다.

[Terminal 1: Backend 서버 실행]

Bash
cd backend
python main.py
# 서버 가동 확인 및 API 문서: http://localhost:8000/docs
[Terminal 2: Frontend UI 실행]

Bash
cd frontend
streamlit run app.py
# 브라우저에서 UI가 자동 실행되며 무한상사 AI 시스템에 접속됩니다.
📂 프로젝트 구조 (Architecture)
우리 프로젝트는 역할과 책임이 명확히 분리된 Layered Architecture(계층형 아키텍처)를 따릅니다.

Plaintext
smart-meeting-ai/
├── backend/               # FastAPI 백엔드 (API 및 AI 엔진)
│   ├── api/v1/            # API 엔드포인트 라우터 (chat, meeting, video)
│   ├── core/              # DB 초기화 등 코어 설정
│   ├── pipelines/         # AI 분석 파이프라인 (비디오 STT 5단계, RAG)
│   ├── schemas/           # Pydantic 데이터 검증 모델
│   ├── services/          # 핵심 비즈니스 로직 및 DB 통신
│   ├── main.py            # 백엔드 서버 실행 엔트리포인트 (직접 실행)
│   └── requirements.txt   # 백엔드 전용 의존성 패키지
├── frontend/              # Streamlit 프론트엔드 (UI)
│   ├── components/        # 공통 UI 컴포넌트 (사이드바 등)
│   ├── pages/             # 개별 화면 (Upload, Chat, Report)
│   ├── services/          # 백엔드 API 통신 전담 모듈
│   ├── app.py             # 프론트엔드 실행 엔트리포인트 (라우팅 전담)
│   └── requirements.txt   # 프론트엔드 전용 의존성 패키지
├── database/              # 데이터베이스 물리적 저장소
│   ├── relational/        # 메타데이터 DB (SQLite, schema.sql)
│   └── vector/            # AI RAG용 벡터 DB (Chroma)
└── infrastructure/        # 클라우드 배포 인프라 설정 (Docker Compose)


🧠 시스템 상세 설계 (System Design)
세부적인 아키텍처 및 시스템 동작 원리는 아래 탭을 클릭하여 확인하세요.

<details>
<summary><b>1. AI 파이프라인 워크플로우 (클릭하여 펴기)</b></summary>



비디오 업로드 시 백엔드의 pipelines/video_pipeline을 통해 다음 5단계의 AI 분석 파이프라인이 자동 실행됩니다.

Audio Extraction: 영상에서 음성 추출 (yt-dlp 등)

STT (Speech-to-Text): 음성을 텍스트로 변환 (Whisper 등)

Speaker Separation: 화자 분리 및 스크립트화 처리

Vector Embedding: 텍스트 청크 분할 후 Chroma DB 적재

Summarization: 회의 내용 구조화 및 요약 생성

</details>

<details>
<summary><b>2. AI 에이전트 설계 (RAG 챗봇)</b></summary>



전문가 챗봇(02_expert_chat.py)은 상황에 맞는 두 가지 모드를 지원합니다.

공식 검증 모드: 환각(Hallucination)을 철저히 배제하고, Vector DB에 적재된 실제 회의록 내용만을 바탕으로 답변과 출처(Source)를 정확히 짚어냅니다. (Streaming 응답 지원)

전문가 자문 모드: 회의 내용을 바탕으로 외부 도메인 지식을 결합하여, 리스크를 분석하고 새로운 해결책과 인사이트를 제시합니다.

</details>

<details>
<summary><b>3. 핵심 API 명세 (API Spec)</b></summary>



백엔드는 프론트엔드와 완벽히 분리된 RESTful API를 제공합니다.

POST /api/v1/video/upload : 회의 영상 업로드 및 STT 분석 파이프라인 트리거

GET /api/v1/video/status/{meeting_id} : 비동기 분석 진행 상태 폴링(Polling)

POST /api/v1/chat/ask : 회의 컨텍스트 기반 RAG 챗봇 질의응답 (타닥타닥 Streaming 반환)

(전체 API 스펙 및 테스트는 http://localhost:8000/docs의 Swagger UI에서 확인 가능)

</details>