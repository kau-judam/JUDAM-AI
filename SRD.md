# 주담 AI 서버 - SRD (Software Requirements Document)

---

## 1. 개요

### 1.1 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 프로젝트명 | 酒談 (주담) |
| 프로젝트 설명 | 소비자 맞춤형 전통주 공동 기획 펀딩 플랫폼 |
| 개발 기간 | 2026-04-01 ~ 2026-06-30 (12주) |
| 개발 언어 | Python 3.12, Node.js, React |
| 데이터베이스 | PostgreSQL, Redis |
| 인프라 | AWS (EC2, RDS, S3) |

### 1.2 목표 및 범위

#### 1.2.1 목표

1. **개인화된 추천**: 사용자의 취향에 맞는 전통주 추천
2. **커뮤니티**: 전통주 관련 커뮤니티 형성
3. **공동 기획 펀딩**: 사용자가 원하는 전통주 공동 기획 및 펀딩
4. **AI 기반 서비스**: 술BTI 테스트, 추천, 인사이트 제공

#### 1.2.2 범위

| 기능 | 포함 여부 | 비고 |
|------|----------|------|
| 회원가입/로그인 | ✅ 포함 | 카카오 로그인, JWT 토큰 |
| 술BTI 테스트 | ✅ 포함 | 5개 축 설문, 맛 벡터 변환 |
| 추천 서비스 | ✅ 포함 | 맛 벡터 기반, 취향 진화, 역추천 |
| 커뮤니티 | ✅ 포함 | 게시글, 댓글, 좋아요 |
| 펀딩 | ✅ 포함 | 프로젝트 생성, 후원, 진행 상황 |
| 인사이트 대시보드 | ⏳ 예정 | 집계, 예측, 군집화 |
| 법률 필터링 | ⏳ 예정 | 국가법령정보센터 API |

### 1.3 용어 정의

| 용어 | 설명 |
|------|------|
| 술BTI | 술 성향 유형 테스트 (Sool BTI) |
| 맛 벡터 | 전통주의 맛을 8개 축으로 표현한 벡터 |
| 코사인 유사도 | 두 벡터 간의 유사도를 측정하는 지표 |
| 취향 진화 트래킹 | 사용자의 평가 기반으로 맛 벡터 자동 업데이트 |
| 역추천 | 음식/안주 기반으로 어울리는 전통주 추천 |
| RAG | Retrieval-Augmented Generation (검색 증강 생성) |
| 앙커 데이터 | 실제 시음 후 직접 점수 매긴 기준 데이터 |

---

## 2. 기능 요구사항

### 2.1 사용자 기능

#### 2.1.1 회원가입/로그인

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 회원가입 | 이메일, 비밀번호, 닉네임 입력 | 높음 |
| 카카오 로그인 | 카카오 OAuth 2.0 연동 | 높음 |
| 로그인 | 이메일/비밀번호 또는 카카오 로그인 | 높음 |
| 로그아웃 | JWT 토큰 삭제 | 높음 |
| 비밀번호 찾기 | 이메일로 임시 비밀번호 발송 | 중간 |
| 회원정보 수정 | 닉네임, 비밀번호 수정 | 중간 |
| 회원탈퇴 | 계정 삭제 및 데이터 정리 | 낮음 |

#### 2.1.2 술BTI 테스트

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 술BTI 설문 | 5개 축 설문 (단맛, 바디감, 탄산, 풍미, 도수) | 높음 |
| 맛 벡터 변환 | 설문 응답 → 8차원 맛 벡터 변환 | 높음 |
| 결과 표시 | 술BTI 유형 및 맛 벡터 표시 | 높음 |
| 결과 공유 | 술BTI 결과 SNS 공유 | 중간 |
| 결과 저장 | 사용자 프로필에 술BTI 결과 저장 | 중간 |

#### 2.1.3 추천 서비스

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 맛 벡터 기반 추천 | 사용자 맛 벡터와 유사한 전통주 추천 | 높음 |
| 취향 진화 트래킹 | 사용자 평가 기반 맛 벡터 자동 업데이트 | 높음 |
| 음식 기반 역추천 | 음식/안주 기반 전통주 추천 | 높음 |
| 추천 결과 필터링 | 도수, 지역, 양조장 등 필터링 | 중간 |
| 추천 결과 저장 | 추천 기록 저장 | 중간 |

#### 2.1.4 커뮤니티

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 게시글 작성 | 제목, 내용, 이미지 업로드 | 높음 |
| 게시글 조회 | 게시글 목록 및 상세 조회 | 높음 |
| 게시글 수정 | 작성자만 수정 가능 | 높음 |
| 게시글 삭제 | 작성자만 삭제 가능 | 높음 |
| 댓글 작성 | 게시글에 댓글 작성 | 높음 |
| 댓글 수정/삭제 | 작성자만 수정/삭제 가능 | 높음 |
| 좋아요 | 게시글/댓글 좋아요 | 중간 |
| 검색 | 제목, 내용, 작성자 검색 | 중간 |

