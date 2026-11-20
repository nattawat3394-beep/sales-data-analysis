# -*- coding: utf-8 -*-
import csv
import json
import os
from collections import defaultdict, Counter

input_csv = r"C:\Users\MIRU\Downloads\sales_data.csv"
output_dir = r"c:\Users\MIRU\Desktop\งานจาร\sales-data-analysis"

with open(input_csv, "r", encoding="utf-8-sig", errors="replace") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

total_records = len(rows)
gross_revenue = sum(float(r["ยอดรวมสุทธิ"]) for r in rows)

# Detect Burst simultaneous orders
cust_minute = Counter((r["รหัสลูกค้า"], r["วันที่สั่งซื้อ"], r["เวลาสั่งซื้อ"]) for r in rows)
burst_keys = {k for k, v in cust_minute.items() if v > 1}

# Define the 7 Garbage Points
garbage_point_counts = {
    "point_1_canceled": 0,
    "point_2_returned": 0,
    "point_3_store_cod": 0,
    "point_4_store_off_hours": 0,
    "point_5_underage_cc": 0,
    "point_6_unspecified_gender": 0,
    "point_7_simultaneous_location": 0,
}

clean_rows = []
garbage_rows = []

for r in rows:
    reasons = []
    status = r["สถานะ"]
    channel = r["ช่องทางการขาย"]
    payment = r["วิธีชำระเงิน"]
    hour = int(r["เวลาสั่งซื้อ"].split(":")[0])
    age = int(r["อายุ"])
    gender = r["เพศ"]
    k = (r["รหัสลูกค้า"], r["วันที่สั่งซื้อ"], r["เวลาสั่งซื้อ"])

    # 1. Canceled
    if status == "ยกเลิก":
        reasons.append("จุดที่ 1: สถานะยกเลิก (ไม่เกิดการซื้อขายจริง)")
        garbage_point_counts["point_1_canceled"] += 1

    # 2. Returned
    if status == "คืนสินค้า":
        reasons.append("จุดที่ 2: สถานะคืนสินค้า (มีการคืนเงิน)")
        garbage_point_counts["point_2_returned"] += 1

    # 3. Store COD
    if channel == "หน้าร้าน" and payment == "เก็บเงินปลายทาง":
        reasons.append("จุดที่ 3: ซื้อหน้าร้านแต่ระบุเก็บเงินปลายทาง (ตรรกะ POS ผิดพลาด)")
        garbage_point_counts["point_3_store_cod"] += 1

    # 4. Store Off-hours
    if channel == "หน้าร้าน" and (hour < 8 or hour >= 22):
        reasons.append("จุดที่ 4: ซื้อหน้าร้านนอกเวลาทำการ (22:00 - 07:59 น.)")
        garbage_point_counts["point_4_store_off_hours"] += 1

    # 5. Underage credit card
    if age < 18 and payment == "บัตรเครดิต":
        reasons.append("จุดที่ 5: ผู้เยาว์อายุต่ำกว่า 18 ปีใช้บัตรเครดิต (ขัดต่อระเบียบการเงิน)")
        garbage_point_counts["point_5_underage_cc"] += 1

    # 6. Unspecified gender
    if gender == "ไม่ระบุ":
        reasons.append("จุดที่ 6: เพศไม่ระบุ (ข้อมูลประชากรไม่สมบูรณ์)")
        garbage_point_counts["point_6_unspecified_gender"] += 1

    # 7. Simultaneous Location
    if k in burst_keys:
        reasons.append("จุดที่ 7: ธุรกรรมชนเวลาต่างสถานที่พร้อมกัน (เป็นไปไม่ได้ทางกายภาพ)")
        garbage_point_counts["point_7_simultaneous_location"] += 1

    if len(reasons) > 0:
        garbage_rows.append({
            **r,
            "garbage_reasons": " | ".join(reasons),
            "reasons_count": len(reasons)
        })
    else:
        clean_rows.append(r)

# Financial calculation
clean_revenue = sum(float(r["ยอดรวมสุทธิ"]) for r in clean_rows)
clean_net = sum(float(r["ยอดก่อนค่าส่ง"]) for r in clean_rows)
clean_shipping = sum(float(r["ค่าจัดส่ง"]) for r in clean_rows)
clean_units = sum(int(r["จำนวน"]) for r in clean_rows)
garbage_revenue = sum(float(r["ยอดรวมสุทธิ"]) for r in garbage_rows)

reviews_list = [float(r["คะแนนรีวิว"]) for r in clean_rows if r["คะแนนรีวิว"].strip()]
avg_rating = sum(reviews_list) / len(reviews_list) if reviews_list else 0.0

# Monthly trends on Clean Data
monthly_data = defaultdict(lambda: {"real_revenue": 0.0, "orders": 0, "items": 0})
for r in clean_rows:
    m = r["วันที่สั่งซื้อ"][:7]
    monthly_data[m]["real_revenue"] += float(r["ยอดรวมสุทธิ"])
    monthly_data[m]["orders"] += 1
    monthly_data[m]["items"] += int(r["จำนวน"])

