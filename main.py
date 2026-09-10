from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
import os

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from database import engine, get_db
import models
import schemas

# Ensure tables are created
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def read_index(cat: str = "", token: str = ""):
    # Read the Index.html and replace template variables for local testing
    if not os.path.exists("Index.html"):
        return HTMLResponse(content="Index.html not found", status_code=404)
        
    with open("Index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
        
    html_content = html_content.replace("<?= cat ?>", cat)
    html_content = html_content.replace("<?= token ?>", token)
    html_content = html_content.replace("<?= cat || 'TVOP' ?>", cat if cat else 'TVOP')
    html_content = html_content.replace("<?= cat || 'แมวตัวนี้' ?>", cat if cat else 'แมวตัวนี้')
    
    return HTMLResponse(content=html_content)

@app.get("/api/progress/{employeeId}")
def get_progress(employeeId: str, db: Session = Depends(get_db)):
    participant = db.query(models.Participant).filter(
        models.Participant.employee_id == employeeId
    ).first()
    
    if not participant:
        return {"count": 0, "completed": False}
        
    return {"count": participant.total_found, "completed": participant.is_completed}

@app.post("/api/scan")
def scan_cat(scan_data: schemas.ScanRequest, db: Session = Depends(get_db)):
    # 1. Query the Cat table using the token from the QR code
    cat = db.query(models.Cat).filter(models.Cat.token == scan_data.token).first()
    if not cat or not cat.is_active:
        return {"ok": False, "message": "QR นี้ไม่ใช่แมวที่เปิดใช้งาน (Invalid QR Code)"}
    
    cat_id_upper = cat.cat_id
    
    # 3. Check duplicate in ScanLog
    existing_scan = db.query(models.ScanLog).filter(
        models.ScanLog.employee_id == scan_data.employeeId,
        models.ScanLog.cat_id == cat_id_upper,
        models.ScanLog.status == 'FOUND'
    ).first()
    
    is_duplicate = existing_scan is not None
    
    # 4. Insert new ScanLog record
    new_scan_status = 'DUPLICATE' if is_duplicate else 'FOUND'
    new_scan = models.ScanLog(
        employee_id=scan_data.employeeId,
        name=scan_data.name,
        department=scan_data.department,
        cat_id=cat_id_upper,
        status=new_scan_status
    )
    db.add(new_scan)
    
    # Flush so the newly inserted log is considered in the count query
    db.flush()
    
    # 5. Update or insert Participant
    participant = db.query(models.Participant).filter(
        models.Participant.employee_id == scan_data.employeeId
    ).first()
    
    now = datetime.now(timezone.utc)
    
    if not participant:
        participant = models.Participant(
            employee_id=scan_data.employeeId,
            name=scan_data.name,
            department=scan_data.department,
            first_scan_at=now,
            last_scan_at=now
        )
        db.add(participant)
    else:
        participant.last_scan_at = now
        # Keep name and department updated in case of changes
        participant.name = scan_data.name
        participant.department = scan_data.department
        
    # Calculate distinct cats found
    total_found = db.query(func.count(func.distinct(models.ScanLog.cat_id))).filter(
        models.ScanLog.employee_id == scan_data.employeeId,
        models.ScanLog.status == 'FOUND'
    ).scalar() or 0
    
    participant.total_found = total_found
    participant.is_completed = total_found >= 10
    
    # 6. Commit the transaction
    db.commit()
    
    # 7. Return JSON response
    return {
        "ok": True,
        "duplicate": is_duplicate,
        "catId": cat.cat_id,
        "catName": cat.name,
        "count": total_found,
        "completed": participant.is_completed,
        "timestamp": now.isoformat()
    }

@app.get("/api/admin/data")
def get_admin_data(db: Session = Depends(get_db)):
    participants = db.query(models.Participant).order_by(models.Participant.total_found.desc()).all()
    scans = db.query(models.ScanLog).order_by(models.ScanLog.id.desc()).limit(100).all()
    cats = db.query(models.Cat).all()
    
    return {
        "participants": [
            {
                "employee_id": p.employee_id,
                "name": p.name,
                "department": p.department,
                "total_found": p.total_found,
                "is_completed": p.is_completed,
                "first_scan_at": p.first_scan_at.isoformat() if p.first_scan_at else None,
                "last_scan_at": p.last_scan_at.isoformat() if p.last_scan_at else None,
            }
            for p in participants
        ],
        "recent_scans": [
            {
                "id": s.id,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "employee_id": s.employee_id,
                "name": s.name,
                "department": s.department,
                "cat_id": s.cat_id,
                "status": s.status,
            }
            for s in scans
        ],
        "cats": [
            {
                "cat_id": c.cat_id,
                "name": c.name,
                "is_active": c.is_active,
                "token": c.token,
            }
            for c in cats
        ]
    }

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    html = """<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>HR Cat Hunt - Admin Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --accent: #ff8a00;
            --accent-green: #10b981;
            --accent-blue: #0ea5e9;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Prompt', sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 30px 20px;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 30px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 20px;
        }
        h1 { font-size: 28px; font-weight: 700; color: var(--text); }
        h1 span { color: var(--accent); }
        .refresh-btn {
            background: var(--accent);
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 15px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: opacity 0.2s;
        }
        .refresh-btn:hover { opacity: 0.9; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 35px;
        }
        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 4px;
            background: var(--accent);
        }
        .stat-card.green::before { background: var(--accent-green); }
        .stat-card.blue::before { background: var(--accent-blue); }
        .stat-label { color: var(--text-muted); font-size: 14px; margin-bottom: 8px; }
        .stat-val { font-size: 34px; font-weight: 700; color: var(--text); }
        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .table-wrap {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 18px;
            overflow-x: auto;
            margin-bottom: 40px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 14px;
        }
        th {
            background: #f1f5f9;
            color: var(--text-muted);
            font-weight: 600;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 12px;
        }
        td {
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            color: var(--text);
        }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: rgba(0, 0, 0, 0.02); }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-completed { background: rgba(16, 185, 129, 0.2); color: #059669; }
        .badge-progress { background: rgba(255, 138, 0, 0.2); color: #ea580c; }
        .badge-found { background: rgba(16, 185, 129, 0.2); color: #059669; }
        .badge-dup { background: rgba(148, 163, 184, 0.2); color: #475569; }
        .progress-mini {
            width: 100px;
            height: 8px;
            background: var(--border);
            border-radius: 999px;
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
            margin-right: 8px;
        }
        .progress-mini-bar {
            height: 100%;
            background: var(--accent);
            border-radius: 999px;
        }
        .progress-mini-bar.full { background: var(--accent-green); }
        .empty-row { text-align: center; color: var(--text-muted); padding: 30px; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🐱 HR Cat Hunt <span>Dashboard</span></h1>
                <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">สรุปข้อมูลผู้เข้าร่วมกิจกรรมและการสแกนทั้งหมด</p>
            </div>
            <div>
                <button class="refresh-btn" onclick="loadData()">🔄 รีเฟรชข้อมูล</button>
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">ผู้ลงทะเบียนทั้งหมด</div>
                <div class="stat-val" id="totalParticipants">0</div>
            </div>
            <div class="stat-card green">
                <div class="stat-label">หาครบ 10 ตัวแล้ว 🎉</div>
                <div class="stat-val" id="totalCompleted">0</div>
            </div>
            <div class="stat-card blue">
                <div class="stat-label">จำนวนการสแกนทั้งหมด</div>
                <div class="stat-val" id="totalScans">0</div>
            </div>
        </div>

        <div class="section-title">🏆 อันดับผู้เข้าร่วมกิจกรรม (Participants)</div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>รหัสพนักงาน</th>
                        <th>ชื่อ - นามสกุล</th>
                        <th>แผนก</th>
                        <th>ความคืบหน้า</th>
                        <th>สถานะ</th>
                        <th>สแกนตัวแรก</th>
                        <th>สแกนล่าสุด</th>
                    </tr>
                </thead>
                <tbody id="participantTable">
                    <tr><td colspan="7" class="empty-row">กำลังโหลดข้อมูล...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="section-title">📜 บันทึกการสแกนล่าสุด (Recent Scans)</div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>เวลา</th>
                        <th>รหัสพนักงาน</th>
                        <th>ชื่อ</th>
                        <th>แผนก</th>
                        <th>แมวที่สแกน</th>
                        <th>ผลลัพธ์</th>
                    </tr>
                </thead>
                <tbody id="scansTable">
                    <tr><td colspan="6" class="empty-row">กำลังโหลดข้อมูล...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                const res = await fetch('/api/admin/data');
                const data = await res.json();

                // Stats
                document.getElementById('totalParticipants').textContent = data.participants.length;
                document.getElementById('totalCompleted').textContent = data.participants.filter(p => p.is_completed).length;
                document.getElementById('totalScans').textContent = data.recent_scans.length;

                // Participants Table
                const pTbody = document.getElementById('participantTable');
                if (data.participants.length === 0) {
                    pTbody.innerHTML = '<tr><td colspan="7" class="empty-row">ยังไม่มีผู้เข้าร่วมสแกน</td></tr>';
                } else {
                    pTbody.innerHTML = data.participants.map(p => {
                        const pct = Math.min(100, (p.total_found / 10) * 100);
                        const isFull = p.is_completed;
                        const badge = isFull 
                            ? '<span class="badge badge-completed">🎉 สำเร็จ (10/10)</span>' 
                            : '<span class="badge badge-progress">กำลังตามหา</span>';
                        
                        const firstTime = p.first_scan_at ? new Date(p.first_scan_at).toLocaleString('th-TH') : '-';
                        const lastTime = p.last_scan_at ? new Date(p.last_scan_at).toLocaleString('th-TH') : '-';

                        return `<tr>
                            <td><b>${p.employee_id}</b></td>
                            <td>${p.name}</td>
                            <td>${p.department}</td>
                            <td>
                                <div class="progress-mini"><div class="progress-mini-bar ${isFull ? 'full' : ''}" style="width: ${pct}%"></div></div>
                                <b>${p.total_found}/10</b>
                            </td>
                            <td>${badge}</td>
                            <td>${firstTime}</td>
                            <td>${lastTime}</td>
                        </tr>`;
                    }).join('');
                }

                // Scans Table
                const sTbody = document.getElementById('scansTable');
                if (data.recent_scans.length === 0) {
                    sTbody.innerHTML = '<tr><td colspan="6" class="empty-row">ยังไม่มีประวัติการสแกน</td></tr>';
                } else {
                    sTbody.innerHTML = data.recent_scans.map(s => {
                        const time = s.timestamp ? new Date(s.timestamp).toLocaleString('th-TH') : '-';
                        const badge = s.status === 'FOUND' 
                            ? '<span class="badge badge-found">✅ เจอแมวใหม่</span>' 
                            : '<span class="badge badge-dup">😼 สแกนซ้ำ</span>';
                        return `<tr>
                            <td>${time}</td>
                            <td><b>${s.employee_id}</b></td>
                            <td>${s.name}</td>
                            <td>${s.department}</td>
                            <td><b>${s.cat_id}</b></td>
                            <td>${badge}</td>
                        </tr>`;
                    }).join('');
                }
            } catch (err) {
                console.error('Error loading admin data:', err);
            }
        }
        window.onload = loadData;
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)

