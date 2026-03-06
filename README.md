💡 프로젝트 폴더 구조 및 환경 분리 사유
본 프로젝트는 프론트엔드와 백엔드를 통합 관리하는 모노레포(Monorepo) 구조를 채택하여, 최상단(Root) 경로를 smart-meeting-ai로 완벽히 일원화했습니다. 이를 통해 .git과 .gitignore의 제어 범위를 일치시킴으로써, 팀원 각자의 로컬 가상환경(venv)이나 대용량 미디어 파일이 깃허브에 섞여 올라가는 치명적인 충돌을 원천 차단하고 안전한 협업 환경을 구축했습니다.


# 🏢 무한상사 AI 거버넌스 시스템 (Smart Meeting AI)

사내 회의 영상을 AI로 분석하고, RAG 기반 전문가 챗봇을 통해 의사결정을 검증 및 자문하는 엔터프라이즈 하이브리드 AI 시스템입니다.


##  시작하기 (Getting Started)

본 프로젝트는 백엔드(FastAPI)와 프론트엔드(Streamlit)가 독립적으로 구성된 아키텍처를 따릅니다. 의존성 충돌을 막기 위해 패키지가 분리되어 있습니다. 

AI 라이브러리(ChromaDB, Numpy 등)의 완벽한 호환성과 팀원 간의 원활한 협업을 위해 **최상단(Root) 단일 가상환경** 체제를 유지하며, **Python 3.10.x** 버전을 표준으로 사용합니다.

다른 버전(3.11 이상, 3.9 이하) 사용 시 C++ 컴파일 에러나 의존성 충돌이 발생할 수 있으니 반드시 버전을 맞춰주세요.

* **FFmpeg**: 영상 처리를 위해 OS 레벨에 설치되어 있어야 합니다. (제일 하단에 설치 방법 참조)

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
세부적인 아키텍처 및 시스템 동작 원리.

<details>
<summary><b>1. AI 파이프라인 워크플로우 (클릭하여 펴기)</b></summary>

비디오 업로드 시 백엔드의 `pipelines/video_pipeline`을 통해 다음 5단계의 AI 분석 파이프라인이 자동 실행됩니다.

* **Audio Extraction:** 영상에서 음성 추출 (yt-dlp, FFmpeg 기반)
* **STT (Speech-to-Text):** 음성을 텍스트로 변환 (Whisper 모델 활용)
* **Speaker Separation:** 화자 분리(Diarization) 및 타임스탬프 기반 스크립트화 처리
* **Vector Embedding:** 텍스트 청크 분할 후 의미론적 검색을 위해 Vector DB(Chroma DB / Pinecone)에 적재
* **Summarization:** LLM 기반 회의 내용 구조화 및 핵심 요약 생성

</details>

<details>
<summary><b>2. AI 에이전트 설계 (RAG 챗봇) (클릭하여 펴기)</b></summary>

전문가 챗봇(`02_expert_chat.py`)은 상황에 맞는 두 가지 하이브리드 모드를 지원하여 답변의 신뢰성과 활용성을 극대화합니다.

* 공식 검증 모드 (Strict RAG): 환각(Hallucination)을 철저히 배제하고, Vector DB에 적재된 실제 회의록 내용만을 바탕으로 답변하며 명확한 출처(Source Reference)를 제공합니다.
* 전문가 자문 모드 (Advisory Agent): 회의 내용을 바탕으로 외부 도메인 지식을 결합하여, 리스크를 분석하고 새로운 해결책과 비즈니스 인사이트를 제시합니다.

</details>

<details>
<summary><b>3. 회의록/액션 아이템 자동 생성 및 AI 자율 리포트 에이전트 (클릭하여 펴기)</b></summary>

사내 DATABASE에 적재된 회의 영상 데이터(STT 텍스트 및 Vector DB)를 기반으로, 후속 업무를 자동화하고 심층 인사이트를 제공하는 지능형 워크플로우입니다. (LangGraph / CrewAI 프레임워크 기반)

* <b>사내 데이터 연동 및 회의록/액션 아이템 추출 (Data Integration & Extraction):</b>
  저장된 회의 스크립트를 LLM이 분석하여 전체 회의록을 구조화합니다. 이와 동시에 담당자(Assignee), 기한(Due Date), 작업 목표가 포함된 실행 가능한 '액션 아이템(Action Items)'을 정형화된 데이터 포맷(JSON)으로 자동 추출합니다.
* <b>동적 키워드 파싱 (Dynamic Keyword Parsing):</b>
  도출된 액션 아이템 내에서 추가적인 리서치, 시장 조사, 또는 기술 검토가 필요한 핵심 비즈니스 키워드(Key Entities)를 에이전트가 스스로 식별합니다.
* <b>AI 에이전트 자율 서치 및 리포트 자동 생성 (Autonomous Research & Reporting):</b>
  추출된 키워드를 트리거(Trigger)로 백그라운드 워커가 활성화됩니다. 에이전트는 외부 검색 도구(Tavily Search API 등) 및 사내 지식 기반을 자율적으로 탐색하며 데이터를 수집하고, 액션 아이템 실행에 직접적인 도움이 되는 '심층 분석 리포트'를 자동 발행합니다.

</details>

<details>
<summary><b>4. 핵심 API 명세 (API Spec) (클릭하여 펴기)</b></summary>

백엔드는 프론트엔드와 완벽히 분리된 FastAPI 기반 RESTful API를 제공하며, 긴 작업은 비동기(Async) 큐를 통해 처리됩니다.

* `POST /api/v1/video/upload` : 회의 영상 업로드 및 5단계 STT 분석 파이프라인 트리거
* `GET /api/v1/video/status/{meeting_id}` : 비동기 분석 및 리포트 생성 진행 상태 폴링(Polling)  
* `GET /api/v1/meeting/{meeting_id}/action-items` : JSON 형태로 구조화된 액션 아이템 및 자동 생성 리포트 조회
* `POST /api/v1/chat/ask` : 회의 컨텍스트 기반 RAG 챗봇 질의응답
*(전체 API 스펙 및 데이터 스키마는 `http://localhost:8000/docs`의 Swagger UI에서 확인 및 테스트 가능)*

</details>

**FFmpeg**: 영상 처리를 위해 OS 레벨에 설치하는 방법

FFmpeg 설치 가이드 (Windows 요약본)

###  필수 프로그램 설치: FFmpeg (영상/음성 처리 도구)

프로젝트의 AI 파이프라인(`yt-dlp`, `pydub`)이 영상과 음성을 자르고 압축하려면, 가상환경 내부가 아닌 **PC(OS) 자체에 FFmpeg가 반드시 설치**되어 있어야 합니다.

**🪟 Windows 1분 설치 가이드**

1. 명령 프롬프트(cmd) 또는 PowerShell을 열고 아래 명령어를 실행합니다.
   
   bash
   winget install ffmpeg

설치가 끝나면 환경변수 적용을 위해 열려있는 터미널과 VS Code를 모두 껐다가 다시 켜주세요.

터미널에 아래 명령어를 입력하여 정상 설치를 확인합니다.

    Bash
    ffmpeg -version