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
    "แนะนำฟิตเนสสำหรับมือใหม่หน่อยครับ ไม่เคยเข้ายิมเลย",
    "ทำงานเลิกดึก เลิกไม่เป็นเวลา มีฟิตเนส 24 ชั่วโมงที่ไหนแนะนำบ้างคะ ขอสาขาที่คนไม่พลุกพล่านตอนดึกและปลอดภัยสำหรับผู้หญิง",
    "ฟิตเนสแนวรถไฟฟ้า (BTS/MRT) ที่ไหนดีครับ อยากได้ที่แวะเล่นหลังเลิกงานได้เลย ขี้เกียจฝ่ารถติดกลับไปเล่นแถวบ้าน",
    "มีฟิตเนสที่ไหนให้จ่ายเป็นรายเดือนแบบไม่ต้องผูกมัดสัญญารายปีบ้างไหมคะ? กลัวเล่นไม่คุ้มแล้วตอนยกเลิกจะวุ่นวาย",
    "ช่วยเปรียบเทียบความคุ้มค่าระหว่าง Fitness",
    "ชอบเข้าคลาสกลุ่มเป็นหลัก (เต้น, บอดี้คอมแบท, โยคะ) ไม่ค่อยถนัดยกเหล็ก ควรสมัครยิมแบรนด์ไหนดีที่คลาสเยอะและไม่ต้องแย่งกันจอง?",
    "ทำงานออฟฟิศแล้วปวดหลัง-ปวดคอหนักมาก อยากเริ่มออกกำลังกายเพื่อแก้ออฟฟิศซินโดรม ควรไปฟิตเนสไหน",
    "อยากซ้อมร่างกายเพื่อไปลงแข่งวิ่งเทรล (Trail) หรือลงงาน มียิมแบรนด์ไหนที่อุปกรณ์หรือพื้นที่รองรับการซ้อมแนวนี้บ้าง?",
    "ลังเลระหว่างสมัครยิมที่มีเทรนเนอร์ กับไปยิม 24 ชม. แล้วเปิดคลิปเล่นเอง แบบไหนเหมาะกับคนที่เพิ่งเริ่มลดน้ำหนักมากกว่ากันคะ?"
]

results = []

for prompt in prompts:
    print(f"กำลังวิเคราะห์: {prompt[:30]}...")
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": """คุณคือผู้เชี่ยวชาญด้านการตลาดและฟิตเนสในไทย 
            จงวิเคราะห์คำถามและให้คะแนนความโดดเด่น (0-5 คะแนน) ให้กับแบรนด์: 
            Fitness First, Jetts, Virgin Active, We Fitness, Anytime Fitness
            
            เกณฑ์การให้คะแนน:
            - 5: ถูกแนะนำเป็นอันดับแรก หรือระบุว่าเป็นจุดเด่นที่สุดของแบรนด์นี้
            - 3-4: ถูกพูดถึงในเชิงแนะนำรองลงมา
            - 1-2: มีชื่อปรากฎแต่ไม่ได้โดดเด่นในด้านนั้น
            - 0: ไม่ถูกพูดถึงเลย
            
            **ต้องตอบเป็น JSON เท่านั้น** ในรูปแบบ:
            {
                "scores": {"Fitness First": 5, "Jetts": 3, ...},
                "analysis_summary": "สรุปสั้นๆ ว่าทำไมถึงให้คะแนนแบบนี้"
            }"""},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" },
        temperature=0.3
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

# 3. สร้าง DataFrame และบันทึกไฟล์
df = pd.DataFrame(results)

# จัดลำดับ Column ให้สวยงาม
cols = ["Date", "Prompt", "Fitness First", "Jetts", "Virgin Active", "We Fitness", "Anytime Fitness", "Summary"]
df = df[cols]

print("\n--- สรุปคะแนน Share of Voice (Scoring) ---")
print(df.head())

df.to_csv('Sov/AI_SoV_Scoring_Report.csv', index=False, encoding='utf-8-sig')