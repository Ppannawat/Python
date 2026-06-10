from fastapi import FastAPI

# [1] สร้างระบบฟังก์ชันคำนวณเรตติ้ง (เหมือนที่คุณเขียนเป๊ะๆ)
def check_rating(ovr_score):
    if ovr_score >= 90:
        return "World Class"
    elif ovr_score >= 80:
        return "Elite"
    else:
        return "Standard"

# [2] ประกาศตัวแอปพลิเคชัน FastAPI ของเรา
app = FastAPI()

# [3] สร้างเส้นทาง (API Endpoint) บนเว็บ
# แปลว่า: ถ้ามีใครส่งข้อมูล ชื่อ, ประตู, ค่าพลัง มาที่ลิงก์ /bonus ให้ทำงานที่ฟังก์ชันนี้
@app.get("/bonus")
def calculate_football_bonus(name: str, club: str, goal: int, ovr: int):
    
    # ดึงฟังก์ชันเช็คเรตติ้งมาใช้งาน
    rank = check_rating(ovr)
    
    # คิดตรรกะเรื่องโบนัสเหมือนเดิม
    if goal < 0:
        bonus = "ข้อมูลจำนวนประตูไม่ถูกต้อง"
    # ถ้าข้อมูลถูกต้อง ค่อยเอามาคิดตรรกะเรื่องโบนัสตามปกติ
    elif goal >= 30:
        bonus = "รับโบนัสเพิ่ม 1,000,000 บาท"
    elif goal >= 15:
        bonus = "รับโบนัสเพิ่ม 500,000 บาท"
    else:
        bonus = "ไม่ได้รับโบนัสในฤดูกาลนี้"
        
    # [4] ส่งข้อมูลกลับไปหาหน้าบ้านในรูปแบบ Dictionary (ซึ่งบนเว็บจะเรียกว่า JSON)
    return {
        "player_name": name,
        "club": club,
        "goals": goal,
        "rating": rank,
        "bonus_status": bonus
    }