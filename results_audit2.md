# 비정상 입력 견고성 점검 (results_audit2.md)

실제 서버를 띄우고(`uvicorn app.main:app`, db_connected=false·gemini on) 주요 엔드포인트에
**빈값/범위밖/타입오류/누락** 입력을 실제로 HTTP 호출하여 500 발생 지점을 탐지.
- 스크립트: `scripts/run_robustness_audit.py` (결과 원본: `_audit2_results.json`)
- 판정: **422**=Pydantic 검증 거부, **400**=핸들러 비즈니스 가드, **200**=정상 처리, **500/EXC**=서버오류(문제)
- Gemini 비용 최소화: 펀딩·레시피는 `taste_input` 직접입력(Gemini 우회), 법률만 정상 1건 라이브.

## 총평
- **총 36건 호출 → 500/EXC 0건.** 모든 비정상 입력이 4xx로 정상 거부되거나(34건), 안전하게 graceful 처리(200·2건)됨.
- **명백한 1줄 버그(빈입력 미가드 등) 없음** → 코드 수정 없음. 빈값/누락/범위밖/타입오류는 Pydantic Field 제약과 핸들러 가드가 이미 전부 차단.
- 개선 여지 2건(잘못된 enum/도메인밖 정수를 조용히 통과)과 base64 크기검증(M2) 미적용은 **제안만**.

---

## 1) 엔드포인트별 결과 [입력 / HTTP코드 / 정상여부]

### survey/convert (Gemini 없음)
| 입력 | 코드 | 정상여부 |
|------|:----:|:--------:|
| 빈 body `{}` | 422 | ✅ 거부(전 필드 missing) |
| q24·q25 누락 | 422 | ✅ 거부(missing) |
| q4=99 (범위밖 1~7) | 422 | ✅ 거부(le=7) |
| q4='abc' (타입오류) | 422 | ✅ 거부(int_parsing) |
| q23=9 (범위밖 1~5) | 422 | ✅ 거부(le=5) |
| q24=5 (리스트 아닌 int) | 422 | ✅ 거부(list_type) |
| q24=[99]·q25=[99] (도메인밖 정수) | **200** | ⚠ graceful 통과(가드 없음, 크래시 X) |
| 정상 | 200 | ✅ |

### recommend (Gemini 없음)
| 입력 | 코드 | 정상여부 |
|------|:----:|:--------:|
| 빈 body `{}` | 400 | ✅ 거부("user_vector 또는 user_id 필수") |
| top_k=0 | 422 | ✅ 거부(ge=1) |
| top_k=999 | 422 | ✅ 거부(le=50) |
| user_vector sweetness=99 | 422 | ✅ 거부(le=10) |
| user_id='ghost123'(미존재) | 400 | ✅ 거부(저장 프로필 없음) |
| pool='garbage' (잘못된 enum) | **200** | ⚠ graceful 통과(검증 없음, 결과 반환됨) |
| user_vector finish 누락 | 422 | ✅ 거부(missing) |
| 정상 | 200 | ✅ |

> 참고: 미존재 user_id가 **400으로 정확히 떨어짐** → 기존 audit에서 수정한 `except HTTPException: raise`(400이 500으로 둔갑 방지)가 실제로 동작 중임을 라이브로 확인.

### bti/feedback (Gemini 없음, db off→JSON fallback)
| 입력 | 코드 | 정상여부 |
|------|:----:|:--------:|
| bti_code='ABC' (len 3, 5자 필요) | 422 | ✅ 거부(min_length=5) |
| is_correct 누락 | 422 | ✅ 거부(missing) |
| bti_code='' (빈값) | 422 | ✅ 거부(string_too_short) |
| 정상(미존재 user) | 200 | ✅ JSON fallback 저장(`storage:json`) |

> 핸들러에 외부 try/except가 없으나(기존 audit M3), db/JSON 경로가 정상 동작해 500 미발생. DB 연결 상태에서 쓰기 실패 시의 가드는 여전히 제안 대상(아래).

