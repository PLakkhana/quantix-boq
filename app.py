import streamlit as st
import pandas as pd
import io
import json

st.set_page_config(page_title="Quantix - Structural BOQ", page_icon="🏗️", layout="wide")

# --- โค้ด CSS บังคับฟอนต์ภาษาไทย (แบบครอบคลุมและมี Font Fallback) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&display=swap');
        
        /* บังคับทุก Element ในหน้าเว็บและตารางให้ใช้ Sarabun และฟอนต์ไทยมาตรฐาน */
        html, body, [class*="css"], .stApp, table, th, td, div, span, input, textarea, select {
            font-family: 'Sarabun', 'Tahoma', 'Cordia New', sans-serif !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ Quantix: ระบบคำนวณ BOQ โครงสร้างอาคาร")
st.write("ระบบถอดปริมาณ ประเมินราคางานโครงสร้าง")

# --- ฟังก์ชันจัดการ Session State สำหรับปุ่มรีเซ็ตค่าทั้งหมด ---
if "reset_trigger" not in st.session_state:
    st.session_state.reset_trigger = 0

def reset_all_data():
    st.session_state.reset_trigger += 1

# --- Sidebar: ปุ่มรีเซ็ตตัวเลขทั้งหมด ---
st.sidebar.header("⚙️ จัดการข้อมูล")
if st.sidebar.button("🔄 รีเซ็ตตัวเลขและตารางทั้งหมด", type="primary"):
    reset_all_data()
    st.sidebar.success("เคลียร์ตัวเลขและรีเซ็ตข้อมูลทั้งหมดเป็น 0 เรียบร้อยแล้ว!")

# --- Sidebar: ลิงก์อ้างอิงราคากลางและค่าแรง ---
st.sidebar.divider()
st.sidebar.subheader("🔗 แหล่งอ้างอิงราคากลาง")
st.sidebar.markdown("[📊 ราคาวัสดุก่อสร้าง (พาณิชย์)](https://index.tpso.go.th/construction-material-prices/prices-building-materials)")
st.sidebar.markdown("[👷‍♂️ ราคากลางค่าแรงงาน (โยธาไทย)](https://www.yotathai.com/passadu/w480)")
st.sidebar.divider()

# --- ตัวเลือกขนาดเหล็กสำหรับ Dropdown ---
rebar_choices = ["RB6", "RB9", "DB12", "DB16", "DB20", "DB25"]
floor_choices = ["ชั้น 1 (Ground Floor)", "ชั้น 2 (Second Floor)", "ชั้น 3 (Third Floor)", "ชั้นดาดฟ้า (Roof)"]

# --- Sidebar: ตั้งค่าราคาต่อหน่วยกลาง และ Waste Factor ---
st.sidebar.header("⚙️ ตั้งค่าระบบและเปอร์เซ็นต์เผื่อเศษวัสดุ (Waste Factor)")
with st.sidebar.expander("🛠️ ตั้งค่า Waste Factor (%)", expanded=True):
    waste_concrete = st.number_input("เผื่อคอนกรีต (%):", min_value=0.0, max_value=20.0, value=0.0, step=1.0, key=f"wc_{st.session_state.reset_trigger}")
    waste_rebar = st.number_input("เผื่อเหล็กเสริม (%):", min_value=0.0, max_value=30.0, value=0.0, step=1.0, key=f"wr_{st.session_state.reset_trigger}")
    waste_formwork = st.number_input("เผื่อไม้แบบ (%):", min_value=0.0, max_value=20.0, value=0.0, step=1.0, key=f"wf_{st.session_state.reset_trigger}")

st.sidebar.header("⚙️ ตั้งค่าราคาต่อหน่วยกลาง")
st.sidebar.subheader("1. งานเสาเข็มและงานดิน (บาท)")
pile_mat_price = st.sidebar.number_input("ค่าวัสดุเสาเข็ม (ต้น):", min_value=0.0, value=0.0, step=50.0, key=f"pm_{st.session_state.reset_trigger}")
pile_lab_price = st.sidebar.number_input("ค่าแรงตอก/ตัดหัวเสาเข็ม (ต้น):", min_value=0.0, value=0.0, step=10.0, key=f"pl_{st.session_state.reset_trigger}")
earth_price = st.sidebar.number_input("ค่าแรงขุดดิน (ลบ.ม.):", min_value=0.0, value=0.0, step=10.0, key=f"ep_{st.session_state.reset_trigger}")
sand_mat_price = st.sidebar.number_input("ค่าวัสดุทรายหยาบ (ลบ.ม.):", min_value=0.0, value=0.0, step=10.0, key=f"sm_{st.session_state.reset_trigger}")
sand_lab_price = st.sidebar.number_input("ค่าแรงทรายหยาบ (ลบ.ม.):", min_value=0.0, value=0.0, step=10.0, key=f"sl_{st.session_state.reset_trigger}")
lean_mat_price = st.sidebar.number_input("ค่าวัสดุคอนกรีตหยาบ (ลบ.ม.):", min_value=0.0, value=0.0, step=50.0, key=f"lm_{st.session_state.reset_trigger}")
lean_lab_price = st.sidebar.number_input("ค่าแรงคอนกรีตหยาบ (ลบ.ม.):", min_value=0.0, value=0.0, step=20.0, key=f"ll_{st.session_state.reset_trigger}")
conc_mat_price = st.sidebar.number_input("ค่าวัสดุคอนกรีตโครงสร้าง 240 ksc (ลบ.ม.):", min_value=0.0, value=0.0, step=50.0, key=f"cm_{st.session_state.reset_trigger}")
conc_lab_price = st.sidebar.number_input("ค่าแรงเทคอนกรีตโครงสร้าง (ลบ.ม.):", min_value=0.0, value=0.0, step=20.0, key=f"cl_{st.session_state.reset_trigger}")

st.sidebar.subheader("2. งานไม้แบบ (บาท)")
form_mat_price = st.sidebar.number_input("ค่าวัสดุไม้แบบ (ตร.ม.):", min_value=0.0, value=0.0, step=20.0, key=f"formm_{st.session_state.reset_trigger}")
form_lab_price = st.sidebar.number_input("ค่าแรงไม้แบบ (ตร.ม.):", min_value=0.0, value=0.0, step=20.0, key=f"forml_{st.session_state.reset_trigger}")
nail_mat_price = st.sidebar.number_input("ค่าวัสดุตะปู (กก.):", min_value=0.0, value=0.0, step=1.0, key=f"nm_{st.session_state.reset_trigger}")
wire_mat_price = st.sidebar.number_input("ค่าวัสดุรวดผูกเหล็ก (กก.):", min_value=0.0, value=0.0, step=1.0, key=f"wm_{st.session_state.reset_trigger}")

st.sidebar.subheader("3. งานพื้น คสล. หล่อในที่ และกันซึม")
slab_conc_lab_price = st.sidebar.number_input("ค่าแรงเทพื้น คสล. (ลบ.ม.):", min_value=0.0, value=0.0, step=20.0, key=f"scl_{st.session_state.reset_trigger}")
slab_form_lab_price = st.sidebar.number_input("ค่าแรงไม้แบบพื้น คสล. (ตร.ม.):", min_value=0.0, value=0.0, step=10.0, key=f"sfl_{st.session_state.reset_trigger}")
waterproof_mat_price = st.sidebar.number_input("ค่าวัสดุกันซึมฐานราก/คานคอดิน (ตร.ม.):", min_value=0.0, value=0.0, step=10.0, key=f"wpm_{st.session_state.reset_trigger}")

st.sidebar.subheader("4. งานพื้นสำเร็จรูป SP และค้ำยัน (บาท)")
sp_slab_price = st.sidebar.number_input("ค่าวัสดุแผ่นพื้น SP + Topping (ตร.ม.):", min_value=0.0, value=0.0, step=20.0, key=f"spp_{st.session_state.reset_trigger}")
shoring_mat_price = st.sidebar.number_input("ค่าวัสดุไม้ค้ำยันพื้น SP (ตร.ม.):", min_value=0.0, value=0.0, step=10.0, key=f"shm_{st.session_state.reset_trigger}")
shoring_lab_price = st.sidebar.number_input("ค่าแรงติดตั้งค้ำยัน (ตร.ม.):", min_value=0.0, value=0.0, step=10.0, key=f"shl_{st.session_state.reset_trigger}")

st.sidebar.subheader("5. งานเหล็กเสริม (ค่าวัสดุ / ค่าแรงต่อ กก.)")
rebar_prices = {
    "RB6": {"mat": st.sidebar.number_input("RB6 ค่าวัสดุ (บาท/กก.):", value=0.0, key=f"rb6_m_{st.session_state.reset_trigger}"), "lab": st.sidebar.number_input("RB6 ค่าแรง (บาท/กก.):", value=0.0, key=f"rb6_l_{st.session_state.reset_trigger}")},
    "RB9": {"mat": st.sidebar.number_input("RB9 ค่าวัสดุ (บาท/กก.):", value=0.0, key=f"rb9_m_{st.session_state.reset_trigger}"), "lab": st.sidebar.number_input("RB9 ค่าแรง (บาท/กก.):", value=0.0, key=f"rb9_l_{st.session_state.reset_trigger}")},
    "DB12": {"mat": st.sidebar.number_input("DB12 ค่าวัสดุ (บาท/กก.):", value=0.0, key=f"db12_m_{st.session_state.reset_trigger}"), "lab": st.sidebar.number_input("DB12 ค่าแรง (บาท/กก.):", value=0.0, key=f"db12_l_{st.session_state.reset_trigger}")},
    "DB16": {"mat": st.sidebar.number_input("DB16 ค่าวัสดุ (บาท/กก.):", value=0.0, key=f"db16_m_{st.session_state.reset_trigger}"), "lab": st.sidebar.number_input("DB16 ค่าแรง (บาท/กก.):", value=0.0, key=f"db16_l_{st.session_state.reset_trigger}")},
    "DB20": {"mat": st.sidebar.number_input("DB20 ค่าวัสดุ (บาท/กก.):", value=0.0, key=f"db20_m_{st.session_state.reset_trigger}"), "lab": st.sidebar.number_input("DB20 ค่าแรง (บาท/กก.):", value=0.0, key=f"db20_l_{st.session_state.reset_trigger}")},
    "DB25": {"mat": st.sidebar.number_input("DB25 ค่าวัสดุ (บาท/กก.):", value=0.0, key=f"db25_m_{st.session_state.reset_trigger}"), "lab": st.sidebar.number_input("DB25 ค่าแรง (บาท/กก.):", value=0.0, key=f"db25_l_{st.session_state.reset_trigger}")},
}

# --- สร้าง Tabs จัดระเบียบหน้าจอหลัก ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 1. กำหนดข้อมูลโครงการ (Schedules)", 
    "📊 2. สรุป Master BOQ", 
    "🏢 3. แยกตามชั้น", 
    "📈 4. วิเคราะห์ต้นทุน"
])

