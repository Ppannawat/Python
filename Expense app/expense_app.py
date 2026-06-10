from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from bson import ObjectId
import os

app = FastAPI()

# -----------------------------------------------------------------
# [DATABASE SETTINGS] ตั้งค่าการเชื่อมต่อฐานข้อมูล MongoDB
# -----------------------------------------------------------------
MONGO_URL = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)

db = client["expense_db"]
collection = db["transactions"]


class TransactionInput(BaseModel):
    type: str
    amount: float
    note: str
    month: str 

# -----------------------------------------------------------------
# [API Endpoints] ระบบประมวลผลหลังบ้าน (Backend)
# -----------------------------------------------------------------

@app.get("/summary")
async def get_monthly_summary(month: str = None):
    if not month:
        month = datetime.now().strftime("%Y-%m")
        
    current_year = month.split("-")[0]
        
    monthly_cursor = collection.find({"month_by": month})
    monthly_transactions = await monthly_cursor.to_list(length=1000)
    
    yearly_cursor = collection.find({"month_by": {"$regex": f"^{current_year}"}})
    yearly_transactions = await yearly_cursor.to_list(length=1000)
    
    total_income = 0.0
    total_expense = 0.0
    history_list = []
    
    for t in monthly_transactions:
        t_id = str(t["_id"]) 
        if t["type"] == "income":
            total_income += float(t["amount"])
        elif t["type"] == "expense":
            total_expense += float(t["amount"])
            
        history_list.append({
            "id": t_id,
            "type": t["type"],
            "amount": float(t["amount"]),
            "note": t["note"],
            "month_by": t["month_by"]
        })
    
    yearly_income = 0.0
    yearly_expense = 0.0
    for yt in yearly_transactions:
        if yt["type"] == "income":
            yearly_income += float(yt["amount"])
        elif yt["type"] == "expense":
            yearly_expense += float(yt["amount"])
            
    balance = total_income - total_expense
    yearly_balance = yearly_income - yearly_expense
    
    if balance == 0:
        status_text = ""
    elif balance > 0:
        status_text = "💵 การเงินมั่งคั่ง"
    else:
        status_text = "🚨 เงินออมติดลบแล้ว!"
    
    return {
        "current_month": month,
        "current_year": current_year,
        "total_income": total_income,
        "total_expense": total_expense,
        "remaining_balance": balance,
        "status": status_text,
        "yearly_summary": {
            "income": yearly_income,
            "expense": yearly_expense,
            "balance": yearly_balance
        },
        "history": history_list
    }

@app.post("/add-transaction")
async def add_new_transaction(data: TransactionInput):
    transaction_type = data.type.lower()
    if transaction_type not in ["income", "expense"]:
        return {"error": "ประเภทไม่ถูกต้อง"}
    if data.amount <= 0:
        return {"error": "จำนวนเงินต้องมากกว่า 0"}

    new_document = {
        "type": transaction_type,
        "amount": float(data.amount),
        "note": data.note,
        "month_by": data.month
    }
    
    await collection.insert_one(new_document)
    return {"message": "success"}

@app.delete("/delete-transaction/{transaction_id}")
async def delete_transaction(transaction_id: str):
    try:
        result = await collection.delete_one({"_id": ObjectId(transaction_id)})
        if result.deleted_count > 0:
            return {"message": "success"}
    except:
        pass
    return {"error": "ไม่พบรายการ"}