monthly_sorted = []
for m in sorted(monthly_data.keys()):
    d = monthly_data[m]
    monthly_sorted.append({
        "month": m,
        "real_revenue": round(d["real_revenue"], 2),
        "orders": d["orders"],
        "items": d["items"]
    })

# Categories (Clean Data)
category_stats = defaultdict(lambda: {"revenue": 0.0, "units": 0, "orders": 0})
for r in clean_rows:
    cat = r["หมวดสินค้า"]
    category_stats[cat]["revenue"] += float(r["ยอดรวมสุทธิ"])
    category_stats[cat]["units"] += int(r["จำนวน"])
    category_stats[cat]["orders"] += 1

categories_list = []
for cat, s in category_stats.items():
    categories_list.append({
        "category": cat,
        "revenue": round(s["revenue"], 2),
        "units": s["units"],
        "orders": s["orders"],
        "revenue_pct": round((s["revenue"] / clean_revenue) * 100, 2)
    })
categories_list.sort(key=lambda x: x["revenue"], reverse=True)

# Top Products (Clean Data)
prod_stats = defaultdict(lambda: {"category": "", "revenue": 0.0, "units": 0, "orders": 0, "ratings": [], "price_sum": 0.0, "count": 0})
for r in clean_rows:
    p = r["ชื่อสินค้า"]
    prod_stats[p]["category"] = r["หมวดสินค้า"]
    prod_stats[p]["revenue"] += float(r["ยอดรวมสุทธิ"])
    prod_stats[p]["units"] += int(r["จำนวน"])
    prod_stats[p]["orders"] += 1
    prod_stats[p]["price_sum"] += float(r["ราคาต่อหน่วย"])
    prod_stats[p]["count"] += 1
    if r["คะแนนรีวิว"].strip():
        prod_stats[p]["ratings"].append(float(r["คะแนนรีวิว"]))

top_products = []
for p, s in prod_stats.items():
    avg_r = sum(s["ratings"]) / len(s["ratings"]) if s["ratings"] else 0.0
    avg_p = s["price_sum"] / s["count"] if s["count"] else 0.0
    top_products.append({
        "product": p,
        "category": s["category"],
        "revenue": round(s["revenue"], 2),
        "units": s["units"],
        "orders": s["orders"],
        "avg_price": round(avg_p, 2),
        "avg_rating": round(avg_r, 2)
    })
top_products.sort(key=lambda x: x["revenue"], reverse=True)

# Channels (Clean Data)
channel_stats = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "units": 0})
for r in clean_rows:
    ch = r["ช่องทางการขาย"]
    channel_stats[ch]["revenue"] += float(r["ยอดรวมสุทธิ"])
    channel_stats[ch]["orders"] += 1
    channel_stats[ch]["units"] += int(r["จำนวน"])

channels_list = []
for ch, s in channel_stats.items():
    channels_list.append({
        "channel": ch,
        "revenue": round(s["revenue"], 2),
        "orders": s["orders"],
        "units": s["units"],
        "share_pct": round((s["revenue"] / clean_revenue) * 100, 2)
    })
channels_list.sort(key=lambda x: x["revenue"], reverse=True)

# Payments (Clean Data)
payment_stats = defaultdict(lambda: {"revenue": 0.0, "orders": 0})
for r in clean_rows:
    pay = r["วิธีชำระเงิน"]
    payment_stats[pay]["revenue"] += float(r["ยอดรวมสุทธิ"])
    payment_stats[pay]["orders"] += 1

payments_list = []
for pay, s in payment_stats.items():
    payments_list.append({
        "payment": pay,
        "revenue": round(s["revenue"], 2),
        "orders": s["orders"],
        "share_pct": round((s["revenue"] / clean_revenue) * 100, 2)
    })
payments_list.sort(key=lambda x: x["revenue"], reverse=True)

# Regions (Clean Data)
region_stats = defaultdict(lambda: {"revenue": 0.0, "orders": 0})
for r in clean_rows:
    reg = r["ภาค"]
    region_stats[reg]["revenue"] += float(r["ยอดรวมสุทธิ"])
    region_stats[reg]["orders"] += 1

regions_list = [{"region": k, "revenue": round(v["revenue"], 2), "orders": v["orders"]} for k, v in region_stats.items()]
regions_list.sort(key=lambda x: x["revenue"], reverse=True)

# Top 10 Provinces
prov_stats = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "region": ""})
for r in clean_rows:
    p = r["จังหวัด"]
    prov_stats[p]["revenue"] += float(r["ยอดรวมสุทธิ"])
    prov_stats[p]["orders"] += 1
    prov_stats[p]["region"] = r["ภาค"]

provinces_list = [{"province": k, "region": v["region"], "revenue": round(v["revenue"], 2), "orders": v["orders"]} for k, v in prov_stats.items()]
provinces_list.sort(key=lambda x: x["revenue"], reverse=True)