with tab1:
    st.subheader("📋 ตารางกำหนดข้อมูลองค์อาคารและงานโครงสร้าง (รองรับการระบุชั้น)")
    
    with st.expander("📌 1. งานเสาเข็ม (Pile Schedule)", expanded=True):
        default_piles = pd.DataFrame([
            {"ขนาดเสาเข็ม": "", "จำนวน (ต้น)": 0.0},
        ])
        edited_piles = st.data_editor(default_piles, num_rows="dynamic", key=f"pile_table_pro_{st.session_state.reset_trigger}", use_container_width=True)

    with st.expander("🛠️ 2. งานดินขุด, งานใต้ดิน และระบบกันซึม", expanded=False):
        default_earthworks = pd.DataFrame([
            {"โซน/หลุม": "", "กว้าง (ม.)": 0.0, "ยาว (ม.)": 0.0, "ลึก (ม.)": 0.0, "จำนวนฐานราก": 0, "หนาทรายหยาบ (ม.)": 0.0, "หนาคอนกรีตหยาบ (ม.)": 0.0, "ต้องการกันซึม": False},
        ])
        edited_earthworks = st.data_editor(default_earthworks, num_rows="dynamic", key=f"earthwork_table_pro_{st.session_state.reset_trigger}", use_container_width=True)

    with st.expander("🏗️ 3. งานฐานรากและเสาตอม่อ (Footing & Pier Schedule)", expanded=False):
        default_footings = pd.DataFrame([
            {"ฐานราก": "", "กว้าง B (ม.)": 0.0, "ยาว L (ม.)": 0.0, "หนา t (ม.)": 0.0, "ความสูงตอม่อ (ม.)": 0.0, "จำนวน (ฐาน)": 0, "พื้นที่ไม้แบบ (ตร.ม.)": 0.0, "เหล็กตะแกรง": "RB6", "ระยะเรียง @ (ม.)": 0.0, "จำนวนเดือย": 0, "เหล็กเดือย": "RB6", "เหล็กปลอก": "RB6", "ระยะเรียงปลอก (ม.)": 0.0},
        ])
        edited_footings = st.data_editor(
            default_footings, num_rows="dynamic", key=f"footing_table_pro_{st.session_state.reset_trigger}", use_container_width=True,
            column_config={
                "เหล็กตะแกรง": st.column_config.SelectboxColumn(options=rebar_choices),
                "เหล็กเดือย": st.column_config.SelectboxColumn(options=rebar_choices),
                "เหล็กปลอก": st.column_config.SelectboxColumn(options=rebar_choices),
            }
        )

    with st.expander("🧱 4. งานคานคอดินและคานชั้นบน (Beam Schedule)", expanded=False):
        default_beams = pd.DataFrame([
            {"ชั้น": "ชั้น 1 (Ground Floor)", "คาน": "", "ความกว้าง b (ม.)": 0.0, "ความลึก h (ม.)": 0.0, "ความยาวรวม (ม.)": 0.0, "พื้นที่ไม้แบบ (ตร.ม.)": 0.0, "เหล็กบน": "RB6", "จำนวนเส้นบน": 0, "เหล็กล่าง": "RB6", "จำนวนเส้นล่าง": 0, "เหล็กปลอก": "RB6", "ระยะเรียงปลอก s (ม.)": 0.0},
        ])
        edited_beams = st.data_editor(
            default_beams, num_rows="dynamic", key=f"beam_table_pro_{st.session_state.reset_trigger}", use_container_width=True,
            column_config={
                "ชั้น": st.column_config.SelectboxColumn(options=floor_choices),
                "เหล็กบน": st.column_config.SelectboxColumn(options=rebar_choices),
                "เหล็กล่าง": st.column_config.SelectboxColumn(options=rebar_choices),
                "เหล็กปลอก": st.column_config.SelectboxColumn(options=rebar_choices),
            }
        )

    with st.expander("🏛️ 5. งานเสาชั้นบน (Column Schedule)", expanded=False):
        default_columns = pd.DataFrame([
            {"ชั้น": "ชั้น 1 (Ground Floor)", "เสา": "", "ความกว้าง b (ม.)": 0.0, "ความลึก h (ม.)": 0.0, "ความสูง H (ม.)": 0.0, "จำนวนต้น": 0, "พื้นที่ไม้แบบ (ตร.ม.)": 0.0, "เหล็กยืน": "RB6", "จำนวนเส้นยืน": 0, "เหล็กปลอก": "RB6", "ระยะเรียงปลอก s (ม.)": 0.0},
        ])
        edited_columns = st.data_editor(
            default_columns, num_rows="dynamic", key=f"column_table_pro_{st.session_state.reset_trigger}", use_container_width=True,
            column_config={
                "ชั้น": st.column_config.SelectboxColumn(options=floor_choices),
                "เหล็กยืน": st.column_config.SelectboxColumn(options=rebar_choices),
                "เหล็กปลอก": st.column_config.SelectboxColumn(options=rebar_choices),
            }
        )

    with st.expander("⬛ 6. งานพื้น คสล. หล่อในที่ (Slab Schedule)", expanded=False):
        default_slabs = pd.DataFrame([
            {"ชั้น": "ชั้น 1 (Ground Floor)", "พื้น": "", "พื้นที่ใช้งาน (ตร.ม.)": 0.0, "ความหนาพื้น t (ม.)": 0.0, "พื้นที่ไม้แบบรวม (ตร.ม.)": 0.0, "เหล็กเสริมพื้น": "RB6"},
        ])
        edited_slabs = st.data_editor(
            default_slabs, num_rows="dynamic", key=f"slab_table_pro_{st.session_state.reset_trigger}", use_container_width=True,
            column_config={
                "ชั้น": st.column_config.SelectboxColumn(options=floor_choices),
                "เหล็กเสริมพื้น": st.column_config.SelectboxColumn(options=rebar_choices),
            }
        )

    with st.expander("🔲 7. งานพื้นสำเร็จรูป SP/PS (Prestressed Slab Schedule)", expanded=False):
        default_sp_slabs = pd.DataFrame([
            {"ชั้น": "ชั้น 2 (Second Floor)", "พื้น SP": "", "พื้นที่ใช้งาน (ตร.ม.)": 0.0, "ความหนา Topping (ม.)": 0.0, "เหล็กกันร้าว": "RB6", "พื้นที่ค้ำยัน (ตร.ม.)": 0.0},
        ])
        edited_sp_slabs = st.data_editor(
            default_sp_slabs, num_rows="dynamic", key=f"sp_slab_table_pro_{st.session_state.reset_trigger}", use_container_width=True,
            column_config={
                "ชั้น": st.column_config.SelectboxColumn(options=floor_choices),
                "เหล็กกันร้าว": st.column_config.SelectboxColumn(options=rebar_choices),
            }
        )

