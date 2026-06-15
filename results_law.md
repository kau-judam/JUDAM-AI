# 법률 조문 임베딩 — 완료 보고 (results_law.md)

결정: 임베딩 모델 = **MiniLM(`paraphrase-multilingual-MiniLM-L12-v2`, 384차원)**, 로컬 수집·임베딩, **PersistentClient** 전환.
원칙 준수: 각 단계 코드 확인 후 진행, EphemeralClient fallback 유지, 키 값 미출력.

## 최종 상태: ✅ 완료 (1~5단계)

| 단계 | 상태 | 핵심 결과 |
|------|------|-----------|
| 1. LAW_API 연결 복구 | ✅ | UA/Referer 헤더 추가로 "사용자 검증 실패" 해소 → `LawSearch` 정상 수신 |
| 2. 조문 수집 | ✅ | 9개 법령 전부 성공, **1,719개 조문/청크** → `data/law_articles.json` |
| 3. MiniLM + PersistentClient | ✅ | 1,719청크 임베딩 적재 → `rag_db/law` (count>0 시 재적재 스킵), Ephemeral fallback 유지 |
| 4. 검색 경로 전환 + 검증 | ✅ | 조문 단위 검색 동작, `/api/law/filter` end-to-end 위반 탐지 확인 |
| 5. 문서/설정 | ✅ | `.gitignore`에 `rag_db/`, API_GUIDE 법률 섹션 갱신 |

## 1. LAW_API 연결 복구
- **원인**: 기존엔 헤더 없이 호출 → law.go.kr이 "정확한 서버 IP/도메인 등록" 요구하며 거부.
- **수정**(`app/law_client.py`): `AsyncClient(headers=self.law_headers)` — `User-Agent`(브라우저)+`Referer: https://www.law.go.kr/`. `LAW_USER_AGENT`/`LAW_REFERER` 환경변수 override 가능.
- **OC 점검**: `.env`의 `LAW_API_KEY`(=OC)는 길이 9, `@` 없음 → 이메일 ID 형식 적합. 호출 성공(`LawSearch` 수신)으로 유효 확인.
- **재검증**: `query=주세법` 단일 호출 → `{"LawSearch": {...}}` 정상(이전 "사용자 검증 실패" 사라짐).
- **응답 구조 확정**(추측 아님, 실제 확인):
  - 검색 `lawSearch.do` → `LawSearch.law[]` (`법령일련번호`=MST, `법령ID`, `법령명한글`)
  - 본문 `lawService.do?MST=...` → `법령.조문.조문단위[]` (`조문번호`/`조문제목`/`조문내용`/`조문여부`/`조문키`/`항`/`호`)
  - ※ 기존 코드의 `lawDetailService.do`는 **404** → `lawService.do`로 정정. 기존 `data["Law"]` 파싱도 `LawSearch.law`로 정정(`get_relevant_articles`).

## 2. 조문 수집 (`scripts/build_law_index.py`)
- 9개 법령(`LawClient.LAWS`) 각각 검색→MST→본문 조회, `조문여부=='조문'`만 추출.
- **삭제 조문(빈 플레이스홀더) 제외**, 긴 조문은 ~800자 청크 분할. `조문키`로 ID 유일성 보장(+최종 가드).
- 호출 사이 0.7s 지연. 결과: **1,719청크** (법령별: 청소년보호 76 · 식품위생 161 · 전통주 41 · 표시광고 45 · 주세 30 · 상표 273 · 자본시장 789 · 저작권 228 · 전자상거래 76).
- `data/law_articles.json` 저장(커밋 대상 — 재빌드 가능).

## 3. MiniLM 임베딩 + PersistentClient (`app/embedder.py`, `app/law_rag.py`, `scripts/embed_law_index.py`)
- `embedder.py`: 모델 `paraphrase-multilingual-MiniLM-L12-v2`(384d). `LAW_EMBED_MODEL`로 override.
- `law_rag.py`: **PersistentClient(`rag_db/law`) 컬렉션 `law_articles`** 우선. count>0이면 조문 인덱스 사용, 아니면 **EphemeralClient `law_documents`(9개 설명) fallback**.
  - startup의 `initialize(9개 법령)`은 조문 인덱스가 있으면 **자동 스킵**(인덱스 보존 검증 완료).
  - `build_article_index(records, rebuild=)`: 배치(64) 임베딩 적재, count>0+rebuild=False 시 스킵.
