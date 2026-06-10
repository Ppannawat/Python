def check_rating(ovr_score):
    if ovr_score >= 90:
        return "World Class"
    elif ovr_score >= 80:
        return "Elite"
    else:
        return "Standard"

running = True

while running == True:
    
    name = input("กรุณาใส่ชื่อนักบอลที่คุณชอบ:")
    goal = int(input("ใส่จำนวนประตูที่ยิงได้:"))
    ovr = int(input("ใส่ค่าพลังนักบอล:"))
    
    rank = check_rating(ovr)

    player_dic = {
        "name": name,  
        "goal": goal, 
        "rank": rank   
    }

    if player_dic["goal"] >= 30:
        print(f"{player_dic['name']} (ระดับ: {player_dic['rank']}) รับโบนัสเพิ่ม 1,000,000 บาท")
    elif player_dic["goal"] >= 15:
        print(f"{player_dic['name']} (ระดับ: {player_dic['rank']}) รับโบนัสเพิ่ม 500,000 บาท")
    else:
        print(f"{player_dic['name']} (ระดับ: {player_dic['rank']}) ไม่ได้รับโบนัสในฤดูกาลนี้")
        
    choice = input("ต้องการคำนวณโบนัสต่อหรือไม่? (y/n):")
    if choice == "n":
        running = False
        print("ปิดระบบคำนวณ")