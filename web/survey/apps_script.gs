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
  'bti_code', 'character_name', 'result_title', 'taste_vector_json', 'taste_profile_summary',
  'alcohol_score', 'alcohol_preference', 'calculation_source',
  'is_correct', 'mismatch_axes', 'feedback_reason',
  'q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10', 'q11', 'q12',
  'q13', 'q14', 'q15', 'q16', 'q17', 'q18', 'q19', 'q20', 'q21', 'q22',
  'q23', 'q24', 'q25', 'q24_text', 'q25_text',
  'sweetness', 'body', 'carbonation', 'flavor', 'alcohol', 'acidity',
  'aroma_intensity', 'finish',
  'calculation_result_json'
];

function _sheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) sh = ss.insertSheet(SHEET_NAME);
  if (sh.getLastRow() === 0) {
    sh.appendRow(HEADERS);
  } else {
    sh.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
  }
  return sh;
}

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return _json({ status: 'error', message: 'empty request body' });
    }

    var data;
    try {
      data = JSON.parse(e.postData.contents);
    } catch (parseErr) {
      return _json({ status: 'error', message: 'invalid JSON: ' + String(parseErr) });
    }

    var a = data.answers || {};
    var tv = data.taste_vector || {};
    var fb = data.feedback || {};
    var mismatchAxes = data.mismatch_axes || fb.mismatch_axes || [];
    var isCorrect = data.is_correct;
    if (isCorrect === undefined) isCorrect = fb.is_correct;

    // q1~q25 (q24/q25 는 배열 → 콤마 결합)
    var qVals = [];
    for (var i = 1; i <= 25; i++) {
      var v = data['q' + i];
      if (v === undefined) v = a['q' + i];
      qVals.push(Array.isArray(v) ? v.join(',') : (v == null ? '' : v));
    }

    var row = [data.timestamp || new Date().toISOString()]
      .concat([
        data.bti_code || '',
        data.character_name || '',
        data.result_title || data.character_name || '',
        JSON.stringify(tv || {}),
        data.taste_profile_summary || '',
        data.alcohol_score,
        data.alcohol_preference || '',
        data.calculation_source || '',
        isCorrect,
        Array.isArray(mismatchAxes) ? mismatchAxes.join(',') : mismatchAxes,
        data.feedback_reason || fb.feedback_reason || ''
      ])
      .concat(qVals)
      .concat([
        data.q24_text || a.q24_text || '',
        data.q25_text || a.q25_text || '',
        tv.sweetness, tv.body, tv.carbonation, tv.flavor,
        tv.alcohol, tv.acidity, tv.aroma_intensity, tv.finish,
        JSON.stringify(data.calculation_result || {})
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
