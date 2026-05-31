import pandas as pd

# 1. โหลดข้อมูลจากไฟล์ CSV
file_path = 'Bank_SoV.csv'
df = pd.read_csv(file_path)

# 2. ฟังก์ชันสำหรับจัดหมวดหมู่ Topic (G1, G2, G3, Others)
def categorize_topic(title):
    title = str(title).lower()
    
    g1_keywords = ['s&p global', 'sustainability', 'esg', 'ความยั่งยืน']
    g2_keywords = ['wealth', 'advisory', 'mastery', 'พรีเมียม', 'สินทรัพย์สูง']
    g3_keywords = ['เงินบาท', 'วิกฤตพลังงาน', 'เศรษฐกิจไทย', 'ttb analytics', 'sme', 'ธุรกิจ']
    others_keywords = ['รถไฟฟ้า', 'ลดภาระ', 'รถมือสอง', 'กระเป๋า', 'fintalk', 'กิจกรรม', 'ดับร้อน', 'ฉุกเฉิน']
    
    if any(keyword in title for keyword in g1_keywords):
        return 'G1 (Corporate)'
    elif any(keyword in title for keyword in g2_keywords):
        return 'G2 (Young Pro)'
    elif any(keyword in title for keyword in g3_keywords):
        return 'G3 (SME)'
    else:
        return 'Others'

# 3. ฟังก์ชันสำหรับจัดระดับสื่อ Tier (อ้างอิงจาก PR Report มาตรฐาน 4 Tiers)
def categorize_tier(outlet):
    outlet = str(outlet).lower()
    
    # กลุ่มคำคีย์เวิร์ดที่ระบุว่าเป็น Social Media (มักจะถูกจัดเป็น Tier 3 หรือ 4 ตาม Report)
    social_prefix = ['fb', 'facebook', 'yt', 'youtube', 'x :', 'twitter', 'tiktok']
    is_social = any(prefix in outlet for prefix in social_prefix)

    # Tier 1: สื่อกระแสหลัก, นสพ., เว็บไซต์ใหญ่ และ LINE Today
    tier_1 = [
        'naew na', 'naewna', 'daily news', 'khao sod', 'khaosod', 
        'prachachat', 'bangkok today', 'pptvhd36', 'pptv thailand',
        'hooninside', 'line today'
    ]
    
    # Tier 2: สื่อธุรกิจและการเงินเฉพาะทาง
    tier_2 = ['banmuang', 'mitihoon', 'efinancethai', 'thansettakij', 'acnews']
    
    # Tier 3: เพจหรือกลุ่มโซเชียลขนาดกลาง
    tier_3 = ['sme startup', 'thai-cashless-society', "bank's scholarship students", 'thailand4']
    
    # Tier 4: เพจ FB ย่อย, นิตยสารเฉพาะกลุ่ม
    tier_4 = ['wealth plus', 'mba magazine', 'full max', 'trade max', 'เนตรทิพย์', 'high torque']

    # --- ลอจิกการคัดกรอง ---
    # 1. เช็กสื่อกลุ่มที่มักจะโดนลด Tier หากอยู่บน Social Media (เช่น FB: PPTV, FB: Thunhoon)
    if is_social:
        if any(t in outlet for t in ['pptv', 'thunhoon', 'thun hoon']):
            return 'Tier 4' # อิงจากไฟล์ Report: FB PPTV Wealth และ FB Thunhoon เป็น T4
        elif any(t in outlet for t in tier_3):
            return 'Tier 3'
        elif any(t in outlet for t in tier_4):
            return 'Tier 4'
        else:
            return 'Tier 3' # Default Social Media ให้เป็นสื่อรอง
            
    # 2. เช็กช่องทาง Mainstream (Web / Print)
    if any(t in outlet for t in tier_1) or 'thun' in outlet:
        # หากมีคำว่า thun (Thun Hoon / Thunhoon) และไม่ได้เป็น Social จะเป็น Tier 1
        return 'Tier 1'
    elif any(t in outlet for t in tier_2):
        return 'Tier 2'
    
    # 3. หากไม่ตรงเงื่อนไขใดเลย ให้จัดอยู่ใน Tier 4 หรือ Other
    return 'Tier 4'

# 4. Apply ฟังก์ชัน
df['Topic'] = df['article_title'].apply(categorize_topic)
df['Tier'] = df['outlet_name'].apply(categorize_tier)

# 5. Export ไฟล์เพื่อนำไปทำ Report หรือ Dashboard ต่อ
output_path = 'Bank_SoV_Automated_4Tiers.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')

print(f"อัปเดตข้อมูลและจัด Tier ตาม PR Report เสร็จสิ้น ไฟล์อยู่ที่: {output_path}")