# --- ส่วนคำนวณทางวิศวกรรม ---
rebar_unit_weights = {
    "RB6": 0.222, "RB9": 0.499,
    "DB12": 0.888, "DB16": 1.578, "DB20": 2.466, "DB25": 3.853
}
hook = 0.10

floor_costs = {f: {"mat": 0.0, "lab": 0.0, "total": 0.0} for f in floor_choices}

sum_concrete = 0.0
sum_formwork = 0.0
sum_earthwork = 0.0
sum_sand = 0.0
sum_lean = 0.0
sum_waterproof = 0.0
sum_slab_conc = 0.0
sum_slab_form = 0.0
sum_sp_area = 0.0
sum_shoring_area = 0.0
sum_piles_qty = 0.0
sum_rebar_by_size = {k: 0.0 for k in rebar_unit_weights.keys()}

def add_floor_cost(floor_name, mat_c, lab_c):
    if floor_name not in floor_costs:
        floor_costs[floor_name] = {"mat": 0.0, "lab": 0.0, "total": 0.0}
    floor_costs[floor_name]["mat"] += mat_c
    floor_costs[floor_name]["lab"] += lab_c
    floor_costs[floor_name]["total"] += (mat_c + lab_c)

if not edited_piles.empty:
    for idx, row in edited_piles.iterrows():
        try:
            if pd.isna(row.get("จำนวน (ต้น)")): continue
            qty = float(row["จำนวน (ต้น)"])
            sum_piles_qty += qty
            add_floor_cost("ชั้น 1 (Ground Floor)", qty * pile_mat_price, qty * pile_lab_price)
        except: continue