- 적재: 1,719청크 → `rag_db/law/law_articles`.

## 4. 검색 검증
- 직접 검색(MiniLM 쿼리 임베딩):
  - `'청소년 주류 판매'` → 청소년보호법 제28조·제16조 ✅
  - `'원금 보장'` → 자본시장법 제3조 ✅(법령 정확)
  - `'숙취 해소'` → 상표법/자본시장법 ❌ (MiniLM 의미 매칭 한계)
- **`/api/law/filter` end-to-end**(1회 Gemini): 입력 "숙취 해소 막걸리" → `violation=True`, 식품위생법 과대광고 탐지, 수정 권고 정상.
  - ※ 필터는 **키워드 1차 탐지 → RAG 컨텍스트 → Gemini** 순서라, RAG 의미검색이 약한 쿼리도 키워드 단계에서 보완됨.
- 차원: 인덱스·쿼리 모두 MiniLM 384d로 일치(rebuild로 기존 768d 흔적 제거). 9개 설명 컬렉션과 분리(Ephemeral vs Persistent)되어 충돌 없음.

## 5. 한계 / 운영 메모
- **MiniLM 의미 정확도 제한**: 다국어 경량 모델이라 한국어 법률 의미검색은 일부 쿼리에서 부정확(`숙취 해소` 등). 정확도 우선이면 ko-sbert(768d)로 교체 후 `--rebuild` 필요(`LAW_EMBED_MODEL` 변경). 키워드 1차 탐지가 있어 실사용 영향은 제한적.
- **LAW_API IP/도메인 의존**: 헤더로 통과했으나, 환경에 따라 호출 IP가 바뀌면 law.go.kr이 다시 거부할 수 있음. 그 경우 **재수집만 막히고**(인덱스는 영속이라 검색은 계속 동작) — 아래 재빌드로 복구.

## 재빌드 명령 (IP 변경/조문 갱신 시)
```bash
# 1) 조문 재수집 (LAW_API 호출 — 헤더 자동 적용)
python scripts/build_law_index.py          # → data/law_articles.json

# 2) MiniLM 재임베딩 + Persistent 적재
python scripts/embed_law_index.py --rebuild  # 기존 인덱스 지우고 재적재
#    (인자 없이 실행하면 count>0 시 스킵)

# 모델 교체 시: .env 에 LAW_EMBED_MODEL=jhgan/ko-sroberta-multitask 후 위 2) --rebuild
```
- `rag_db/`는 `.gitignore`(대용량). `data/law_articles.json`은 커밋 → 어디서나 2)만으로 인덱스 복구 가능.
- LAW_API가 막히면 1)을 건너뛰고 기존 `data/law_articles.json`으로 2)만 실행해도 됨.

## EC2 배포 절차 (RAG 인덱스 확보)
`rag_db/`는 `.gitignore`라 git으로 안 간다. 반면 `data/law_articles.json`(1,719청크)·스크립트는 커밋됨. 두 가지 방법:

**① EC2에서 재임베딩 (권장, 재현 가능)**
```bash
git pull                                      # data/law_articles.json + scripts 확보
pip install sentence-transformers chromadb
python scripts/embed_law_index.py --rebuild   # json → rag_db/law (MiniLM 384d, CPU 1~2분)
```
- 선행: 디스크 2GB+, 최초 실행 시 MiniLM(~470MB) HF 다운로드용 아웃바운드 인터넷, 메모리 t3.small(2GB)+ 권장(t2.micro는 OOM 위험). 법령 API 호출 불필요.

**② 로컬 rag_db/ 직접 복사 (빠름)**
```bash
scp -r rag_db/ ec2-user@<EC2_HOST>:/path/to/juddam-ai/rag_db/
```
- 선행: **런타임 쿼리 임베딩 때문에 EC2에도 sentence-transformers+MiniLM은 필요**(검색이 쿼리를 MiniLM으로 임베딩). chromadb 버전을 로컬과 일치시킬 것.

> 어느 방법이든 EC2에 sentence-transformers+MiniLM 설치는 필수(②도 면제 안 됨). 폐쇄망이면 MiniLM 모델 캐시(`HF_HOME`)도 함께 복사. 상세 진단·필터 테스트 결과는 `results_law_test.md` 참고.