# -----------------------------------------------------------------
# [FRONTEND] ส่วนแสดงหน้าเว็บ
# -----------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def get_web_page():
    html_content = """
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Expense Tracker</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600&display=swap" rel="stylesheet">
        <style>body { font-family: 'Kanit', sans-serif; }</style>
    </head>
    <body class="bg-slate-50 min-h-screen pb-12">
        <div class="max-w-5xl mx-auto px-4 pt-8">
            <div class="flex flex-col md:flex-row justify-between items-center mb-8 bg-white p-6 border border-slate-200 rounded-2xl shadow-sm gap-4">
                <div class="text-center md:text-left">
                    <h1 class="text-2xl font-bold text-slate-800">📊 ระบบบัญชีรายรับ - รายจ่าย</h1>
                </div>
                <div class="flex items-center gap-2 bg-blue-50/60 p-2.5 rounded-2xl border border-blue-100 shadow-inner">
                    <span class="text-sm font-bold text-blue-800 ml-1">📅 ตัวเลือกเวลา:</span>
                    <select id="filter-year" onchange="loadData()" class="border border-slate-200 rounded-xl p-1.5 bg-white font-bold text-slate-700 shadow-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"></select>
                    <select id="filter-month" onchange="loadData()" class="border border-slate-200 rounded-xl p-1.5 bg-white font-bold text-slate-700 shadow-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option value="01">มกราคม</option><option value="02">กุมภาพันธ์</option><option value="03">มีนาคม</option><option value="04">เมษายน</option>
                        <option value="05">พฤษภาคม</option><option value="06">มิถุนายน</option><option value="07">กรกฎาคม</option><option value="08">สิงหาคม</option>
                        <option value="09">กันยายน</option><option value="10">ตุลาคม</option><option value="11">พฤศจิกายน</option><option value="12">ธันวาคม</option>
                    </select>
                </div>
            </div>
            
            <div class="mb-8">
                <h3 class="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3" id="title-monthly">📊 สรุปยอดรายเดือน</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                    <div class="bg-emerald-50 border border-emerald-100 rounded-2xl p-5 shadow-sm">
                        <p class="text-xs text-emerald-600 font-semibold mb-1">รายรับเดือนนี้</p>
                        <p class="text-2xl font-bold text-emerald-700" id="ui-income">0.00 ฿</p>
                    </div>
                    <div class="bg-rose-50 border border-rose-100 rounded-2xl p-5 shadow-sm">
                        <p class="text-xs text-rose-600 font-semibold mb-1">รายจ่ายเดือนนี้</p>
                        <p class="text-2xl font-bold text-rose-700" id="ui-expense">0.00 ฿</p>
                    </div>
                    <div class="bg-blue-50 border border-blue-100 rounded-2xl p-5 shadow-sm">
                        <p class="text-xs text-blue-600 font-semibold mb-1">เงินคงเหลือเดือนนี้</p>
                        <p class="text-2xl font-bold text-blue-700 mb-1" id="ui-balance">0.00 ฿</p>
                        <span class="text-[10px] px-2 py-0.5 rounded-full font-medium hidden" id="ui-status"></span>
                    </div>
                </div>
                <h3 class="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3" id="title-yearly">🏢 สรุปยอดสะสมรวมทั้งปี</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div class="bg-slate-100 border border-slate-200 rounded-xl p-4">
                        <p class="text-xs text-slate-500 font-medium">รายรับสะสมทั้งปี</p>
                        <p class="text-xl font-bold text-slate-700" id="year-income">0.00 ฿</p>
                    </div>
                    <div class="bg-slate-100 border border-slate-200 rounded-xl p-4">
                        <p class="text-xs text-slate-500 font-medium">รายจ่ายสะสมทั้งปี</p>
                        <p class="text-xl font-bold text-slate-700" id="year-expense">0.00 ฿</p>
                    </div>
                    <div class="bg-slate-100 border border-slate-200 rounded-xl p-4">
                        <p class="text-xs text-slate-500 font-medium">เงินออมสุทธิทั้งปี</p>
                        <p class="text-xl font-bold" id="year-balance">0.00 ฿</p>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-5 gap-8">
                <div class="md:col-span-2 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm h-fit">
                    <h2 class="text-lg font-bold text-slate-800 mb-4">➕ เพิ่มรายการใหม่</h2>
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-slate-600 mb-1">ประเภท</label>
                            <select id="form-type" class="w-full border border-slate-200 rounded-xl p-2.5 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500">
                                <option value="income">➕ รายรับ (Income)</option>
                                <option value="expense">➖ รายจ่าย (Expense)</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-600 mb-1">จำนวนเงิน (บาท)</label>
                            <input type="number" step="0.01" id="form-amount" placeholder="0.00" class="w-full border border-slate-200 rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-600 mb-1">บันทึกช่วยจำ</label>
                            <input type="text" id="form-note" placeholder="เช่น ค่าอาหาร, ค่าน้ำ" class="w-full border border-slate-200 rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <button onclick="addTransaction()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium p-3 rounded-xl transition duration-200 shadow-sm">
                            💾 บันทึกค่าใช้จ่าย
                        </button>
                    </div>
                </div>
                <div class="md:col-span-3 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                    <h2 class="text-lg font-bold text-slate-800 mb-4" id="ui-table-title">🕒 รายการประจำเดือน</h2>
                    <div class="overflow-hidden rounded-xl border border-slate-100">
                        <table class="w-full text-left border-collapse">
                            <thead>
                                <tr class="bg-slate-50 text-slate-500 text-xs uppercase font-semibold border-b border-slate-100">
                                    <th class="p-3">รายการ</th><th class="p-3 text-right">จำนวนเงิน</th><th class="p-3 text-center">จัดการ</th>
                                </tr>
                            </thead>
                            <tbody id="ui-history" class="divide-y divide-slate-100 text-sm text-slate-700"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function fmt(num) {
                return parseFloat(num).toLocaleString('th-TH', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            }

            function populateYearOptions() {
                const yearSelect = document.getElementById('filter-year');
                const currentYearBE = new Date().getFullYear() + 543;
                for (let i = currentYearBE - 5; i <= currentYearBE + 5; i++) {
                    const opt = document.createElement('option');
                    opt.value = i;
                    opt.text = "" + i;
                    yearSelect.appendChild(opt);
                }
            }

            function initDatePicker() {
                populateYearOptions();
                const currentYearBE = new Date().getFullYear() + 543;
                const savedYear = localStorage.getItem('selected_year') || currentYearBE.toString();
                const savedMonth = localStorage.getItem('selected_month') || (new Date().getMonth() + 1).toString().padStart(2, '0');
                document.getElementById('filter-year').value = savedYear;
                document.getElementById('filter-month').value = savedMonth;
            }

            async function loadData() {
                const yearBE = document.getElementById('filter-year').value;
                const month = document.getElementById('filter-month').value;
                const yearAD = parseInt(yearBE) - 543;
                const combinedDate = `${yearAD}-${month}`;
                
                localStorage.setItem('selected_year', yearBE);
                localStorage.setItem('selected_month', month);
                
                const response = await fetch(`/summary?month=${combinedDate}`);
                const data = await response.json();
                
                const monthText = document.getElementById('filter-month').options[document.getElementById('filter-month').selectedIndex].text;
                document.getElementById('title-monthly').innerText = `📊 สรุปยอดรายเดือน (${monthText} พ.ศ. ${yearBE})`;
                document.getElementById('title-yearly').innerText = `🏢 สรุปยอดสะสมรวมทั้งปี พ.ศ. ${yearBE}`;
                document.getElementById('ui-table-title').innerText = `🕒 รายการประจำเดือน ${monthText} พ.ศ. ${yearBE}`;
                
                document.getElementById('ui-income').innerText = fmt(data.total_income) + ' ฿';
                document.getElementById('ui-expense').innerText = fmt(data.total_expense) + ' ฿';
                document.getElementById('ui-balance').innerText = fmt(data.remaining_balance) + ' ฿';
                
                const statusEl = document.getElementById('ui-status');
                statusEl.innerText = data.status;
                statusEl.className = data.remaining_balance === 0 ? "text-[10px] px-2 py-0.5 rounded-full font-medium hidden" : (data.remaining_balance > 0 ? "text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-700 inline-block" : "text-[10px] px-2 py-0.5 rounded-full font-medium bg-rose-100 text-rose-700 inline-block");

                document.getElementById('year-income').innerText = fmt(data.yearly_summary.income) + ' ฿';
                document.getElementById('year-expense').innerText = fmt(data.yearly_summary.expense) + ' ฿';
                const yBalanceEl = document.getElementById('year-balance');
                yBalanceEl.innerText = fmt(data.yearly_summary.balance) + ' ฿';
                yBalanceEl.className = data.yearly_summary.balance >= 0 ? "text-xl font-bold text-emerald-600" : "text-xl font-bold text-rose-600";

                const historyBody = document.getElementById('ui-history');
                historyBody.innerHTML = '';
                if (data.history.length === 0) {
                    historyBody.innerHTML = `<tr><td colspan="3" class="p-4 text-center text-slate-400">ยังไม่มีการบันทึกข้อมูล</td></tr>`;
                    return;
                }
                data.history.forEach(item => {
                    const isIncome = item.type === 'income';
                    const tr = document.createElement('tr');
                    tr.className = "hover:bg-slate-50 transition";
                    tr.innerHTML = `<td class="p-3"><span class="font-medium block text-slate-800">${item.note}</span><span class="text-xs ${isIncome ? 'text-emerald-600':'text-rose-600'}">${isIncome ? 'รายรับ':'รายจ่าย'}</span></td><td class="p-3 text-right font-bold ${isIncome ? 'text-emerald-600':'text-rose-600'}">${isIncome ? '+':'-'}${fmt(item.amount)} ฿</td><td class="p-3 text-center"><button onclick="deleteTransaction('${item.id}')" class="text-rose-500 hover:text-rose-700 font-medium hover:underline text-xs">ลบ</button></td>`;
                    historyBody.appendChild(tr);
                });
            }

            async function addTransaction() {
                const type = document.getElementById('form-type').value;
                const amount = parseFloat(document.getElementById('form-amount').value);
                const note = document.getElementById('form-note').value;
                const yearBE = document.getElementById('filter-year').value;
                const month = document.getElementById('filter-month').value;
                const yearAD = parseInt(yearBE) - 543;
                const combinedDate = `${yearAD}-${month}`;

                if (isNaN(amount) || amount <= 0 || !note) { alert('กรุณากรอกข้อมูลให้ครบถ้วน'); return; }

                await fetch('/add-transaction', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type, amount, note, month: combinedDate })
                });
                document.getElementById('form-amount').value = '';
                document.getElementById('form-note').value = '';
                loadData();
            }

            async function deleteTransaction(id) {
                if(confirm('คุณแน่ใจใช่ไหมที่จะลบรายการนี้?')) {
                    await fetch(`/delete-transaction/${id}`, { method: 'DELETE' });
                    loadData();
                }
            }

            initDatePicker();
            loadData();
        </script>
    </body>
    </html>
    """
    return html_content