#### 2.1.5 펀딩

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 프로젝트 생성 | 제목, 내용, 목표 금액, 마감일 설정 | 높음 |
| 프로젝트 조회 | 프로젝트 목록 및 상세 조회 | 높음 |
| 프로젝트 수정/삭제 | 작성자만 수정/삭제 가능 | 높음 |
| 후원 | 프로젝트에 후원 금액 입력 | 높음 |
| 후원 내역 조회 | 후원 내역 조회 | 높음 |
| 진행 상황 업데이트 | 작성자가 진행 상황 업데이트 | 중간 |
| 알림 | 후원, 마감일 등 알림 | 중간 |

### 2.2 관리자 기능

#### 2.2.1 사용자 관리

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 사용자 목록 조회 | 전체 사용자 목록 조회 | 높음 |
| 사용자 상세 조회 | 사용자 상세 정보 조회 | 높음 |
| 사용자 정지 | 사용자 계정 정지 | 중간 |
| 사용자 복구 | 정지된 사용자 계정 복구 | 중간 |

#### 2.2.2 커뮤니티 관리

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 게시글 삭제 | 부적절한 게시글 삭제 | 높음 |
| 댓글 삭제 | 부적절한 댓글 삭제 | 높음 |
| 신고 처리 | 신고 내역 조회 및 처리 | 중간 |

#### 2.2.3 펀딩 관리

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 프로젝트 승인 | 프로젝트 승인/거절 | 높음 |
| 프로젝트 삭제 | 부적절한 프로젝트 삭제 | 높음 |
| 후원 내역 조회 | 전체 후원 내역 조회 | 중간 |
| 정산 | 성공한 프로젝트 정산 | 중간 |

#### 2.2.4 통계/인사이트

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 사용자 통계 | 가입자, 활성 사용자 통계 | 중간 |
| 커뮤니티 통계 | 게시글, 댓글 통계 | 중간 |
| 펀딩 통계 | 프로젝트, 후원 통계 | 중간 |
| 추천 통계 | 추천 클릭, 전환율 통계 | 낮음 |

---

## 3. 비기능 요구사항

### 3.1 성능 요구사항

| 항목 | 요구사항 | 측정 방법 |
|------|----------|----------|
| 응답 시간 | API 응답 시간 500ms 이내 | JMeter, Apache Bench |
| 동시 사용자 | 1,000명 동시 접속 지원 | JMeter, Apache Bench |
| 데이터 처리 | 10,000개 데이터 처리 1초 이내 | Python time 모듈 |
| 캐싱 | 자주 조회하는 데이터 캐싱 | Redis hit rate |

### 3.2 보안 요구사항

| 항목 | 요구사항 | 구현 방법 |
|------|----------|----------|
| 인증 | JWT 토큰 기반 인증 | jsonwebtoken |
| 암호화 | 비밀번호 bcrypt 암호화 | bcrypt |
| HTTPS | 모든 통신 HTTPS | SSL 인증서 |
| SQL Injection | 파라미터화 쿼리 사용 | Prepared Statement |
| XSS | 사용자 입력 이스케이프 | DOMPurify |
| CORS | 허용된 도메인만 접근 허용 | cors 미들웨어 |

### 3.3 가용성 요구사항

| 항목 | 요구사항 | 구현 방법 |
|------|----------|----------|
| 가동률 | 99.9% 가동률 | 로드 밸런싱, 오토스케일링 |
| 백업 | 일일 백업 | AWS RDS 백업 |
| 장애 복구 | 1시간 내 장애 복구 | 모니터링, 알림 |

### 3.4 확장성 요구사항

| 항목 | 요구사항 | 구현 방법 |
|------|----------|----------|
| 수평 확장 | 서버 수평 확장 가능 | Docker, Kubernetes |
| 수직 확장 | 서버 사양 증설 가능 | AWS EC2 |
| 데이터베이스 확장 | 데이터베이스 샤딩 가능 | PostgreSQL 파티셔닝 |

---

## 4. 시스템 아키텍처