if not edited_earthworks.empty:
    for idx, row in edited_earthworks.iterrows():
        try:
            if pd.isna(row.get("กว้าง (ม.)")) or pd.isna(row.get("ยาว (ม.)")) or pd.isna(row.get("ลึก (ม.)")) or pd.isna(row.get("จำนวนฐานราก")): continue
            ew_w, ew_l, ew_d, e_qty = float(row["กว้าง (ม.)"]), float(row["ยาว (ม.)"]), float(row["ลึก (ม.)"]), int(row["จำนวนฐานราก"])
            sand_t = float(row.get("หนาทรายหยาบ (ม.)", 0.05)) if pd.notna(row.get("หนาทรายหยาบ (ม.)")) else 0.05
            lean_t = float(row.get("หนาคอนกรีตหยาบ (ม.)", 0.05)) if pd.notna(row.get("หนาคอนกรีตหยาบ (ม.)")) else 0.05
            has_wp = bool(row.get("ต้องการกันซึม", False))
            
            earth_vol = ew_w * ew_l * ew_d * e_qty
            sand_vol = (ew_w * ew_l * sand_t * e_qty) * (1.0 + waste_concrete/100.0)
            lean_vol = (ew_w * ew_l * lean_t * e_qty) * (1.0 + waste_concrete/100.0)
            wp_area = (ew_w * ew_l * e_qty) if has_wp else 0.0
            
            sum_earthwork += earth_vol
            sum_sand += sand_vol
            sum_lean += lean_vol
            sum_waterproof += wp_area
            
            add_floor_cost("ชั้น 1 (Ground Floor)", 
                           (sand_vol * sand_mat_price) + (lean_vol * lean_mat_price) + (wp_area * waterproof_mat_price), 
                           (earth_vol * earth_price) + (sand_vol * sand_lab_price) + (lean_vol * lean_lab_price))
        except: continue

if not edited_footings.empty:
    for idx, row in edited_footings.iterrows():
        try:
            if pd.isna(row.get("กว้าง B (ม.)")) or pd.isna(row.get("ยาว L (ม.)")) or pd.isna(row.get("หนา t (ม.)")) or pd.isna(row.get("จำนวน (ฐาน)")): continue
            b, l, t, qty = float(row["กว้าง B (ม.)"]), float(row["ยาว L (ม.)"]), float(row["หนา t (ม.)"]), int(row["จำนวน (ฐาน)"])
            pier_h = float(row.get("ความสูงตอม่อ (ม.)", 1.00)) if pd.notna(row.get("ความสูงตอม่อ (ม.)")) else 1.00
            
            conc = (b * l * t * qty) * (1.0 + waste_concrete/100.0)
            form = (float(row["พื้นที่ไม้แบบ (ตร.ม.)"]) if pd.notna(row.get("พื้นที่ไม้แบบ (ตร.ม.)")) else (2 * (b + l) * t * qty) + (4 * 0.20 * pier_h * qty)) * (1.0 + waste_formwork/100.0)
            
            sum_concrete += conc
            sum_formwork += form
            
            mat_size = str(row.get("เหล็กตะแกรง", "DB12"))
            sp = float(row.get("ระยะเรียง @ (ม.)", 0.20)) if pd.notna(row.get("ระยะเรียง @ (ม.)")) else 0.20
            cov = 0.075
            n_b = int((l - 2 * cov) / sp) + 1 if (l - 2 * cov) > 0 else 1
            len_b = (b - 2 * cov) + (2 * hook)
            n_l = int((b - 2 * cov) / sp) + 1 if (b - 2 * cov) > 0 else 1
            len_l = (l - 2 * cov) + (2 * hook)
            mat_len = ((n_b * len_b) + (n_l * len_l)) * qty
            mat_kg = (mat_len * rebar_unit_weights.get(mat_size, 0.888)) * (1.0 + waste_rebar/100.0)

            dowel_size = str(row.get("เหล็กเดือย", "DB16"))
            dowel_qty = int(row.get("จำนวนเดือย", 4)) if pd.notna(row.get("จำนวนเดือย")) else 4
            dowel_kg = (dowel_qty * 1.20 * qty * rebar_unit_weights.get(dowel_size, 1.578)) * (1.0 + waste_rebar/100.0)

            tie_size = str(row.get("เหล็กปลอก", "RB6"))
            tie_sp = float(row.get("ระยะเรียงปลอก (ม.)", 0.15)) if pd.notna(row.get("ระยะเรียงปลอก (ม.)")) else 0.15
            num_ties = int(pier_h / tie_sp) + 1 if tie_sp > 0 else 4
            tie_kg = (num_ties * 0.80 * qty * rebar_unit_weights.get(tie_size, 0.222)) * (1.0 + waste_rebar/100.0)

            sum_rebar_by_size[mat_size] = sum_rebar_by_size.get(mat_size, 0.0) + mat_kg
            sum_rebar_by_size[dowel_size] = sum_rebar_by_size.get(dowel_size, 0.0) + dowel_kg
            sum_rebar_by_size[tie_size] = sum_rebar_by_size.get(tie_size, 0.0) + tie_kg
            
            footing_mat_cost = (conc * conc_mat_price) + (form * form_mat_price) + (mat_kg * rebar_prices[mat_size]["mat"]) + (dowel_kg * rebar_prices[dowel_size]["mat"]) + (tie_kg * rebar_prices[tie_size]["mat"])
            footing_lab_cost = (conc * conc_lab_price) + (form * form_lab_price) + (mat_kg * rebar_prices[mat_size]["lab"]) + (dowel_kg * rebar_prices[dowel_size]["lab"]) + (tie_kg * rebar_prices[tie_size]["lab"])
            add_floor_cost("ชั้น 1 (Ground Floor)", footing_mat_cost, footing_lab_cost)
        except: continue

