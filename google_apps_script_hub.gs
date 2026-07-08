function doGet(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureSheets_(ss);
  return ContentService
    .createTextOutput(JSON.stringify({ok:true, app:'MARU SPORTS HUB', message:'hub alive', time:new Date()}))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureSheets_(ss);
  var raw = e && e.postData && e.postData.contents ? e.postData.contents : '{}';
  var data = JSON.parse(raw);

  writeSheet_(ss, 'hub_payload_log', [{
    received_at: new Date(),
    app: data.app || '',
    version: data.version || '',
    type: data.type || '',
    created_at: data.created_at || '',
    mobile_count: (data.mobile_recommendations || []).length,
    analysis_count: (data.analysis_scores || []).length,
    raw_json: raw.substring(0, 45000)
  }]);

  writeSheet_(ss, 'mobile_recommendations', data.mobile_recommendations || []);
  writeSheet_(ss, 'analysis_scores', data.analysis_scores || []);
  writeSheet_(ss, 'hub_send_logs_remote', data.hub_send_logs || []);
  writeSheet_(ss, 'diagnosis', [data.diagnosis || {}]);
  writeSheet_(ss, 'counts', [data.counts || {}]);

  return ContentService
    .createTextOutput(JSON.stringify({ok:true, received_at: new Date(), mobile_count:(data.mobile_recommendations||[]).length, analysis_count:(data.analysis_scores||[]).length}))
    .setMimeType(ContentService.MimeType.JSON);
}

function ensureSheets_(ss) {
  ['hub_payload_log','mobile_recommendations','analysis_scores','hub_send_logs_remote','diagnosis','counts'].forEach(function(name){
    if (!ss.getSheetByName(name)) ss.insertSheet(name);
  });
}

function writeSheet_(ss, name, rows) {
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  if (!rows || rows.length === 0) return;
  var keys = [];
  rows.forEach(function(r){ Object.keys(flatten_(r)).forEach(function(k){ if(keys.indexOf(k) < 0) keys.push(k); }); });
  if (sh.getLastRow() === 0) sh.appendRow(keys);
  var values = rows.map(function(r){ var f = flatten_(r); return keys.map(function(k){ return f[k] === undefined ? '' : f[k]; }); });
  sh.getRange(sh.getLastRow()+1, 1, values.length, keys.length).setValues(values);
}

function flatten_(obj, prefix, out) {
  out = out || {}; prefix = prefix || '';
  if (obj === null || obj === undefined) return out;
  Object.keys(obj).forEach(function(k){
    var v = obj[k]; var key = prefix ? prefix + '.' + k : k;
    if (typeof v === 'object' && !Array.isArray(v) && v !== null) flatten_(v, key, out);
    else out[key] = Array.isArray(v) ? JSON.stringify(v) : v;
  });
  return out;
}
