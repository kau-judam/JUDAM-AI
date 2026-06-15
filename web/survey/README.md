# 술BTI 설문 페이지 — 배포 체크리스트

정적 페이지(`index.html`) 하나로 동작하며, AI 서버 API 호출 없이 브라우저에서 술BTI를 계산합니다.
제출 데이터는 구글시트(Apps Script 웹앱)에 한 줄씩 저장됩니다.

```
web/survey/
├─ index.html        ← 설문 페이지 (이것만 배포하면 됨)
├─ apps_script.gs    ← 구글시트에 붙여넣을 수집 스크립트
└─ README.md         ← 이 문서
```

---

## A. 구글시트 새로 만들기
1. https://sheets.google.com 접속 → **빈 스프레드시트** 생성.
2. 이름은 자유(예: `술BTI 응답`). 시트 탭은 그대로 둬도 됩니다(스크립트가 `responses` 탭을 자동 생성).

## B. Apps Script 붙여넣기
1. 그 시트에서 상단 메뉴 **확장 프로그램 → Apps Script** 클릭.
2. 편집기에 기본으로 있는 `function myFunction() {}` 를 **전부 지우고**,
   `apps_script.gs` 파일 내용을 **전체 복사해 붙여넣기**.
3. 상단 **저장 아이콘(💾)** 클릭(프로젝트 이름 물으면 아무거나).

## C. 웹 앱으로 배포 → URL 복사
1. 우측 상단 **배포 → 새 배포**.
2. **유형 선택(톱니 ⚙) → 웹 앱**.
3. 설정:
   - **실행 계정(Execute as): 나(본인 계정)**
   - **액세스 권한(Who has access): 모든 사용자(Anyone)**
4. **배포** 클릭 → 권한 승인 요청이 뜨면 본인 계정으로 **허용**
   (“이 앱은 Google에서 확인하지 않았습니다” → 고급 → 안전하지 않음(이동) → 허용).
5. 표시되는 **웹 앱 URL** 복사. 형태: `https://script.google.com/macros/s/XXXX/exec`
6. (확인) 그 URL 을 브라우저 새 탭에서 그냥 열어 **`{"status":"ok"}`** 가 보이면 정상(doGet).

## D. index.html 에 URL 연결
1. `web/survey/index.html` 을 편집기로 열기.
2. 다음 줄을 찾아 따옴표 안에 복사한 URL 을 붙여넣기:
   ```js
   const SHEET_WEBHOOK_URL = "";
   ```
   →
   ```js
   const SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/XXXX/exec";
   ```
   - 비워두면 전송 안 하고 브라우저 콘솔에 `console.log` 로만 출력됩니다(개발용 fallback).

## E. Vercel 배포 (둘 중 하나)

### 방법 1) Vercel CLI
```bash
npm i -g vercel          # 최초 1회
cd web/survey
vercel                   # 안내에 따라 로그인/프로젝트 생성 (미리보기 URL 발급)
vercel --prod            # 프로덕션 배포
```
- 루트가 `web/survey` 라 `index.html` 이 사이트 최상위(`/`)로 서빙됩니다.

### 방법 2) GitHub 연동
1. 이 저장소를 GitHub 에 push.
2. https://vercel.com → **Add New… → Project → 저장소 Import**.
3. **Root Directory** 를 `web/survey` 로 지정.
4. **Framework Preset: Other** (빌드 명령/출력 디렉터리 비움 — 정적 파일).
5. **Deploy** → 배포 URL 발급. 이후 push 마다 자동 재배포.

> 참고: `index.html` 의 `SHEET_WEBHOOK_URL` 을 채운 뒤 배포해야 시트에 저장됩니다.
> URL 을 나중에 바꾸면 다시 배포(또는 push)하세요.

## F. 동작 확인
1. 배포된 링크 접속 → 설문 25문항 + 피드백까지 **끝까지 응답** 후 제출.
2. 제출 시 페이지에 **“응답이 저장되었습니다”** 가 뜨는지 확인
   (URL 미설정이면 “제출 완료 (로컬 로그)”, 네트워크 실패면 “저장 실패…”).
3. 구글시트의 **`responses` 탭**에 새 행이 들어왔는지 확인
   (헤더: `timestamp, q1…q25, q24_text, q25_text, sweetness…finish, bti_code, character_name, taste_profile_summary, calculation_source, is_correct, feedback_reason`).

---

## 저장되는 컬럼
`timestamp` · `q1`~`q25`(각 칸, q24/q25 는 선택 인덱스 콤마결합) · `q24_text` · `q25_text` ·
8축(`sweetness, body, carbonation, flavor, alcohol, acidity, aroma_intensity, finish`) ·
`bti_code` · `character_name` · `taste_profile_summary` · `calculation_source`(`local_js`) ·
`is_correct`(예/아니오) · `feedback_reason`(결과가 맞지 않는 이유/메모) · `calculation_result_json`.

## 자주 묻는 문제
- **시트에 행이 안 들어옴**: ① 액세스 권한이 ‘모든 사용자’인지, ② `SHEET_WEBHOOK_URL` 끝이 `/exec` 인지(`/dev` 아님), ③ 코드 수정 후 **새 배포**(또는 ‘배포 관리 → 편집 → 새 버전’)했는지 확인.
- **제출은 됐다는데 저장 실패 메시지**: 네트워크/URL 문제. 결과·캐릭터 화면은 정상 표시되며 응답만 전송되지 않은 상태입니다.
