/**
 * 주담 술BTI 설문 → 구글시트 수집 (Google Apps Script 웹앱)
 *
 * [배포법]
 *   1) 구글시트 > 상단 메뉴 '확장 프로그램' > 'Apps Script'
 *   2) 편집기에 이 파일(apps_script.gs) 내용 전체를 붙여넣기 > 저장(💾)
 *   3) 우측 상단 '배포' > '새 배포'
 *   4) 톱니(⚙) > 유형 선택 > '웹 앱'
 *   5) 실행 계정: '나(본인)' / 액세스 권한: '모든 사용자' 선택 > '배포'
 *   6) 표시되는 '웹 앱 URL'(https://script.google.com/macros/s/.../exec) 복사
 *      → index.html 의 SHEET_WEBHOOK_URL 에 붙여넣기
 *
 * [동작 확인]
 *   - 위 URL 을 브라우저로 그냥 열면(doGet) {"status":"ok"} 가 보이면 정상.
 *
 * [참고] 클라이언트는 mode:'no-cors' + Content-Type text/plain('단순요청')로 POST 하므로
 *        CORS 프리플라이트가 발생하지 않는다. 응답 본문은 opaque 라 클라이언트가 파싱하지 않는다.
 */

var SHEET_NAME = 'responses';

var HEADERS = [
  'timestamp',
  'q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10', 'q11', 'q12',
  'q13', 'q14', 'q15', 'q16', 'q17', 'q18', 'q19', 'q20', 'q21', 'q22',
  'q23', 'q24', 'q25', 'q24_text', 'q25_text',
  'sweetness', 'body', 'carbonation', 'flavor', 'alcohol', 'acidity',
  'aroma_intensity', 'finish',
  'bti4', 'is_match', 'wrong_axes', 'memo'
];

function _sheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) sh = ss.insertSheet(SHEET_NAME);
  if (sh.getLastRow() === 0) sh.appendRow(HEADERS);   // 비어있으면 헤더 먼저
  return sh;
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var a = data.answers || {};
    var tv = data.taste_vector || {};
    var fb = data.feedback || {};

    // q1~q25 (q24/q25 는 배열 → 콤마 결합)
    var qVals = [];
    for (var i = 1; i <= 25; i++) {
      var v = a['q' + i];
      qVals.push(Array.isArray(v) ? v.join(',') : (v == null ? '' : v));
    }

    // wrong_axes: [{axis, actual_direction}] → "sweetness:high; body:low"
    var wrong = (fb.wrong_axes || []).map(function (w) {
      return w.axis + ':' + (w.actual_direction || '');
    }).join('; ');

    var row = [data.timestamp || new Date().toISOString()]
      .concat(qVals)
      .concat([
        a.q24_text || '',
        a.q25_text || '',
        tv.sweetness, tv.body, tv.carbonation, tv.flavor,
        tv.alcohol, tv.acidity, tv.aroma_intensity, tv.finish,
        data.bti4 || '',
        fb.is_match,
        wrong,
        fb.memo || ''
      ]);

    _sheet().appendRow(row);
    return _json({ status: 'ok' });
  } catch (err) {
    return _json({ status: 'error', message: String(err) });
  }
}

function doGet(e) {
  return _json({ status: 'ok' });   // 배포 동작 확인용
}

function _json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