### 4.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                     사용자 (브라우저)                      │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
┌────────────────────▼────────────────────────────────────┐
│                  로드 밸런서 (AWS ALB)                     │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐        ┌───────▼────────┐
│  프론트엔드    │        │   백엔드       │
│  (React)      │        │  (Node.js)     │
│  - 술BTI UI   │        │  - 사용자 인증 │
│  - 추천 UI    │        │  - 커뮤니티    │
│  - 커뮤니티 UI│        │  - 펀딩       │
│  - 펀딩 UI    │        │  - AI 프록시   │
└───────┬────────┘        └───────┬────────┘
        │                         │
        │                         │ HTTP
        │                ┌────────▼────────┐
        │                │   AI 서비스      │
        │                │   (FastAPI)     │
        │                │  - 술BTI 변환   │
        │                │  - 추천 알고리즘 │
        │                │  - 취향 진화    │
        │                │  - 역추천       │
        │                └────────┬────────┘
        │                         │
        │                ┌────────▼────────┐
        │                │  데이터베이스   │
        │                │  (PostgreSQL)  │
        │                │  - 사용자       │
        │                │  - 술BTI       │
        │                │  - 커뮤니티     │
        │                │  - 펀딩        │
        │                └────────┬────────┘
        │                         │
        │                ┌────────▼────────┐
        │                │   캐시 (Redis)  │
        │                └─────────────────┘
        │
        │                ┌─────────────────┐
        │                │   스토리지 (S3)  │
        │                └─────────────────┘
        │
        │                ┌─────────────────┐
        │                │   외부 API       │
        │                │  - 카카오 OAuth  │
        │                │  - Gemini API   │
        │                │  - 법률 API     │
        │                └─────────────────┘
```

### 4.2 프론트엔드 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                     프론트엔드 (React)                    │
├─────────────────────────────────────────────────────────┤
│  라우팅 (React Router)                                  │
│  - /login: 로그인 페이지                                 │
│  - /signup: 회원가입 페이지                             │
│  - /sulbti: 술BTI 테스트 페이지                          │
│  - /recommend: 추천 페이지                              │
│  - /community: 커뮤니티 페이지                           │
│  - /funding: 펀딩 페이지                                │
├─────────────────────────────────────────────────────────┤
│  상태 관리 (Redux Toolkit)                               │
│  - userSlice: 사용자 상태                               │
│  - sulbtiSlice: 술BTI 상태                              │
│  - recommendSlice: 추천 상태                            │
│  - communitySlice: 커뮤니티 상태                         │
│  - fundingSlice: 펀딩 상태                              │
├─────────────────────────────────────────────────────────┤
│  API 호출 (Axios)                                        │
│  - userAPI: 사용자 API                                   │
│  - sulbtiAPI: 술BTI API                                  │
│  - recommendAPI: 추천 API                                │
│  - communityAPI: 커뮤니티 API                            │
│  - fundingAPI: 펀딩 API                                  │
├─────────────────────────────────────────────────────────┤
│  UI 컴포넌트 (Material-UI)                               │
│  - Button, TextField, Card, etc.                         │
└─────────────────────────────────────────────────────────┘
```

