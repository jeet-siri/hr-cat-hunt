const SPREADSHEET_ID = '1-N7HiIiHE9qZxkckPQPydDbzGsvyUC2xbiVDhqTrqG8';
const TZ = 'Asia/Bangkok';

function doGet(e) {
  const t = HtmlService.createTemplateFromFile('Index');
  t.cat = String((e && e.parameter && e.parameter.cat) || '').toUpperCase();
  t.token = String((e && e.parameter && e.parameter.t) || '');
  return t.evaluate().setTitle('TVOP Orange Cat Hunt').addMetaTag('viewport','width=device-width, initial-scale=1');
}

function scan(payload) {
  payload = payload || {};
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const scans = ss.getSheetByName('Scans');
    const cats = ss.getSheetByName('Cats');
    const settings = getSettings_(ss);
    const now = new Date();
    const start = new Date(settings.START_AT.replace(' ','T') + '+07:00');
    const end = new Date(settings.END_AT.replace(' ','T') + '+07:00');
    if (now < start || now > end) return {ok:false, code:'CLOSED', message:'กิจกรรมยังไม่เปิด หรือสิ้นสุดแล้ว'};

    const employeeId = clean_(payload.employeeId);
    const name = clean_(payload.name);
    const department = clean_(payload.department);
    const catId = clean_(payload.cat).toUpperCase();
    const token = clean_(payload.token);
    if (!employeeId) return {ok:false, code:'EMPLOYEE_REQUIRED', message:'กรุณากรอกรหัสพนักงาน'};
    if (settings.REQUIRE_NAME === true && !name) return {ok:false, message:'กรุณากรอกชื่อ'};
    if (settings.REQUIRE_DEPARTMENT === true && !department) return {ok:false, message:'กรุณากรอกแผนก'};

    const catRows = cats.getRange(2,1,10,8).getValues();
    const cat = catRows.find(r => String(r[0]).toUpperCase() === catId);
    if (!cat || cat[4] !== true) return {ok:false, code:'CAT_INVALID', message:'QR นี้ไม่ใช่แมวที่เปิดใช้งาน'};
    const validToken = String(cat[3]) === token;
    if (!validToken) return {ok:false, code:'TOKEN_INVALID', message:'QR ไม่ถูกต้อง กรุณาสแกนจากป้ายแมวจริง'};

    const lastRow = scans.getLastRow();
    const existing = lastRow > 1 ? scans.getRange(2,1,lastRow-1,11).getValues() : [];
    const duplicate = existing.some(r => String(r[1]) === employeeId && String(r[4]).toUpperCase() === catId && String(r[8]) === 'FOUND');
    const sessionId = Utilities.getUuid();
    scans.appendRow([now, employeeId, name, department, catId, cat[1], true, duplicate, duplicate ? 'DUPLICATE' : 'FOUND', clean_(payload.userAgent), sessionId]);

    const found = new Set(existing.filter(r => String(r[1]) === employeeId && String(r[8]) === 'FOUND').map(r => String(r[4]).toUpperCase()));
    if (!duplicate) found.add(catId);
    const count = found.size;
    upsertParticipant_(ss, employeeId, name, department, now, count);
    updateCatCount_(cats, catId);
    return {ok:true, duplicate:duplicate, catId:catId, catName:cat[1], count:count, total:10, completed:count >= 10, timestamp:Utilities.formatDate(now,TZ,'dd/MM/yyyy HH:mm:ss')};
  } finally { lock.releaseLock(); }
}

function getProgress(employeeId) {
  employeeId = clean_(employeeId);
  if (!employeeId) return {count:0, cats:[]};
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sh = ss.getSheetByName('Scans');
  if (sh.getLastRow() < 2) return {count:0, cats:[]};
  const rows = sh.getRange(2,1,sh.getLastRow()-1,9).getValues();
  const found = [...new Set(rows.filter(r => String(r[1])===employeeId && String(r[8])==='FOUND').map(r=>String(r[4])) )];
  return {count:found.length, cats:found, total:10, completed:found.length>=10};
}

function getSettings_(ss) {
  const rows = ss.getSheetByName('Settings').getRange(2,1,20,2).getValues();
  const o = {};
  rows.forEach(r => { if (r[0] !== '') o[String(r[0])] = r[1]; });
  return o;
}
function clean_(v) { return String(v == null ? '' : v).trim().slice(0,200); }
function upsertParticipant_(ss, id, name, dept, now, count) {
  const sh=ss.getSheetByName('Participants'); const lr=sh.getLastRow();
  const ids=lr>1?sh.getRange(2,1,lr-1,1).getValues().flat().map(String):[];
  let idx=ids.indexOf(id), row=idx>=0?idx+2:lr+1;
  if(idx<0) sh.getRange(row,1,1,10).setValues([[id,name,dept,now,now,count,count>=10,count>=10?now:'',count>=10,'']]);
  else { const first=sh.getRange(row,4).getValue()||now; const completedAt=sh.getRange(row,8).getValue(); sh.getRange(row,1,1,9).setValues([[id,name,dept,first,now,count,count>=10,(count>=10&&!completedAt)?now:completedAt,count>=10]]); }
}
function updateCatCount_(sh, catId) {
  const rows=sh.getRange(2,1,10,1).getValues().flat().map(String); const i=rows.indexOf(catId); if(i<0)return;
  const ss=SpreadsheetApp.openById(SPREADSHEET_ID), scans=ss.getSheetByName('Scans');
  const vals=scans.getLastRow()>1?scans.getRange(2,2,scans.getLastRow()-1,8).getValues():[];
  const unique=new Set(vals.filter(r=>String(r[3])===catId && String(r[7])==='FOUND').map(r=>String(r[0])));
  sh.getRange(i+2,8).setValue(unique.size);
}