if not edited_beams.empty:
    for idx, row in edited_beams.iterrows():
        try:
            if pd.isna(row.get("ความกว้าง b (ม.)")) or pd.isna(row.get("ความลึก h (ม.)")) or pd.isna(row.get("ความยาวรวม (ม.)")): continue
            b_w, b_h, b_len = float(row["ความกว้าง b (ม.)"]), float(row["ความลึก h (ม.)"]), float(row["ความยาวรวม (ม.)"])
            flr = row.get("ชั้น", "ชั้น 1 (Ground Floor)")
            
            b_conc = (b_w * b_h * b_len) * (1.0 + waste_concrete/100.0)
            b_form = (float(row["พื้นที่ไม้แบบ (ตร.ม.)"]) if pd.notna(row.get("พื้นที่ไม้แบบ (ตร.ม.)")) else (2 * b_h * b_len)) * (1.0 + waste_formwork/100.0)
            
            sum_concrete += b_conc
            sum_formwork += b_form
            
            top_size = str(row.get("เหล็กบน", "DB16"))
            top_n = int(row.get("จำนวนเส้นบน", 2)) if pd.notna(row.get("จำนวนเส้นบน")) else 2
            top_kg = (b_len * top_n * rebar_unit_weights.get(top_size, 1.578)) * (1.0 + waste_rebar/100.0)
            
            bot_size = str(row.get("เหล็กล่าง", "DB16"))
            bot_n = int(row.get("จำนวนเส้นล่าง", 2)) if pd.notna(row.get("จำนวนเส้นล่าง")) else 2
            bot_kg = (b_len * bot_n * rebar_unit_weights.get(bot_size, 1.578)) * (1.0 + waste_rebar/100.0)
            
            stir_size = str(row.get("เหล็กปลอก", "RB6"))
            stir_sp = float(row.get("ระยะเรียงปลอก s (ม.)", 0.20)) if pd.notna(row.get("ระยะเรียงปลอก s (ม.)")) else 0.20
            num_stirs = int(b_len / stir_sp) + 1 if stir_sp > 0 else 1
            stir_perimeter = (2 * (b_w - 0.08 + b_h - 0.08)) + 0.10
            stir_kg = (num_stirs * stir_perimeter * rebar_unit_weights.get(stir_size, 0.222)) * (1.0 + waste_rebar/100.0)

            sum_rebar_by_size[top_size] = sum_rebar_by_size.get(top_size, 0.0) + top_kg
            sum_rebar_by_size[bot_size] = sum_rebar_by_size.get(bot_size, 0.0) + bot_kg
            sum_rebar_by_size[stir_size] = sum_rebar_by_size.get(stir_size, 0.0) + stir_kg
            
            beam_mat_cost = (b_conc * conc_mat_price) + (b_form * form_mat_price) + (top_kg * rebar_prices[top_size]["mat"]) + (bot_kg * rebar_prices[bot_size]["mat"]) + (stir_kg * rebar_prices[stir_size]["mat"])
            beam_lab_cost = (b_conc * conc_lab_price) + (b_form * form_lab_price) + (top_kg * rebar_prices[top_size]["lab"]) + (bot_kg * rebar_prices[bot_size]["lab"]) + (stir_kg * rebar_prices[stir_size]["lab"])
            add_floor_cost(flr, beam_mat_cost, beam_lab_cost)
        except: continue

if not edited_columns.empty:
    for idx, row in edited_columns.iterrows():
        try:
            if pd.isna(row.get("ความกว้าง b (ม.)")) or pd.isna(row.get("ความลึก h (ม.)")) or pd.isna(row.get("ความสูง H (ม.)")) or pd.isna(row.get("จำนวนต้น")): continue
            c_w, c_h, c_H, c_qty = float(row["ความกว้าง b (ม.)"]), float(row["ความลึก h (ม.)"]), float(row["ความสูง H (ม.)"]), int(row["จำนวนต้น"])
            flr = row.get("ชั้น", "ชั้น 1 (Ground Floor)")
            
            c_conc = (c_w * c_h * c_H * c_qty) * (1.0 + waste_concrete/100.0)
            c_form = (float(row["พื้นที่ไม้แบบ (ตร.ม.)"]) if pd.notna(row.get("พื้นที่ไม้แบบ (ตร.ม.)")) else 2 * (c_w + c_h) * c_H * c_qty) * (1.0 + waste_formwork/100.0)
            
            sum_concrete += c_conc
            sum_formwork += c_form
            
            main_size = str(row.get("เหล็กยืน", "DB12"))
            main_n = int(row.get("จำนวนเส้นยืน", 4)) if pd.notna(row.get("จำนวนเส้นยืน")) else 4
            main_kg = (c_H * main_n * c_qty * rebar_unit_weights.get(main_size, 0.888)) * (1.0 + waste_rebar/100.0)
            
            col_stir_size = str(row.get("เหล็กปลอก", "RB6"))
            col_stir_sp = float(row.get("ระยะเรียงปลอก s (ม.)", 0.15)) if pd.notna(row.get("ระยะเรียงปลอก s (ม.)")) else 0.15
            num_col_stirs = int(c_H / col_stir_sp) + 1 if col_stir_sp > 0 else 1
            col_stir_perim = (2 * (c_w - 0.08 + c_h - 0.08)) + 0.10
            col_stir_kg = (num_col_stirs * col_stir_perim * c_qty * rebar_unit_weights.get(col_stir_size, 0.222)) * (1.0 + waste_rebar/100.0)

            sum_rebar_by_size[main_size] = sum_rebar_by_size.get(main_size, 0.0) + main_kg
            sum_rebar_by_size[col_stir_size] = sum_rebar_by_size.get(col_stir_size, 0.0) + col_stir_kg
            
            col_mat_cost = (c_conc * conc_mat_price) + (c_form * form_mat_price) + (main_kg * rebar_prices[main_size]["mat"]) + (col_stir_kg * rebar_prices[col_stir_size]["mat"])
            col_lab_cost = (c_conc * conc_lab_price) + (c_form * form_lab_price) + (main_kg * rebar_prices[main_size]["lab"]) + (col_stir_kg * rebar_prices[col_stir_size]["lab"])
            add_floor_cost(flr, col_mat_cost, col_lab_cost)
        except: continue

