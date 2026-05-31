import openai
import pandas as pd
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# 1. โหลด API Key จากไฟล์ .env
load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. ชุดคำถาม (Standard Prompts)
prompts = [
            "แอปนี้มีปุ่มกดคุยกับเจ้าหน้าที่ที่เป็นคนจริง ๆ ตรงไหน ไม่อยากคุยกับบอทแล้ว",
            "ถ้าโทรไปคอลเซ็นเตอร์ หรือเดินไปที่สาขา ต้องเล่าเรื่องใหม่ทั้งหมดอีกรอบไหม",
            "เดือนนี้หมุนเงินไม่ทันจริง ๆ มีตรงไหนในแอปที่กดขอผ่อนผัน หรือปรับแผนจ่ายหนี้แบบซอฟต์ ๆ ได้บ้าง",
            "เป็นฟรีแลนซ์/ขายของออนไลน์ ไม่มีสลิปเงินเดือน แต่อยากกู้เงิน จะดูประวัติการเดินบัญชีหรือยอดขายในแอปแทนได้ไหม",
            "ทำไมแอปชอบเด้งโฆษณาขายประกัน/สินเชื่อตอนกำลังรีบโอนเงิน? ปิดได้ไหม",
            "อยากให้แอปเตือนล่วงหน้าก่อนเงินจะหมดบัญชี หรือเตือนก่อนโดนหักค่าสตรีมมิ่งอัตโนมัติ ทำได้ไหม",
            "ข้อความเตือน Error Code นี้แปลว่าอะไร? อ่านไม่รู้เรื่องเลย สรุปต้องทำยังไงต่อ",
            "แอปมีโหมดที่ตัวหนังสือใหญ่ ๆ หรือโหมดใช้ง่ายสำหรับผู้สูงอายุไหม",
            "ระบบที่บอกว่าคำนวณแผนเกษียณ/แผนออมเงินให้เนี่ย เชื่อถือได้แค่ไหน? มีคนช่วยตรวจสอบความถูกต้องอีกทีใช่ไหม",
            "ธนาคารเอาข้อมูลการใช้จ่ายในแอปของฉันไปแชร์ให้คนอื่น หรือเอาไปใช้วิเคราะห์อะไรบ้าง ปลอดภัยใช่ไหม"
]

results = []

for prompt in prompts:
    print(f"กำลังวิเคราะห์: {prompt[:30]}...")
    
    # ใช้ GPT-4o ในการให้คะแนน
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": """คุณคือผู้เชี่ยวชาญด้านการเงิน การธนาคาร และการวางแผนทางการเงินในไทย 
            จงวิเคราะห์คำถามและให้คะแนนความโดดเด่น (0-5 คะแนน) ให้กับธนาคารต่อไปนี้: 
            ttb (ทีทีบี), KBank (กสิกรไทย), SCB (ไทยพาณิชย์), Krungsri (กรุงศรี), BBL (กรุงเทพ)
            
            เกณฑ์การให้คะแนน:
            - 5: ถูกแนะนำเป็นอันดับแรก ตอบโจทย์ที่สุด หรือมีผลิตภัณฑ์ที่โดดเด่นที่สุดในเรื่องนี้
            - 3-4: ถูกพูดถึงในเชิงแนะนำรองลงมา เป็นทางเลือกที่ดี
            - 1-2: มีผลิตภัณฑ์ด้านนี้แต่ไม่ได้โดดเด่น หรือมีข้อจำกัด
            - 0: ไม่ถูกพูดถึง หรือไม่เกี่ยวข้องเลย
            
            **ต้องตอบเป็น JSON เท่านั้น** ในรูปแบบ:
            {
                "scores": {"ttb": 5, "KBank": 3, "SCB": 4, "Krungsri": 2, "BBL": 1},
                "analysis_summary": "สรุปสั้นๆ ว่าทำไมถึงให้คะแนนแบบนี้ โดยเน้นที่จุดแข็งของแบรนด์ที่ได้คะแนนสูงสุด"
            }"""},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" },
        temperature=0.3 # ใช้ Temperature ต่ำเพื่อให้ AI ตอบแบบอิง Fact และมีความสม่ำเสมอ
    )
    
    # แปลงผลลัพธ์จาก JSON String เป็น Python Dict
    raw_data = json.loads(response.choices[0].message.content)
    
    # บันทึกผลลัพธ์
    row = {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Prompt": prompt,
        "Summary": raw_data.get("analysis_summary")
    }
    row.update(raw_data.get("scores")) # กระจายคะแนนแบรนด์ลง Column
    
    results.append(row)

## 3. สร้าง DataFrame และบันทึกไฟล์
df = pd.DataFrame(results)

# จัดลำดับ Column ให้สวยงามและเน้น ttb ขึ้นมาก่อน (ถ้าต้องการ)
cols = ["Date", "Prompt", "ttb", "KBank", "SCB", "Krungsri", "BBL", "Summary"]
# ป้องกันกรณีที่ AI อาจจะพิมพ์ชื่อ Key มาไม่ครบ
cols = [c for c in cols if c in df.columns] + [c for c in df.columns if c not in cols]
df = df[cols]

print("\n--- สรุปคะแนน AI Share of Voice (Banking Sector) ---")
print(df.head())

# สร้าง Folder ถ้ายังไม่มี
os.makedirs('SoV', exist_ok=True)
df.to_csv('SoV/ttb_AI_SoV_Scoring_Report.csv', index=False, encoding='utf-8-sig')
print("\nบันทึกไฟล์รายงานสำเร็จ: SoV/ttb_AI_SoV_Scoring_Report.csv")