### 4.3 백엔드 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   백엔드 (Node.js + Express)             │
├─────────────────────────────────────────────────────────┤
│  라우팅 (Express Router)                                 │
│  - /api/auth: 인증 라우팅                                │
│  - /api/user: 사용자 라우팅                              │
│  - /api/sulbti: 술BTI 라우팅                             │
│  - /api/recommend: 추천 라우팅                           │
│  - /api/community: 커뮤니티 라우팅                       │
│  - /api/funding: 펀딩 라우팅                             │
├─────────────────────────────────────────────────────────┤
│  미들웨어 (Express Middleware)                           │
│  - cors: CORS 설정                                       │
│  - helmet: 보안 헤더 설정                                │
│  - morgan: 로깅                                          │
│  - express-rate-limit: 속도 제한                        │
│  - auth: JWT 인증 미들웨어                               │
├─────────────────────────────────────────────────────────┤
│  컨트롤러 (Controller)                                   │
│  - authController: 인증 컨트롤러                         │
│  - userController: 사용자 컨트롤러                       │
│  - sulbtiController: 술BTI 컨트롤러                      │
│  - recommendController: 추천 컨트롤러                   │
│  - communityController: 커뮤니티 컨트롤러               │
│  - fundingController: 펀딩 컨트롤러                     │
├─────────────────────────────────────────────────────────┤
│  서비스 (Service)                                         │
│  - authService: 인증 서비스                              │
│  - userService: 사용자 서비스                            │
│  - sulbtiService: 술BTI 서비스                           │
│  - recommendService: 추천 서비스                         │
│  - communityService: 커뮤니티 서비스                     │
│  - fundingService: 펀딩 서비스                           │
├─────────────────────────────────────────────────────────┤
│  모델 (Model)                                             │
│  - User: 사용자 모델                                     │
│  - Sulbti: 술BTI 모델                                    │
│  - Post: 게시글 모델                                     │
│  - Comment: 댓글 모델                                    │
│  - Funding: 펀딩 모델                                    │
├─────────────────────────────────────────────────────────┤
│  데이터베이스 (Sequelize ORM)                             │
│  - PostgreSQL: 주 데이터베이스                           │
│  - Redis: 캐시                                          │
└─────────────────────────────────────────────────────────┘
```

### 4.4 AI 서비스 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   AI 서비스 (FastAPI)                      │
├─────────────────────────────────────────────────────────┤
│  라우팅 (FastAPI Router)                                 │
│  - /api/survey/convert: 술BTI 설문 → 맛 벡터 변환        │
│  - /api/recommend: 맛 벡터 기반 추천                     │
│  - /api/taste/update: 사용자 취향 업데이트              │
│  - /api/taste/history/{user_id}: 취향 히스토리 조회     │
│  - /api/food/recommend: 음식 기반 추천                   │
├─────────────────────────────────────────────────────────┤
│  핵심 로직 (Core)                                         │
│  - recommender.py: 추천 시스템                           │
│  - vector_extractor.py: 맛 벡터 추출                     │
│  - survey_converter.py: 설문 변환기                       │
├─────────────────────────────────────────────────────────┤
│  추천 알고리즘                                            │
│  - 코사인 유사도: 맛 벡터 기반 추천                      │
│  - 취향 진화 트래킹: 사용자 평가 기반 업데이트           │
│  - 역추천: 음식/안주 기반 추천                           │
│  - 다중 소스 앙상블: 맛 + 원재료 + 지역                  │
├─────────────────────────────────────────────────────────┤
│  데이터 (Data)                                            │
│  - makgeolli_with_vectors_v2.json: 막걸리 데이터        │
│  - anchors.json: 앙커 데이터                            │
├─────────────────────────────────────────────────────────┤
│  외부 API (External API)                                  │
│  - Gemini API: AI 생성                                   │
│  - 법률 API: 법률 필터링 (예정)                          │
└─────────────────────────────────────────────────────────┘
```

### 4.5 인프라 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                      AWS 인프라                           │
├─────────────────────────────────────────────────────────┤
│  네트워크 (VPC)                                           │
│  - 퍼블릭 서브넷: ALB, EC2                               │
│  - 프라이빗 서브넷: RDS, Redis                           │
├─────────────────────────────────────────────────────────┤
│  로드 밸런싱 (ALB)                                        │
│  - HTTPS 터미네이션                                       │
│  - 헬스 체크                                             │
├─────────────────────────────────────────────────────────┤
│  컴퓨팅 (EC2)                                            │
│  - 프론트엔드: React 빌드 파일 호스팅                    │
│  - 백엔드: Node.js 서버                                 │
│  - AI 서비스: FastAPI 서버                              │
├─────────────────────────────────────────────────────────┤
│  데이터베이스 (RDS)                                       │
│  - PostgreSQL: 주 데이터베이스                           │
│  - Multi-AZ: 고가용성                                    │
├─────────────────────────────────────────────────────────┤
│  캐시 (ElastiCache)                                       │
│  - Redis: 캐시                                          │
├─────────────────────────────────────────────────────────┤
│  스토리지 (S3)                                            │
│  - 이미지: 사용자 이미지, 프로젝트 이미지                │
│  - 정적 파일: React 빌드 파일                           │
├─────────────────────────────────────────────────────────┤
│  CI/CD (CodePipeline)                                    │
│  - 소스: GitHub                                          │
│  - 빌드: CodeBuild                                       │
│  - 배포: CodeDeploy                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 5. API 명세서

### 5.1 사용자 API

#### 5.1.1 회원가입

**엔드포인트**: `POST /api/auth/signup`