if not edited_slabs.empty:
    for idx, row in edited_slabs.iterrows():
        try:
            if pd.isna(row.get("พื้นที่ใช้งาน (ตร.ม.)")) or pd.isna(row.get("ความหนาพื้น t (ม.)")): continue
            s_area, s_thick = float(row["พื้นที่ใช้งาน (ตร.ม.)"]), float(row["ความหนาพื้น t (ม.)"])
            flr = row.get("ชั้น", "ชั้น 1 (Ground Floor)")
            slab_rebar_size = str(row.get("เหล็กเสริมพื้น", "RB6"))
            
            s_conc = (s_area * s_thick) * (1.0 + waste_concrete/100.0)
            slab_form_area = (float(row["พื้นที่ไม้แบบรวม (ตร.ม.)"]) if pd.notna(row.get("พื้นที่ไม้แบบรวม (ตร.ม.)")) else s_area) * (1.0 + waste_formwork/100.0)
            slab_rebar_kg = (s_area * 3.5) * (1.0 + waste_rebar/100.0)
            
            sum_slab_conc += s_conc
            sum_slab_form += slab_form_area
            sum_rebar_by_size[slab_rebar_size] = sum_rebar_by_size.get(slab_rebar_size, 0.0) + slab_rebar_kg
            
            slab_mat_cost = (s_conc * conc_mat_price) + (slab_form_area * form_mat_price) + (slab_rebar_kg * rebar_prices[slab_rebar_size]["mat"])
            slab_lab_cost = (s_conc * slab_conc_lab_price) + (slab_form_area * slab_form_lab_price) + (slab_rebar_kg * rebar_prices[slab_rebar_size]["lab"])
            add_floor_cost(flr, slab_mat_cost, slab_lab_cost)
        except: continue

if not edited_sp_slabs.empty:
    for idx, row in edited_sp_slabs.iterrows():
        try:
            if pd.isna(row.get("พื้นที่ใช้งาน (ตร.ม.)")) or pd.isna(row.get("ความหนา Topping (ม.)")): continue
            sp_area = float(row["พื้นที่ใช้งาน (ตร.ม.)"])
            flr = row.get("ชั้น", "ชั้น 2 (Second Floor)")
            sp_thick = float(row.get("ความหนา Topping (ม.)", 0.05))
            anti_crack_size = str(row.get("เหล็กกันร้าว", "RB6"))
            shoring_area = float(row.get("พื้นที่ค้ำยัน (ตร.ม.)", sp_area))
            
            sum_sp_area += sp_area
            sum_shoring_area += shoring_area
            
            sp_conc = (sp_area * sp_thick) * (1.0 + waste_concrete/100.0)
            sum_concrete += sp_conc
            
            anti_crack_kg = (sp_area * 2.2) * (1.0 + waste_rebar/100.0)
            sum_rebar_by_size[anti_crack_size] = sum_rebar_by_size.get(anti_crack_size, 0.0) + anti_crack_kg
            
            sp_mat_cost = (sp_area * sp_slab_price) + (sp_conc * conc_mat_price) + (anti_crack_kg * rebar_prices[anti_crack_size]["mat"]) + (shoring_area * shoring_mat_price)
            sp_lab_cost = (sp_conc * conc_lab_price) + (anti_crack_kg * rebar_prices[anti_crack_size]["lab"]) + (shoring_area * shoring_lab_price)
            add_floor_cost(flr, sp_mat_cost, sp_lab_cost)
        except: continue

# --- สร้าง Master BOQ Rows ---
boq_rows = []
item_no = 1

if sum_piles_qty > 0:
    pile_m = sum_piles_qty * pile_mat_price
    pile_l = sum_piles_qty * pile_lab_price
    boq_rows.append([str(item_no), "เสาเข็ม I-0.22x0.22x15.00 ม.", f"{sum_piles_qty:.2f}", "ต้น", f"{pile_mat_price:,.2f}", f"{pile_m:,.2f}", f"{pile_lab_price:,.2f}", f"{pile_l:,.2f}", f"{pile_m + pile_l:,.2f}"])
    item_no += 1

earth_lab = sum_earthwork * earth_price
if sum_earthwork > 0:
    boq_rows.append([str(item_no), "งานขุดดินหลุมฐานราก", f"{sum_earthwork:.2f}", "ลบ.ม.", "0.00", "0.00", f"{earth_price:,.2f}", f"{earth_lab:,.2f}", f"{earth_lab:,.2f}"])
    item_no += 1

