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

# 1. Classification & Garbage Audit
clean_rows = []
garbage_rows = []

audit_summary = {
    "total_records": total_records,
    "gross_revenue": sum(float(r["ยอดรวมสุทธิ"]) for r in rows),
    "completed_orders": 0,
    "completed_revenue": 0.0,
    "canceled_orders": 0,
    "canceled_revenue": 0.0,
    "returned_orders": 0,
    "returned_revenue": 0.0,
    "store_cod_anomalies": 0,
    "unspecified_gender_count": 0,
    "missing_review_count": 0
}

for r in rows:
    total_val = float(r["ยอดรวมสุทธิ"])
    status = r["สถานะ"]
    channel = r["ช่องทางการขาย"]
    payment = r["วิธีชำระเงิน"]
    gender = r["เพศ"]
    review = r["คะแนนรีวิว"]
    
    if status == "สำเร็จ":
        clean_rows.append(r)
        audit_summary["completed_orders"] += 1
        audit_summary["completed_revenue"] += total_val
    elif status == "ยกเลิก":
        garbage_rows.append({**r, "garbage_reason": "คำสั่งซื้อถูกยกเลิก (ไม่เกิดการขายจริง)"})
        audit_summary["canceled_orders"] += 1
        audit_summary["canceled_revenue"] += total_val
    elif status == "คืนสินค้า":
        garbage_rows.append({**r, "garbage_reason": "คืนสินค้าและคืนเงิน (สูญเสียรายได้)"})
        audit_summary["returned_orders"] += 1
        audit_summary["returned_revenue"] += total_val

    if channel == "หน้าร้าน" and payment == "เก็บเงินปลายทาง":
        audit_summary["store_cod_anomalies"] += 1

    if gender == "ไม่ระบุ":
        audit_summary["unspecified_gender_count"] += 1

    if not review.strip():
        audit_summary["missing_review_count"] += 1

audit_summary["lost_revenue"] = audit_summary["canceled_revenue"] + audit_summary["returned_revenue"]
audit_summary["realized_revenue"] = audit_summary["completed_revenue"]
audit_summary["real_success_rate"] = round((audit_summary["completed_orders"] / total_records) * 100, 2)
audit_summary["waste_rate"] = round(((audit_summary["canceled_orders"] + audit_summary["returned_orders"]) / total_records) * 100, 2)

# 2. Financial & Sales Metrics for Clean Data
clean_net_merchandise = sum(float(r["ยอดก่อนค่าส่ง"]) for r in clean_rows)
clean_shipping_total = sum(float(r["ค่าจัดส่ง"]) for r in clean_rows)
clean_units_sold = sum(int(r["จำนวน"]) for r in clean_rows)
clean_aov = audit_summary["realized_revenue"] / len(clean_rows)

reviews_list = [float(r["คะแนนรีวิว"]) for r in clean_rows if r["คะแนนรีวิว"].strip()]
avg_rating = sum(reviews_list) / len(reviews_list) if reviews_list else 0.0

# 3. Monthly Trends (2024 - 2025)
monthly_data = defaultdict(lambda: {
    "real_revenue": 0.0,
    "gross_revenue": 0.0,
    "canceled_revenue": 0.0,
    "returned_revenue": 0.0,
    "orders": 0,
    "items": 0
})

for r in rows:
    m = r["วันที่สั่งซื้อ"][:7] # YYYY-MM
    amt = float(r["ยอดรวมสุทธิ"])
    qty = int(r["จำนวน"])
    monthly_data[m]["gross_revenue"] += amt
    
    if r["สถานะ"] == "สำเร็จ":
        monthly_data[m]["real_revenue"] += amt
        monthly_data[m]["orders"] += 1
        monthly_data[m]["items"] += qty
    elif r["สถานะ"] == "ยกเลิก":
        monthly_data[m]["canceled_revenue"] += amt
    elif r["สถานะ"] == "คืนสินค้า":
        monthly_data[m]["returned_revenue"] += amt

monthly_sorted = []
for m in sorted(monthly_data.keys()):
    d = monthly_data[m]
    monthly_sorted.append({
        "month": m,
        "real_revenue": round(d["real_revenue"], 2),
        "gross_revenue": round(d["gross_revenue"], 2),
        "lost_revenue": round(d["canceled_revenue"] + d["returned_revenue"], 2),
        "orders": d["orders"],
        "items": d["items"]
    })

# 4. Categories Analysis (Cleaned Data)
category_stats = defaultdict(lambda: {"revenue": 0.0, "units": 0, "orders": 0, "products": set()})
for r in clean_rows:
    cat = r["หมวดสินค้า"]
    amt = float(r["ยอดรวมสุทธิ"])
    qty = int(r["จำนวน"])
    category_stats[cat]["revenue"] += amt
    category_stats[cat]["units"] += qty
    category_stats[cat]["orders"] += 1
    category_stats[cat]["products"].add(r["ชื่อสินค้า"])

categories_list = []
for cat, s in category_stats.items():
    categories_list.append({
        "category": cat,
        "revenue": round(s["revenue"], 2),
        "units": s["units"],
        "orders": s["orders"],
        "product_count": len(s["products"]),
        "revenue_pct": round((s["revenue"] / audit_summary["realized_revenue"]) * 100, 2)
    })
categories_list.sort(key=lambda x: x["revenue"], reverse=True)

# 5. Top Products (Cleaned Data)
product_stats = defaultdict(lambda: {
    "category": "",
    "revenue": 0.0,
    "units": 0,
    "orders": 0,
    "ratings": [],
    "unit_price_sum": 0.0,
    "price_records": 0
})