**요청**:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "nickname": "닉네임"
}
```

**응답**:
```json
{
  "status": "success",
  "message": "회원가입이 완료되었습니다.",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "nickname": "닉네임",
    "created_at": "2026-04-28T00:00:00Z"
  }
}
```

#### 5.1.2 로그인

**엔드포인트**: `POST /api/auth/login`

**요청**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**응답**:
```json
{
  "status": "success",
  "message": "로그인이 완료되었습니다.",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "nickname": "닉네임"
  }
}
```

#### 5.1.3 카카오 로그인

**엔드포인트**: `POST /api/auth/kakao`

**요청**:
```json
{
  "code": "카카오 인증 코드"
}
```

**응답**:
```json
{
  "status": "success",
  "message": "카카오 로그인이 완료되었습니다.",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "nickname": "닉네임",
    "kakao_id": "123456789"
  }
}
```

### 5.2 술BTI API

#### 5.2.1 술BTI 설문 → 맛 벡터 변환

**엔드포인트**: `POST /api/sulbti/convert`

**요청**:
```json
{
  "sweetness": 7,
  "body": 5,
  "carbonation": 3,
  "flavor": 6,
  "alcohol": 4
}
```

**응답**:
```json
{
  "status": "success",
  "taste_vector": {
    "sweetness": 7.0,
    "body": 5.0,
    "carbonation": 3.0,
    "flavor": 6.0,
    "alcohol": 4.0,
    "acidity": 5.0,
    "aroma_intensity": 5.0,
    "finish": 5.0
  }
}
```

#### 5.2.2 술BTI 결과 저장

**엔드포인트**: `POST /api/sulbti/save`

**요청**:
```json
{
  "taste_vector": {
    "sweetness": 7.0,
    "body": 5.0,
    "carbonation": 3.0,
    "flavor": 6.0,
    "alcohol": 4.0,
    "acidity": 5.0,
    "aroma_intensity": 5.0,
    "finish": 5.0
  }
}
```

**응답**:
```json
{
  "status": "success",
  "message": "술BTI 결과가 저장되었습니다.",
  "sulbti_id": 1
}
```

### 5.3 추천 API

#### 5.3.1 맛 벡터 기반 추천

**엔드포인트**: `POST /api/recommend`

**요청**:
```json
{
  "user_vector": {
    "sweetness": 7.0,
    "body": 5.0,
    "carbonation": 3.0,
    "flavor": 6.0,
    "alcohol": 4.0,
    "acidity": 5.0,
    "aroma_intensity": 5.0,
    "finish": 5.0
  },
  "top_k": 10,
  "exclude_ids": []
}
```

**응답**:
```json
[
  {
    "id": "makgeolli_0",
    "name": "이동 생 쌀 막걸리",
    "similarity": 0.95,
    "abv": 6.0,
    "brewery": "이동주조",
    "region": "경기도 포천시 이동면 화동로 2466",
    "features": "적절한 산미가 음식맛을 도드라져 갈비찜과 어울린다.",
    "taste_vector": {
      "sweetness": 1.7,
      "body": 5.0,
      "carbonation": 5.0,
      "flavor": 5.0,
      "alcohol": 5.0,
      "acidity": 6.4,
      "aroma_intensity": 5.0,
      "finish": 5.0
    }
  }
]
```

#### 5.3.2 사용자 취향 업데이트

**엔드포인트**: `POST /api/taste/update`

**요청**:
```json
{
  "user_id": "user_1",
  "drink_id": "makgeolli_0",
  "rating": 5,
  "tags": ["달콤", "산미"]
}
```

**응답**:
```json
{
  "status": "success",
  "message": "사용자 user_1의 취향이 업데이트되었습니다."
}
```

#### 5.3.3 취향 히스토리 조회

**엔드포인트**: `GET /api/taste/history/{user_id}`

**응답**:
```json
{
  "user_id": "user_1",
  "history_count": 3,
  "history": [
    {
      "drink_id": "makgeolli_0",
      "drink_name": "이동 생 쌀 막걸리",
      "rating": 5,
      "tags": ["달콤", "산미"],
      "taste_vector": {
        "sweetness": 1.7,
        "body": 5.0,
        "carbonation": 5.0,
        "flavor": 5.0,
        "alcohol": 5.0,
        "acidity": 6.4,
        "aroma_intensity": 5.0,
        "finish": 5.0
      },
      "timestamp": "2026-04-28T00:00:00Z"
    }
  ],
  "evolved_taste_vector": {
    "sweetness": 6.5,
    "body": 5.0,
    "carbonation": 4.5,
    "flavor": 5.5,
    "alcohol": 4.5,
    "acidity": 5.5,
    "aroma_intensity": 5.0,
    "finish": 5.0
  }
}
```

#### 5.3.4 음식 기반 추천

**엔드포인트**: `POST /api/food/recommend`

**요청**:
```json
{
  "food": "갈비찜",
  "top_k": 5
}
```

**응답**:
```json
[
  {
    "id": "makgeolli_0",
    "name": "이동 생 쌀 막걸리",
    "abv": 6.0,
    "brewery": "이동주조",
    "region": "경기도 포천시 이동면 화동로 2466",
    "features": "적절한 산미가 음식맛을 도드라져 갈비찜과 어울린다.",
    "taste_vector": {
      "sweetness": 1.7,
      "body": 5.0,
      "carbonation": 5.0,
      "flavor": 5.0,
      "alcohol": 5.0,
      "acidity": 6.4,
      "aroma_intensity": 5.0,
      "finish": 5.0
    },
    "reason": "갈비찜과 잘 어울립니다"
  }
]
```

### 5.4 커뮤니티 API

#### 5.4.1 게시글 작성

**엔드포인트**: `POST /api/community/posts`

**요청**:
```json
{
  "title": "게시글 제목",
  "content": "게시글 내용",
  "images": ["image1.jpg", "image2.jpg"]
}
```

**응답**:
```json
{
  "status": "success",
  "message": "게시글이 작성되었습니다.",
  "post": {
    "id": 1,
    "title": "게시글 제목",
    "content": "게시글 내용",
    "images": ["image1.jpg", "image2.jpg"],
    "author": {
      "id": 1,
      "nickname": "닉네임"
    },
    "created_at": "2026-04-28T00:00:00Z"
  }
}
```

#### 5.4.2 게시글 목록 조회

**엔드포인트**: `GET /api/community/posts?page=1&limit=10`

**응답**:
```json
{
  "status": "success",
  "posts": [
    {
      "id": 1,
      "title": "게시글 제목",
      "content": "게시글 내용",
      "author": {
        "id": 1,
        "nickname": "닉네임"
      },
      "created_at": "2026-04-28T00:00:00Z",
      "likes_count": 10,
      "comments_count": 5
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 10
}
```

#### 5.4.3 게시글 상세 조회

**엔드포인트**: `GET /api/community/posts/{post_id}`

**응답**:
```json
{
  "status": "success",
  "post": {
    "id": 1,
    "title": "게시글 제목",
    "content": "게시글 내용",
    "images": ["image1.jpg", "image2.jpg"],
    "author": {
      "id": 1,
      "nickname": "닉네임"
    },
    "created_at": "2026-04-28T00:00:00Z",
    "likes_count": 10,
    "comments_count": 5,
    "is_liked": true
  }
}
```

#### 5.4.4 댓글 작성

**엔드포인트**: `POST /api/community/posts/{post_id}/comments`

**요청**:
```json
{
  "content": "댓글 내용"
}
```

**응답**:
```json
{
  "status": "success",
  "message": "댓글이 작성되었습니다.",
  "comment": {
    "id": 1,
    "content": "댓글 내용",
    "author": {
      "id": 1,
      "nickname": "닉네임"
    },
    "created_at": "2026-04-28T00:00:00Z"
  }
}
```

### 5.5 펀딩 API

#### 5.5.1 프로젝트 생성

**엔드포인트**: `POST /api/funding/projects`

**요청**:
```json
{
  "title": "프로젝트 제목",
  "description": "프로젝트 설명",
  "target_amount": 1000000,
  "deadline": "2026-06-30T00:00:00Z",
  "images": ["image1.jpg", "image2.jpg"]
}
```

**응답**:
```json
{
  "status": "success",
  "message": "프로젝트가 생성되었습니다.",
  "project": {
    "id": 1,
    "title": "프로젝트 제목",
    "description": "프로젝트 설명",
    "target_amount": 1000000,
    "current_amount": 0,
    "deadline": "2026-06-30T00:00:00Z",
    "author": {
      "id": 1,
      "nickname": "닉네임"
    },
    "created_at": "2026-04-28T00:00:00Z"
  }
}
```

#### 5.5.2 프로젝트 목록 조회

**엔드포인트**: `GET /api/funding/projects?page=1&limit=10`

**응답**:
```json
{
  "status": "success",
  "projects": [
    {
      "id": 1,
      "title": "프로젝트 제목",
      "description": "프로젝트 설명",
      "target_amount": 1000000,
      "current_amount": 500000,
      "deadline": "2026-06-30T00:00:00Z",
      "author": {
        "id": 1,
        "nickname": "닉네임"
      },
      "created_at": "2026-04-28T00:00:00Z",
      "progress": 50
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 10
}
```

#### 5.5.3 후원

**엔드포인트**: `POST /api/funding/projects/{project_id}/pledge`

**요청**:
```json
{
  "amount": 10000
}
```

**응답**:
```json
{
  "status": "success",
  "message": "후원이 완료되었습니다.",
  "pledge": {
    "id": 1,
    "project_id": 1,
    "user_id": 1,
    "amount": 10000,
    "created_at": "2026-04-28T00:00:00Z"
  }
}
```

### 5.6 관리자 API

#### 5.6.1 사용자 목록 조회

**엔드포인트**: `GET /api/admin/users?page=1&limit=10`

**응답**:
```json
{
  "status": "success",
  "users": [
    {
      "id": 1,
      "email": "user@example.com",
      "nickname": "닉네임",
      "created_at": "2026-04-28T00:00:00Z",
      "is_active": true
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 10
}
```

#### 5.6.2 사용자 정지

**엔드포인트**: `POST /api/admin/users/{user_id}/suspend`

**요청**:
```json
{
  "reason": "정지 사유"
}
```

**응답**:
```json
{
  "status": "success",
  "message": "사용자가 정지되었습니다."
}
```

#### 5.6.3 통계 조회

**엔드포인트**: `GET /api/admin/stats`

**응답**:
```json
{
  "status": "success",
  "stats": {
    "users": {
      "total": 1000,
      "active": 800,
      "suspended": 10
    },
    "community": {
      "posts": 500,
      "comments": 2000
    },
    "funding": {
      "projects": 50,
      "pledges": 300,
      "total_amount": 5000000
    }
  }
}
```

---

## 6. 데이터베이스 설계

### 6.1 ERD

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   users     │       │   sulbtis   │       │   posts     │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ id (PK)     │       │ id (PK)     │
│ email       │       │ user_id (FK)│◄──────│ user_id (FK)│
│ password    │       │ sweetness   │       │ title       │
│ nickname    │       │ body        │       │ content     │
│ kakao_id    │       │ carbonation │       │ images      │
│ is_active   │       │ flavor      │       │ likes_count │
│ created_at  │       │ alcohol     │       │ created_at  │
│ updated_at  │       │ acidity     │       │ updated_at  │
└─────────────┘       │ aroma_intensity│     └─────────────┘
                      │ finish      │
                      │ created_at  │
                      └─────────────┘
                            │
                            │
┌─────────────┐       ┌────┴─────┐       ┌─────────────┐
│  pledges    │       │  comments │       │  projects   │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ project_id  │◄──────│ post_id (FK)│       │ title       │
│ user_id (FK)│       │ user_id (FK)│       │ description │
│ amount      │       │ content     │       │ target_amount│
│ created_at  │       │ created_at  │       │ current_amount│
└─────────────┘       └─────────────┘       │ deadline    │
                                            │ images      │
                                            │ status      │
                                            │ created_at  │
                                            │ updated_at  │
                                            └─────────────┘
```

### 6.2 테이블 명세서

#### 6.2.1 users 테이블

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 사용자 ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 이메일 |
| password | VARCHAR(255) | NOT NULL | 비밀번호 (bcrypt) |
| nickname | VARCHAR(50) | NOT NULL | 닉네임 |
| kakao_id | VARCHAR(255) | UNIQUE, NULL | 카카오 ID |
| is_active | BOOLEAN | DEFAULT true | 활성 여부 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 수정일 |

#### 6.2.2 sulbtis 테이블

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 술BTI ID |
| user_id | BIGINT | FK, NOT NULL | 사용자 ID |
| sweetness | FLOAT | NOT NULL | 단맛 (0~10) |
| body | FLOAT | NOT NULL | 바디감 (0~10) |
| carbonation | FLOAT | NOT NULL | 탄산 (0~10) |
| flavor | FLOAT | NOT NULL | 풍미 (0~10) |
| alcohol | FLOAT | NOT NULL | 도수 (0~10) |
| acidity | FLOAT | NOT NULL | 산미 (0~10) |
| aroma_intensity | FLOAT | NOT NULL | 향 강도 (0~10) |
| finish | FLOAT | NOT NULL | 여운 (0~10) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 생성일 |

#### 6.2.3 posts 테이블

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 게시글 ID |
| user_id | BIGINT | FK, NOT NULL | 사용자 ID |
| title | VARCHAR(255) | NOT NULL | 제목 |
| content | TEXT | NOT NULL | 내용 |
| images | JSON | NULL | 이미지 URL 리스트 |
| likes_count | INT | DEFAULT 0 | 좋아요 수 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 수정일 |

#### 6.2.4 comments 테이블

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 댓글 ID |
| post_id | BIGINT | FK, NOT NULL | 게시글 ID |
| user_id | BIGINT | FK, NOT NULL | 사용자 ID |
| content | TEXT | NOT NULL | 내용 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 생성일 |

#### 6.2.5 projects 테이블

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 프로젝트 ID |
| user_id | BIGINT | FK, NOT NULL | 사용자 ID |
| title | VARCHAR(255) | NOT NULL | 제목 |
| description | TEXT | NOT NULL | 설명 |
| target_amount | BIGINT | NOT NULL | 목표 금액 |
| current_amount | BIGINT | DEFAULT 0 | 현재 금액 |
| deadline | TIMESTAMP | NOT NULL | 마감일 |
| images | JSON | NULL | 이미지 URL 리스트 |
| status | VARCHAR(20) | DEFAULT 'pending' | 상태 (pending, approved, rejected, completed, failed) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 수정일 |

#### 6.2.6 pledges 테이블

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 후원 ID |
| project_id | BIGINT | FK, NOT NULL | 프로젝트 ID |
| user_id | BIGINT | FK, NOT NULL | 사용자 ID |
| amount | BIGINT | NOT NULL | 후원 금액 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 생성일 |

### 6.3 인덱스 설계

| 테이블 | 인덱스명 | 컬럼 | 타입 | 설명 |
|--------|----------|------|------|------|
| users | idx_email | email | UNIQUE | 이메일 중복 방지 |
| users | idx_kakao_id | kakao_id | UNIQUE | 카카오 ID 중복 방지 |
| sulbtis | idx_user_id | user_id | INDEX | 사용자별 술BTI 조회 |
| posts | idx_user_id | user_id | INDEX | 사용자별 게시글 조회 |
| posts | idx_created_at | created_at | INDEX | 최신 게시글 조회 |
| comments | idx_post_id | post_id | INDEX | 게시글별 댓글 조회 |
| projects | idx_user_id | user_id | INDEX | 사용자별 프로젝트 조회 |
| projects | idx_status | status | INDEX | 상태별 프로젝트 조회 |
| pledges | idx_project_id | project_id | INDEX | 프로젝트별 후원 조회 |
| pledges | idx_user_id | user_id | INDEX | 사용자별 후원 조회 |

---

## 7. 테스트 계획

### 7.1 단위 테스트

| 모듈 | 테스트 항목 | 도구 |
|------|------------|------|
| 사용자 | 회원가입, 로그인, 로그아웃 | Jest |
| 술BTI | 설문 변환, 결과 저장 | Jest |
| 추천 | 맛 벡터 추천, 취향 업데이트 | Jest |
| 커뮤니티 | 게시글 CRUD, 댓글 CRUD | Jest |
| 펀딩 | 프로젝트 CRUD, 후원 | Jest |

### 7.2 통합 테스트

| 모듈 | 테스트 항목 | 도구 |
|------|------------|------|
| 인증 | JWT 토큰 검증 | Supertest |
| 술BTI | 설문 → 추천 통합 | Supertest |
| 커뮤니티 | 게시글 → 댓글 통합 | Supertest |
| 펀딩 | 프로젝트 → 후원 통합 | Supertest |

### 7.3 시스템 테스트

| 테스트 항목 | 설명 | 도구 |
|------------|------|------|
| 성능 테스트 | 1,000명 동시 접속 | JMeter |
| 부하 테스트 | 10,000개 데이터 처리 | Apache Bench |
| 보안 테스트 | SQL Injection, XSS | OWASP ZAP |

### 7.4 인수 테스트

| 테스트 항목 | 설명 | 도구 |
|------------|------|------|
| 사용자 시나리오 | 회원가입 → 술BTI → 추천 | Cypress |
| 커뮤니티 시나리오 | 게시글 작성 → 댓글 작성 | Cypress |
| 펀딩 시나리오 | 프로젝트 생성 → 후원 | Cypress |

---

## 8. 배포 계획

### 8.1 개발 환경

| 항목 | 설정 |
|------|------|
| 도메인 | dev.juddam.com |
| 데이터베이스 | PostgreSQL (개발용) |
| 캐시 | Redis (개발용) |
| 로그 | 개발용 로그 레벨 |

### 8.2 스테이징 환경

| 항목 | 설정 |
|------|------|
| 도메인 | staging.juddam.com |
| 데이터베이스 | PostgreSQL (스테이징용) |
| 캐시 | Redis (스테이징용) |
| 로그 | 스테이징용 로그 레벨 |

### 8.3 운영 환경

| 항목 | 설정 |
|------|------|
| 도메인 | juddam.com |
| 데이터베이스 | PostgreSQL (운영용, Multi-AZ) |
| 캐시 | Redis (운영용, ElastiCache) |
| 로그 | 운영용 로그 레벨, CloudWatch |

---

## 9. 부록

### 9.1 용어 사전

| 용어 | 설명 |
|------|------|
| JWT | JSON Web Token, 인증 토큰 |
| CORS | Cross-Origin Resource Sharing, 교차 출처 리소스 공유 |
| ORM | Object-Relational Mapping, 객체 관계 매핑 |
| CRUD | Create, Read, Update, Delete |
| API | Application Programming Interface |
| UI | User Interface |
| UX | User Experience |

### 9.2 참고 자료

- FastAPI 공식 문서: https://fastapi.tiangolo.com/
- React 공식 문서: https://react.dev/
| Node.js 공식 문서: https://nodejs.org/
- PostgreSQL 공식 문서: https://www.postgresql.org/docs/
- Redis 공식 문서: https://redis.io/docs/
- AWS 공식 문서: https://docs.aws.amazon.com/

### 9.3 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 1.0 | 2026-04-28 | 초안 작성 | 황주원 |