# Demographics (Clean Data)
age_groups = {
    "วัยรุ่น (< 20)": {"orders": 0, "revenue": 0.0},
    "วัยเริ่มทำงาน (20-29)": {"orders": 0, "revenue": 0.0},
    "วัยทำงาน (30-39)": {"orders": 0, "revenue": 0.0},
    "วัยผู้ใหญ่ (40-49)": {"orders": 0, "revenue": 0.0},
    "วัยสูงอายุ (50+)": {"orders": 0, "revenue": 0.0}
}
gender_stats = defaultdict(lambda: {"orders": 0, "revenue": 0.0})

for r in clean_rows:
    age = int(r["อายุ"])
    amt = float(r["ยอดรวมสุทธิ"])
    gen = r["เพศ"]
    
    if age < 20:
        age_groups["วัยรุ่น (< 20)"]["orders"] += 1
        age_groups["วัยรุ่น (< 20)"]["revenue"] += amt
    elif age < 30:
        age_groups["วัยเริ่มทำงาน (20-29)"]["orders"] += 1
        age_groups["วัยเริ่มทำงาน (20-29)"]["revenue"] += amt
    elif age < 40:
        age_groups["วัยทำงาน (30-39)"]["orders"] += 1
        age_groups["วัยทำงาน (30-39)"]["revenue"] += amt
    elif age < 50:
        age_groups["วัยผู้ใหญ่ (40-49)"]["orders"] += 1
        age_groups["วัยผู้ใหญ่ (40-49)"]["revenue"] += amt
    else:
        age_groups["วัยสูงอายุ (50+)"]["orders"] += 1
        age_groups["วัยสูงอายุ (50+)"]["revenue"] += amt
        
    gender_stats[gen]["orders"] += 1
    gender_stats[gen]["revenue"] += amt

age_list = [{"group": k, "orders": v["orders"], "revenue": round(v["revenue"], 2)} for k, v in age_groups.items()]
gender_list = [{"gender": k, "orders": v["orders"], "revenue": round(v["revenue"], 2)} for k, v in gender_stats.items()]

# Sample orders for table
sample_orders = []
for r in clean_rows[:1000]:
    sample_orders.append({
        "id": r["รหัสคำสั่งซื้อ"],
        "date": r["วันที่สั่งซื้อ"],
        "time": r["เวลาสั่งซื้อ"],
        "customer": r["รหัสลูกค้า"],
        "gender": r["เพศ"],
        "age": int(r["อายุ"]),
        "province": r["จังหวัด"],
        "region": r["ภาค"],
        "channel": r["ช่องทางการขาย"],
        "category": r["หมวดสินค้า"],
        "product": r["ชื่อสินค้า"],
        "price": float(r["ราคาต่อหน่วย"]),
        "qty": int(r["จำนวน"]),
        "discount": float(r["ส่วนลด(%)"]),
        "shipping": float(r["ค่าจัดส่ง"]),
        "total": float(r["ยอดรวมสุทธิ"]),
        "payment": r["วิธีชำระเงิน"],
        "status": r["สถานะ"],
        "rating": r["คะแนนรีวิว"] if r["คะแนนรีวิว"].strip() else "-"
    })

dashboard_data = {
    "kpis": {
        "gross_revenue": round(gross_revenue, 2),
        "clean_revenue": round(clean_revenue, 2),
        "removed_revenue": round(garbage_revenue, 2),
        "clean_net_merchandise": round(clean_net, 2),
        "clean_shipping": round(clean_shipping, 2),
        "total_initial_records": total_records,
        "clean_orders": len(clean_rows),
        "removed_orders": len(garbage_rows),
        "clean_units": clean_units,
        "clean_aov": round(clean_revenue / len(clean_rows), 2),
        "clean_rate": round((len(clean_rows) / total_records) * 100, 2),
        "garbage_rate": round((len(garbage_rows) / total_records) * 100, 2),
        "avg_rating": round(avg_rating, 2),
        "points": garbage_point_counts
    },
    "monthly": monthly_sorted,
    "categories": categories_list,
    "top_products": top_products,
    "channels": channels_list,
    "payments": payments_list,
    "regions": regions_list,
    "provinces": provinces_list[:10],
    "age_groups": age_list,
    "genders": gender_list,
    "sample_orders": sample_orders
}

# Export outputs
with open(os.path.join(output_dir, "dashboard_data.json"), "w", encoding="utf-8") as f:
    json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

with open(os.path.join(output_dir, "dashboard_data.js"), "w", encoding="utf-8") as f:
    f.write("const DASHBOARD_DATA = " + json.dumps(dashboard_data, ensure_ascii=False) + ";\n")

# Cleaned CSV
with open(os.path.join(output_dir, "cleaned_sales_data.csv"), "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(clean_rows)

# Garbage CSV
with open(os.path.join(output_dir, "garbage_sales_data.csv"), "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames + ["garbage_reasons", "reasons_count"])
    writer.writeheader()
    writer.writerows(garbage_rows)

print("SUCCESS: 7 Garbage Points fully removed!")
print(f"Pristine Clean Orders: {len(clean_rows)}")
print(f"Total Garbage Orders Removed: {len(garbage_rows)}")
print(f"Clean Realized Revenue: {clean_revenue:,.2f} THB")