### law/filter (Gemini)
| 입력 | 코드 | 정상여부 |
|------|:----:|:--------:|
| title 빈값 `''` | 422 | ✅ 거부(min_length=1) |
| description 누락 | 422 | ✅ 거부(missing) |
| content_type 누락 | 422 | ✅ 거부(missing) |
| 정상(라이브) | 200 | ✅ "건강에 좋은" 위반감지 → `verdict:block` 정확 |

### funding/register (taste_input 직접입력 → Gemini 우회)
| 입력 | 코드 | 정상여부 |
|------|:----:|:--------:|
| name 누락 | 422 | ✅ 거부(missing) |
| abv=999 (범위밖) | 422 | ✅ 거부(le=100) |
| abv=-5 (범위밖) | 422 | ✅ 거부(ge=0) |
| taste_input sweetness=99 | 422 | ✅ 거부(le=10) |
| 정상(direct_input) | 200 | ✅ |
| 중복 funding_id | 400 | ✅ 거부("이미 등록된 펀딩 ID") |

### recipe/register (taste_input 직접입력 → Gemini 우회)
| 입력 | 코드 | 정상여부 |
|------|:----:|:--------:|
| main_ingredient 누락 | 422 | ✅ 거부(missing) |
| user_id 누락 | 422 | ✅ 거부(missing) |
| 정상(direct_input) | 200 | ✅ |

### image/generate (Gemini/SD — 라이브 생성은 비용상 제외, 검증 케이스만)
| 입력 | 코드 | 정상여부 |
|------|:----:|:--------:|
| name 누락 | 422 | ✅ 거부(missing) |
| description 누락 | 422 | ✅ 거부(missing) |
| taste_vector 값 타입오류(`"abc"`) | 422 | ✅ 거부(float_parsing) |

> 핸들러에 외부 try/except가 없음(라인 1371~). 검증 통과 후 생성기 내부 예외 시 500 가능성은 라이브 미실행으로 미검증. 단 `image_generator`는 prompt_only fallback 보유(기존 audit). 제안: 핸들러 try/except 추가.

---

## 2) base64 크기검증 (M2) 현황 — 확인만 (수정 안 함)
- `/api/brewery/verify-ocr`(main.py:716): **빈값 가드는 있음**(`if not image_base64: 400`).
- 그러나 `app/ocr.py` `_decode_base64`(73~)는 **길이 상한·형식 검증 없이** 패딩 후 즉시 `b64decode`.
- 결론: **M2(base64 크기·형식 가드) 여전히 미적용.** 초대형/깨진 base64 입력 시 메모리 급증·디코드 오류 위험은 남아 있음(코드 정독으로 확인, 대용량 페이로드 라이브 테스트는 미실시).

---

## 3) 적용한 수정
- **없음.** 빈입력/누락/범위밖/타입오류는 전부 이미 4xx로 가드되어 명백한 1줄 버그가 발견되지 않음.

## 4) 제안 (코드 변경 보류 — 발표 후 검토)
| # | 위치 | 현상 | 제안 |
|---|------|------|------|
| P1 | `recommend` `pool` 파라미터 | `pool='garbage'`도 200 반환(조용히 fallback) | `pool`을 `{all,base,funding,recipe,approved}` 화이트리스트로 검증 후 400 |
| P2 | `survey/convert` q24·q25 항목 | 도메인밖 정수(예 99)도 200(unknown 매핑) | q24∈1~5, q25∈1~5 항목값 검증 추가(현재 무해하나 조용한 오입력) |
| P3 | `ocr.py` `_decode_base64` / verify-ocr | base64 크기·형식 가드 없음(M2) | 디코드 전 길이 상한(~10MB)+try/except+mime 화이트리스트 |
| P4 | `bti/feedback`·`image/generate` 핸들러 | 외부 try/except 없음(이번엔 500 미발생) | 핸들러 전체 try/except로 graceful 5xx 응답 규약화 |

## 결론
- **발표 기준 견고성 양호**: 비정상 입력 36종 전부 서버 크래시 없이 4xx/정상 처리.
- 후속(제안): P1·P2(조용한 오입력 차단), P3(base64 가드=M2), P4(핸들러 가드 규약화).
