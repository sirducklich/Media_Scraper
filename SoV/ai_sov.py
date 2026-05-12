import openai
import pandas as pd
from datetime import datetime

# ตั้งค่า API Key ของคุณ
client = openai.OpenAI(api_key="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")

# 1. กำหนดชุดคำถาม (Standard Prompts)
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

# 2. กำหนด Keyword ที่ต้องการ Track
my_brand = "Fitness First"
competitors = {
    "Fitness First": ["fitness first", "ฟิตเนส เฟิรส์ท", "เฟิร์ส"],
    "Jetts": ["jetts", "เจ็ทส์"],
    "Virgin Active": ["virgin active", "เวอร์จิ้น"],
    "We Fitness": ["we fitness", "วี ฟิตเนส"],
    "Anytime": ["anytime fitness", "เอนนี่ไทม์"]
}

results = []

for prompt in prompts:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    answer = response.choices[0].message.content
    
    # 3. ให้คะแนน SoV (Entity Recognition)
    # ถ้ามีชื่อแบรนด์ปรากฏในคำตอบ ให้ค่าเป็น 1 (True) ถ้าไม่มีให้ 0 (False)
    row = {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Prompt": prompt,
        my_brand: 1 if my_brand.lower() in answer.lower() else 0
    }
    
    for comp in competitors:
        row[comp] = 1 if comp.lower() in answer.lower() else 0
        
    results.append(row)

df = pd.DataFrame(results)
print(df)

df.to_csv('AI_SoV_Report.csv', index=False)