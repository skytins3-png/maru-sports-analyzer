/**
 * MARU SPORTS ANALYZER Google Apps Script Hub
 * Web App으로 배포 후 GAS_WEBAPP_URL에 입력.
 *
 * 권장 Sheet 탭:
 * config
 * fixtures
 * team_static_cache
 * pre_match_cache
 * odds_cache
 * injury_cache
 * lineup_cache
 * recommendations
 * match_results
 * analysis_history
 * mobile_recommend
 * live_score
 * logs
 */

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    var type = body.type || "logs";
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    if (type === "mobile_recommend
 * live_score") {
      writeMobileRecommend(ss, body);
    } else {
      writeLog(ss, body);
    }

    return ContentService
      .createTextOutput(JSON.stringify({ok: true}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ok: false, error: String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function getOrCreateSheet(ss, name) {
  var sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  return sh;
}

function writeMobileRecommend(ss, body) {
  var sh = getOrCreateSheet(ss, "mobile_recommend
 * live_score");
  sh.clearContents();

  var headers = [
    "rank", "match_id", "league", "match_no", "title",
    "kickoff_kst", "main_pick", "sub_pick",
    "confidence", "risk", "summary",
    "auto_purchase", "auto_payment", "user_must_choose", "updated_at"
  ];

  sh.appendRow(headers);

  var rows = body.rows || [];
  rows.forEach(function(r, idx) {
    sh.appendRow([
      idx + 1,
      r.match_id || "",
      r.league || "",
      r.match_no || "",
      r.title || "",
      r.kickoff_kst || "",
      r.main_pick || "",
      r.sub_pick || "",
      r.confidence || "",
      r.risk || "",
      r.summary || "",
      r.auto_purchase || "NO",
      r.auto_payment || "NO",
      r.user_must_choose || "YES",
      body.created_at || new Date()
    ]);
  });
}

function writeLog(ss, body) {
  var sh = getOrCreateSheet(ss, "logs");
  sh.appendRow([new Date(), JSON.stringify(body)]);
}