for r in clean_rows:
    p = r["ชื่อสินค้า"]
    cat = r["หมวดสินค้า"]
    amt = float(r["ยอดรวมสุทธิ"])
    qty = int(r["จำนวน"])
    price = float(r["ราคาต่อหน่วย"])
    
    product_stats[p]["category"] = cat
    product_stats[p]["revenue"] += amt
    product_stats[p]["units"] += qty
    product_stats[p]["orders"] += 1
    product_stats[p]["unit_price_sum"] += price
    product_stats[p]["price_records"] += 1
    if r["คะแนนรีวิว"].strip():
        product_stats[p]["ratings"].append(float(r["คะแนนรีวิว"]))

top_products = []
for p, s in product_stats.items():
    avg_r = sum(s["ratings"]) / len(s["ratings"]) if s["ratings"] else 0.0
    avg_p = s["unit_price_sum"] / s["price_records"] if s["price_records"] else 0.0
    top_products.append({
        "product": p,
        "category": s["category"],
        "revenue": round(s["revenue"], 2),
        "units": s["units"],
        "orders": s["orders"],
        "avg_price": round(avg_p, 2),
        "avg_rating": round(avg_r, 2),
        "review_count": len(s["ratings"])
    })
top_products.sort(key=lambda x: x["revenue"], reverse=True)

# 6. Channel Breakdown
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
        "aov": round(s["revenue"] / s["orders"], 2),
        "share_pct": round((s["revenue"] / audit_summary["realized_revenue"]) * 100, 2)
    })
channels_list.sort(key=lambda x: x["revenue"], reverse=True)

# 7. Payment Methods Breakdown
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
        "share_pct": round((s["revenue"] / audit_summary["realized_revenue"]) * 100, 2)
    })
payments_list.sort(key=lambda x: x["revenue"], reverse=True)

# 8. Regional & Top Provinces
region_stats = defaultdict(lambda: {"revenue": 0.0, "orders": 0})
province_stats = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "region": ""})

for r in clean_rows:
    reg = r["ภาค"]
    prov = r["จังหวัด"]
    amt = float(r["ยอดรวมสุทธิ"])
    region_stats[reg]["revenue"] += amt
    region_stats[reg]["orders"] += 1
    province_stats[prov]["revenue"] += amt
    province_stats[prov]["orders"] += 1
    province_stats[prov]["region"] = reg

regions_list = [{"region": k, "revenue": round(v["revenue"], 2), "orders": v["orders"]} for k, v in region_stats.items()]
regions_list.sort(key=lambda x: x["revenue"], reverse=True)

provinces_list = [{"province": k, "region": v["region"], "revenue": round(v["revenue"], 2), "orders": v["orders"]} for k, v in province_stats.items()]
provinces_list.sort(key=lambda x: x["revenue"], reverse=True)

# 9. Demographics (Age groups & Gender)
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

# 10. Shipping Days Breakdown
delivery_stats = Counter(int(r["จำนวนวันจัดส่ง"]) for r in clean_rows)
delivery_list = [{"days": f"{k} วัน" if k > 0 else "รับทันที (หน้าร้าน)", "orders": v} for k, v in sorted(delivery_stats.items())]

# 11. Prepare sample clean orders and sample garbage orders for UI table
sample_orders = []
for r in rows[:1000]: # First 1000 orders for interactive table
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
        "gross_revenue": round(audit_summary["gross_revenue"], 2),
        "realized_revenue": round(audit_summary["realized_revenue"], 2),
        "lost_revenue": round(audit_summary["lost_revenue"], 2),
        "net_merchandise": round(clean_net_merchandise, 2),
        "shipping_total": round(clean_shipping_total, 2),
        "total_orders_raw": total_records,
        "completed_orders": len(clean_rows),
        "canceled_orders": audit_summary["canceled_orders"],
        "returned_orders": audit_summary["returned_orders"],
        "units_sold": clean_units_sold,
        "aov": round(clean_aov, 2),
        "success_rate": audit_summary["real_success_rate"],
        "waste_rate": audit_summary["waste_rate"],
        "avg_rating": round(avg_rating, 2),
        "store_cod_anomalies": audit_summary["store_cod_anomalies"],
        "unspecified_gender_count": audit_summary["unspecified_gender_count"],
        "missing_review_count": audit_summary["missing_review_count"]
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
    "delivery": delivery_list,
    "sample_orders": sample_orders
}

# Save JSON and JS files
json_path = os.path.join(output_dir, "dashboard_data.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

js_path = os.path.join(output_dir, "dashboard_data.js")
with open(js_path, "w", encoding="utf-8") as f:
    f.write("const DASHBOARD_DATA = " + json.dumps(dashboard_data, ensure_ascii=False) + ";\n")

# Save cleaned CSV
clean_csv_path = os.path.join(output_dir, "cleaned_sales_data.csv")
with open(clean_csv_path, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(clean_rows)

# Save garbage CSV
garbage_csv_path = os.path.join(output_dir, "garbage_sales_data.csv")
with open(garbage_csv_path, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames + ["garbage_reason"])
    writer.writeheader()
    writer.writerows(garbage_rows)

print("SUCCESS: Data processed and exported successfully!")
print(f"Clean CSV rows: {len(clean_rows)}")
print(f"Garbage CSV rows: {len(garbage_rows)}")
print(f"Realized Revenue: {audit_summary['realized_revenue']:,.2f} THB")
print(f"Lost Revenue: {audit_summary['lost_revenue']:,.2f} THB")