if sum_waterproof > 0:
    wp_m = sum_waterproof * waterproof_mat_price
    boq_rows.append([str(item_no), "งานกันซึมฐานราก/คานคอดิน", f"{sum_waterproof:.2f}", "ตร.ม.", f"{waterproof_mat_price:,.2f}", f"{wp_m:,.2f}", "0.00", "0.00", f"{wp_m:,.2f}"])
    item_no += 1

sand_m = sum_sand * sand_mat_price
sand_l = sum_sand * sand_lab_price
boq_rows.append([str(item_no), f"ทรายหยาบ (รวมเผื่อ {waste_concrete}%)", f"{sum_sand:.3f}", "ลบ.ม.", f"{sand_mat_price:,.2f}", f"{sand_m:,.2f}", f"{sand_lab_price:,.2f}", f"{sand_l:,.2f}", f"{sand_m + sand_l:,.2f}"])
item_no += 1

lean_m = sum_lean * lean_mat_price
lean_l = sum_lean * lean_lab_price
boq_rows.append([str(item_no), f"คอนกรีตหยาบ (รวมเผื่อ {waste_concrete}%)", f"{sum_lean:.3f}", "ลบ.ม.", f"{lean_mat_price:,.2f}", f"{lean_m:,.2f}", f"{lean_lab_price:,.2f}", f"{lean_l:,.2f}", f"{lean_m + lean_l:,.2f}"])
item_no += 1

c_mat = sum_concrete * conc_mat_price
c_lab = sum_concrete * conc_lab_price
boq_rows.append([str(item_no), f"คอนกรีตโครงสร้าง 240 ksc. (รวมเผื่อ {waste_concrete}%)", f"{sum_concrete:.3f}", "ลบ.ม.", f"{conc_mat_price:,.2f}", f"{c_mat:,.2f}", f"{conc_lab_price:,.2f}", f"{c_lab:,.2f}", f"{c_mat + c_lab:,.2f}"])
item_no += 1

slab_conc_mat = sum_slab_conc * conc_mat_price
slab_conc_lab = sum_slab_conc * slab_conc_lab_price
if sum_slab_conc > 0:
    boq_rows.append([str(item_no), f"คอนกรีตพื้น คสล. หล่อในที่ (รวมเผื่อ {waste_concrete}%)", f"{sum_slab_conc:.3f}", "ลบ.ม.", f"{conc_mat_price:,.2f}", f"{slab_conc_mat:,.2f}", f"{slab_conc_lab_price:,.2f}", f"{slab_conc_lab:,.2f}", f"{slab_conc_mat + slab_conc_lab:,.2f}"])
    item_no += 1

f_mat = sum_formwork * form_mat_price
f_lab = sum_formwork * form_lab_price
boq_rows.append([str(item_no), f"ไม้แบบ (ฐานราก/คาน/เสา) (รวมเผื่อ {waste_formwork}%)", f"{sum_formwork:.2f}", "ตร.ม.", f"{form_mat_price:,.2f}", f"{f_mat:,.2f}", f"{form_lab_price:,.2f}", f"{f_lab:,.2f}", f"{f_mat + f_lab:,.2f}"])
item_no += 1

slab_form_mat = sum_slab_form * form_mat_price
slab_form_lab = sum_slab_form * slab_form_lab_price
if sum_slab_form > 0:
    boq_rows.append([str(item_no), f"ไม้แบบพื้น คสล. หล่อในที่ (รวมเผื่อ {waste_formwork}%)", f"{sum_slab_form:.2f}", "ตร.ม.", f"{form_mat_price:,.2f}", f"{slab_form_mat:,.2f}", f"{slab_form_lab_price:,.2f}", f"{slab_form_lab:,.2f}", f"{slab_form_mat + slab_form_lab:,.2f}"])
    item_no += 1

total_r_mat = 0.0
total_r_lab = 0.0
total_rebar_weight = sum(sum_rebar_by_size.values())

for r_size, r_weight in sum_rebar_by_size.items():
    if r_weight > 0:
        rm_price = rebar_prices[r_size]["mat"]
        rl_price = rebar_prices[r_size]["lab"]
        rm = r_weight * rm_price
        rl = r_weight * rl_price
        total_r_mat += rm
        total_r_lab += rl
        boq_rows.append([str(item_no), f"เหล็กเสริม {r_size} มม. (รวมเผื่อ {waste_rebar}%)", f"{r_weight:.2f}", "กก.", f"{rm_price:,.2f}", f"{rm:,.2f}", f"{rl_price:,.2f}", f"{rl:,.2f}", f"{rm + rl:,.2f}"])
        item_no += 1

total_form_area = sum_formwork + sum_slab_form
nail_qty = total_form_area * 0.20
nail_total_cost = nail_qty * nail_mat_price
boq_rows.append([str(item_no), "ตะปู", f"{nail_qty:.2f}", "กก.", f"{nail_mat_price:,.2f}", f"{nail_total_cost:,.2f}", "0.00", "0.00", f"{nail_total_cost:,.2f}"])
item_no += 1

wire_qty = total_rebar_weight * 0.015
wire_total_cost = wire_qty * wire_mat_price
boq_rows.append([str(item_no), "ลวดผูกเหล็ก", f"{wire_qty:.2f}", "กก.", f"{wire_mat_price:,.2f}", f"{wire_total_cost:,.2f}", "0.00", "0.00", f"{wire_total_cost:,.2f}"])
item_no += 1

if sum_sp_area > 0:
    sp_cost = sum_sp_area * sp_slab_price
    boq_rows.append([str(item_no), "แผ่นพื้นสำเร็จรูป SP/PS", f"{sum_sp_area:.2f}", "ตร.ม.", f"{sp_slab_price:,.2f}", f"{sp_cost:,.2f}", "0.00", "0.00", f"{sp_cost:,.2f}"])
    item_no += 1

if sum_shoring_area > 0:
    shoring_m = sum_shoring_area * shoring_mat_price
    shoring_l = sum_shoring_area * shoring_lab_price
    boq_rows.append([str(item_no), "ไม้ค้ำยันแผ่นพื้นสำเร็จรูป", f"{sum_shoring_area:.2f}", "ตร.ม.", f"{shoring_mat_price:,.2f}", f"{shoring_m:,.2f}", f"{shoring_lab_price:,.2f}", f"{shoring_l:,.2f}", f"{shoring_m + shoring_l:,.2f}"])
    item_no += 1

total_mat_cost = (sum_piles_qty * pile_mat_price) + (sum_waterproof * waterproof_mat_price if sum_waterproof > 0 else 0) + sand_m + lean_m + c_mat + slab_conc_mat + f_mat + slab_form_mat + total_r_mat + nail_total_cost + wire_total_cost + (sum_sp_area * sp_slab_price if sum_sp_area > 0 else 0) + (sum_shoring_area * shoring_mat_price if sum_shoring_area > 0 else 0)
total_lab_cost = (sum_piles_qty * pile_lab_price) + earth_lab + sand_l + lean_l + c_lab + slab_conc_lab + f_lab + slab_form_lab + total_r_lab + (sum_shoring_area * shoring_lab_price if sum_shoring_area > 0 else 0)
grand_total = total_mat_cost + total_lab_cost

boq_columns = ["ลำดับที่", "รายการ", "จำนวน", "หน่วย", "ราคาต่อหน่วย (วัสดุ)", "รวมเงิน (วัสดุ)", "ราคาต่อหน่วย (ค่าแรง)", "รวมเงิน (ค่าแรง)", "รวมค่าวัสดุและค่าแรงงาน"]
boq_df = pd.DataFrame(boq_rows, columns=boq_columns)

with tab2:
    st.subheader("📊 สรุปรายการประมาณราคา (Master BOQ พร้อม Waste Factor)")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("รวมค่าวัสดุทั้งหมด", f"{total_mat_cost:,.2f} บาท")
    m2.metric("รวมค่าแรงทั้งหมด", f"{total_lab_cost:,.2f} บาท")
    m3.metric("งบประมาณรวมสุทธิ (Grand Total)", f"{grand_total:,.2f} บาท")
    
    st.markdown("---")
    st.dataframe(boq_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("🏢 สรุปงบประมาณแยกตามชั้น")
    st.write("ตารางแสดงยอดรวมค่าวัสดุและค่าแรงแยกตามชั้นที่ระบุในตารางกำหนดข้อมูลโครงการ")
    
    floor_summary_rows = []
    for flr, vals in floor_costs.items():
        if vals["total"] > 0:
            floor_summary_rows.append({
                "ชั้น / โซน": flr,
                "ค่าวัสดุ (บาท)": f"{vals['mat']:,.2f}",
                "ค่าแรงงาน (บาท)": f"{vals['lab']:,.2f}",
                "รวมสุทธิ (บาท)": f"{vals['total']:,.2f}",
                "สัดส่วน (%)": f"{(vals['total'] / grand_total * 100):.2f}%" if grand_total > 0 else "0.00%"
            })
    
    floor_df = pd.DataFrame(floor_summary_rows)
    st.dataframe(floor_df, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("📈 แผนภูมิวิเคราะห์สัดส่วนงบประมาณโครงสร้าง")
    chart_data = pd.DataFrame({
        "หมวดงาน": ["เสาเข็ม", "ดินขุด/ทราย/คอนกรีตหยาบ", "คอนกรีตโครงสร้างรวมพื้น", "ไม้แบบรวมพื้น", "เหล็กเสริม/ลวดผูก"],
        "งบประมาณ (บาท)": [
            (sum_piles_qty * pile_mat_price) + (sum_piles_qty * pile_lab_price),
            earth_lab + sand_m + sand_l + lean_m + lean_l,
            c_mat + c_lab + slab_conc_mat + slab_conc_lab,
            f_mat + f_lab + slab_form_mat + slab_form_lab + nail_total_cost,
            total_r_mat + total_r_lab + wire_total_cost
        ]
    })
    chart_data.set_index("หมวดงาน", inplace=True)
    st.bar_chart(chart_data)

# --- บันทึก / โหลดโปรเจกต์ (JSON Sidebar) ---
st.sidebar.divider()
st.sidebar.subheader("💾 ระบบบันทึกและโหลดโปรเจกต์")

project_data = {
    "waste": {"concrete": waste_concrete, "rebar": waste_rebar, "formwork": waste_formwork},
    "piles": edited_piles.to_dict(orient="records"),
    "earthworks": edited_earthworks.to_dict(orient="records"),
    "footings": edited_footings.to_dict(orient="records"),
    "beams": edited_beams.to_dict(orient="records"),
    "columns": edited_columns.to_dict(orient="records"),
    "slabs": edited_slabs.to_dict(orient="records"),
    "sp_slabs": edited_sp_slabs.to_dict(orient="records"),
}

json_str = json.dumps(project_data, ensure_ascii=False, indent=4)
st.sidebar.download_button(
    label="📥 บันทึกโปรเจกต์ (JSON)",
    data=json_str,
    file_name="buildquant_project.json",
    mime="application/json"
)

# --- ส่วนดาวน์โหลด Excel รวมทั้งโปรเจกต์ใน Sidebar ---
st.sidebar.divider()
output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    boq_df.to_excel(writer, index=False, sheet_name='Master_BOQ')
    if len(floor_summary_rows) > 0:
        pd.DataFrame(floor_summary_rows).to_excel(writer, index=False, sheet_name='Floor_Breakdown')
    edited_piles.to_excel(writer, index=False, sheet_name='Input_Piles')
    edited_earthworks.to_excel(writer, index=False, sheet_name='Input_Earthwork')
    edited_footings.to_excel(writer, index=False, sheet_name='Input_Footing')
    edited_beams.to_excel(writer, index=False, sheet_name='Input_Beam')
    edited_columns.to_excel(writer, index=False, sheet_name='Input_Column')
    edited_slabs.to_excel(writer, index=False, sheet_name='Input_Slab')
excel_data = output.getvalue()

st.sidebar.download_button(
    label="📥 ดาวน์โหลดรายงาน BOQ ทั้งหมด (Excel)",
    data=excel_data,
    file_name="BuildQuant_Pro_Structural_BOQ.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
