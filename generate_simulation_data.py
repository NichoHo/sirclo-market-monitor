import os
import csv
import random
from datetime import datetime, timedelta

random.seed(42)

# Ensure data directory exists
data_dir = os.path.join(os.getcwd(), "data")
os.makedirs(data_dir, exist_ok=True)

# 50 Beauty & Fashion SKUs
PRODUCTS = [
    # Hero SKUs (Beauty & Skincare)
    {"sku": "SKU-LIP-VELVET-01", "name": "Velvet Matte Lipstick - Dusky Rose", "category": "Lip Makeup", "normal_price": 129000, "cogs": 65000, "hero": True, "wh_stock": 500},
    {"sku": "SKU-LIP-VELVET-02", "name": "Velvet Matte Lipstick - Berry Red", "category": "Lip Makeup", "normal_price": 129000, "cogs": 65000, "hero": True, "wh_stock": 450},
    {"sku": "SKU-LIP-GLAZE-01", "name": "Dewy Tint Lip Glaze - Nude Peach", "category": "Lip Makeup", "normal_price": 115000, "cogs": 55000, "hero": True, "wh_stock": 600},
    {"sku": "SKU-SERUM-VITC-01", "name": "Glow Radiance Vitamin C Serum 30ml", "category": "Skincare", "normal_price": 179000, "cogs": 95000, "hero": True, "wh_stock": 550},
    {"sku": "SKU-SERUM-HYALU-01", "name": "Hydra Barrier Serum 50ml", "category": "Skincare", "normal_price": 165000, "cogs": 85000, "hero": True, "wh_stock": 480},
    {"sku": "SKU-SUNSCREEN-01", "name": "UV Shield Watery Sunscreen SPF50 50ml", "category": "Skincare", "normal_price": 139000, "cogs": 70000, "hero": True, "wh_stock": 700},
    {"sku": "SKU-CUSHION-01", "name": "Flawless Cover Cushion - 01 Light Beige", "category": "Complexion", "normal_price": 199000, "cogs": 105000, "hero": True, "wh_stock": 400},
    {"sku": "SKU-CUSHION-02", "name": "Flawless Cover Cushion - 02 Natural", "category": "Complexion", "normal_price": 199000, "cogs": 105000, "hero": True, "wh_stock": 520},
    {"sku": "SKU-MICELLAR-01", "name": "Gentle Cleansing Micellar Water 400ml", "category": "Skincare", "normal_price": 89000, "cogs": 45000, "hero": True, "wh_stock": 650},
    {"sku": "SKU-MOISTURIZER-01", "name": "Ceramide Deep Moisture Cream 50g", "category": "Skincare", "normal_price": 159000, "cogs": 80000, "hero": True, "wh_stock": 500},

    # Additional Beauty SKUs
    {"sku": "SKU-TONER-01", "name": "Centella Soothing Toner 150ml", "category": "Skincare", "normal_price": 125000, "cogs": 62000, "hero": False, "wh_stock": 250},
    {"sku": "SKU-CLEANSER-01", "name": "Low pH Amino Acid Facial Cleanser 100ml", "category": "Skincare", "normal_price": 95000, "cogs": 48000, "hero": False, "wh_stock": 300},
    {"sku": "SKU-EYELINER-01", "name": "Precision Waterproof Liquid Eyeliner - Black", "category": "Eye Makeup", "normal_price": 79000, "cogs": 38000, "hero": False, "wh_stock": 320},
    {"sku": "SKU-MASCARA-01", "name": "Lash Extender Volume Mascara", "category": "Eye Makeup", "normal_price": 109000, "cogs": 52000, "hero": False, "wh_stock": 280},
    {"sku": "SKU-BLUSH-01", "name": "Soft Cheek Liquid Blush - Dusty Coral", "category": "Cheek Makeup", "normal_price": 99000, "cogs": 49000, "hero": False, "wh_stock": 210},
    {"sku": "SKU-BLUSH-02", "name": "Soft Cheek Liquid Blush - Sweet Rose", "category": "Cheek Makeup", "normal_price": 99000, "cogs": 49000, "hero": False, "wh_stock": 190},
    {"sku": "SKU-POWDER-01", "name": "Translucent Silky Loose Powder 15g", "category": "Complexion", "normal_price": 119000, "cogs": 58000, "hero": False, "wh_stock": 240},
    {"sku": "SKU-CONCEALER-01", "name": "Spot Cover Concealer - Medium", "category": "Complexion", "normal_price": 89000, "cogs": 42000, "hero": False, "wh_stock": 180},
    {"sku": "SKU-SETTINGSPRAY-01", "name": "Matte Lock Makeup Setting Spray 100ml", "category": "Complexion", "normal_price": 119000, "cogs": 56000, "hero": False, "wh_stock": 310},
    {"sku": "SKU-CLAYMASK-01", "name": "Pore Purifying Mugwort Clay Mask 100g", "category": "Skincare", "normal_price": 129000, "cogs": 60000, "hero": False, "wh_stock": 260},
    {"sku": "SKU-EXFOLIATOR-01", "name": "AHA BHA PHA Peeling Solution 30ml", "category": "Skincare", "normal_price": 139000, "cogs": 68000, "hero": False, "wh_stock": 150},
    {"sku": "SKU-EYECREAM-01", "name": "Caffeine Eye Serum Roll-on 15ml", "category": "Skincare", "normal_price": 149000, "cogs": 72000, "hero": False, "wh_stock": 170},
    {"sku": "SKU-LIPBALM-01", "name": "Hydrating Berry Lip Sleeping Mask 20g", "category": "Lip Care", "normal_price": 85000, "cogs": 40000, "hero": False, "wh_stock": 230},
    {"sku": "SKU-LIPOIL-01", "name": "Plumping Peptide Lip Oil 6ml", "category": "Lip Makeup", "normal_price": 95000, "cogs": 46000, "hero": False, "wh_stock": 220},
    {"sku": "SKU-SHEETMASK-01", "name": "Collagen Firming Sheet Mask (Pack of 5)", "category": "Skincare", "normal_price": 75000, "cogs": 35000, "hero": False, "wh_stock": 350},
    {"sku": "SKU-BODYWASH-01", "name": "Brightening Body Wash Niacinamide 400ml", "category": "Body Care", "normal_price": 99000, "cogs": 48000, "hero": False, "wh_stock": 270},
    {"sku": "SKU-BODYLOTION-01", "name": "Deep Repair Body Serum 200ml", "category": "Body Care", "normal_price": 109000, "cogs": 53000, "hero": False, "wh_stock": 290},
    {"sku": "SKU-HAIRSERUM-01", "name": "Argan Hair Treatment Oil 80ml", "category": "Hair Care", "normal_price": 135000, "cogs": 65000, "hero": False, "wh_stock": 180},
    {"sku": "SKU-PERFUME-01", "name": "Eau de Parfum - Vanilla Mirage 50ml", "category": "Fragrance", "normal_price": 249000, "cogs": 115000, "hero": False, "wh_stock": 160},
    {"sku": "SKU-PERFUME-02", "name": "Eau de Parfum - Fresh Citrus Cedar 50ml", "category": "Fragrance", "normal_price": 249000, "cogs": 115000, "hero": False, "wh_stock": 140},

    # Fashion SKUs
    {"sku": "SKU-FASH-DRESS-01", "name": "Floral Tiered Midi Dress - Pastel Blue (S/M)", "category": "Fashion Dress", "normal_price": 289000, "cogs": 140000, "hero": True, "wh_stock": 420},
    {"sku": "SKU-FASH-DRESS-02", "name": "Satin Slip Evening Dress - Emerald (M/L)", "category": "Fashion Dress", "normal_price": 329000, "cogs": 160000, "hero": False, "wh_stock": 190},
    {"sku": "SKU-FASH-BLOUSE-01", "name": "Puff Sleeve Silk Blouse - Ivory (S)", "category": "Fashion Top", "normal_price": 219000, "cogs": 105000, "hero": False, "wh_stock": 210},
    {"sku": "SKU-FASH-BLOUSE-02", "name": "Puff Sleeve Silk Blouse - Ivory (M)", "category": "Fashion Top", "normal_price": 219000, "cogs": 105000, "hero": False, "wh_stock": 230},
    {"sku": "SKU-FASH-CARDIGAN-01", "name": "Cropped Knit Cardigan - Oatmeal", "category": "Fashion Knitwear", "normal_price": 199000, "cogs": 98000, "hero": False, "wh_stock": 170},
    {"sku": "SKU-FASH-PANTS-01", "name": "Wide Leg Pleated Trousers - Beige (M)", "category": "Fashion Bottom", "normal_price": 249000, "cogs": 120000, "hero": False, "wh_stock": 250},
    {"sku": "SKU-FASH-PANTS-02", "name": "Wide Leg Pleated Trousers - Black (L)", "category": "Fashion Bottom", "normal_price": 249000, "cogs": 120000, "hero": False, "wh_stock": 220},
    {"sku": "SKU-FASH-SKIRT-01", "name": "A-Line Pleated Midi Skirt - Taupe", "category": "Fashion Bottom", "normal_price": 189000, "cogs": 90000, "hero": False, "wh_stock": 180},
    {"sku": "SKU-FASH-BLAZER-01", "name": "Oversized Tailored Linen Blazer - Sand", "category": "Fashion Outerwear", "normal_price": 379000, "cogs": 185000, "hero": False, "wh_stock": 130},
    {"sku": "SKU-FASH-TEE-01", "name": "Essential Heavyweight Cotton Tee - White (M)", "category": "Fashion Top", "normal_price": 129000, "cogs": 55000, "hero": False, "wh_stock": 310},
    {"sku": "SKU-FASH-TEE-02", "name": "Essential Heavyweight Cotton Tee - Charcoal (L)", "category": "Fashion Top", "normal_price": 129000, "cogs": 55000, "hero": False, "wh_stock": 290},
    {"sku": "SKU-FASH-TOTE-01", "name": "Canvas Shoulder Tote Bag - Ecru", "category": "Fashion Accessories", "normal_price": 149000, "cogs": 65000, "hero": False, "wh_stock": 260},
    {"sku": "SKU-FASH-BAG-01", "name": "Vegan Leather Crossbody Bag - Espresso", "category": "Fashion Accessories", "normal_price": 279000, "cogs": 135000, "hero": False, "wh_stock": 160},
    {"sku": "SKU-FASH-SCARF-01", "name": "Printed Silk Voile Scarf - Flora Noir", "category": "Fashion Accessories", "normal_price": 99000, "cogs": 45000, "hero": False, "wh_stock": 220},
    {"sku": "SKU-FASH-BELT-01", "name": "Classic Brass Buckle Leather Belt - Tan", "category": "Fashion Accessories", "normal_price": 89000, "cogs": 38000, "hero": False, "wh_stock": 240},
    {"sku": "SKU-FASH-SANDAL-01", "name": "Strappy Low Block Heel Sandal - Cream (38)", "category": "Footwear", "normal_price": 269000, "cogs": 130000, "hero": False, "wh_stock": 140},
    {"sku": "SKU-FASH-FLAT-01", "name": "Pointed Toe Ballet Flat - Black (38)", "category": "Footwear", "normal_price": 239000, "cogs": 115000, "hero": False, "wh_stock": 150},
    {"sku": "SKU-FASH-LOUNGE-01", "name": "Ribbed Pajama Loungewear Set - Sage Green", "category": "Loungewear", "normal_price": 229000, "cogs": 110000, "hero": False, "wh_stock": 180},
    {"sku": "SKU-FASH-DENIM-01", "name": "High Waist Straight Denim - Vintage Blue (28)", "category": "Fashion Bottom", "normal_price": 299000, "cogs": 145000, "hero": False, "wh_stock": 200},
    {"sku": "SKU-FASH-SUNGLASS-01", "name": "Retro Cat-Eye UV400 Sunglasses - Tortoise", "category": "Fashion Accessories", "normal_price": 119000, "cogs": 50000, "hero": False, "wh_stock": 210},
]

# Write 1: Master Product Catalog & Warehouse Inventory
master_file = os.path.join(data_dir, "master_warehouse_inventory_cogs.csv")
with open(master_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "sku", "product_name", "category", "normal_price_idr", "cogs_idr",
        "warehouse_physical_stock", "shopee_allocated_stock", "tiktok_allocated_stock",
        "is_hero_sku", "status"
    ])
    for p in PRODUCTS:
        # Stock allocation setup:
        # Hero SKUs simulate the exact presentation problem:
        # Warehouse has 400-700 units left!
        # But Shopee allocated stock was small (e.g. 50) and has reached 0 during midnight rush!
        # TikTok still has some allocated stock (e.g. 35-60)
        if p["hero"]:
            shopee_alloc = 0 if random.random() < 0.7 else random.randint(1, 5) # 70% of hero SKUs are OOS on Shopee!
            tiktok_alloc = random.randint(25, 60)
        else:
            shopee_alloc = random.randint(15, 80)
            tiktok_alloc = random.randint(15, 80)
            
        writer.writerow([
            p["sku"], p["name"], p["category"], p["normal_price"], p["cogs"],
            p["wh_stock"], shopee_alloc, tiktok_alloc,
            "TRUE" if p["hero"] else "FALSE", "ACTIVE"
        ])

# Write 2: Shopee Inventory Export (50 rows)
# Formatted like standard Shopee Seller Centre "Product Info / Stock Update" export
shopee_inv_file = os.path.join(data_dir, "shopee_inventory.csv")
with open(shopee_inv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "item_id", "sku_reference_no", "product_name", "variation_name",
        "normal_price", "current_stock", "reserved_stock", "stock_status"
    ])
    for idx, p in enumerate(PRODUCTS, 1):
        item_id = f"SP-ITEM-{10000 + idx}"
        # Hero items have 0 or near 0 stock on Shopee (midnight stockout problem)
        if p["hero"]:
            stock = 0 if idx in [1, 2, 4, 6, 8, 31] else random.randint(1, 4)
        else:
            stock = random.randint(10, 85)
        reserved = random.randint(0, 5) if stock > 0 else 0
        status = "OUT_OF_STOCK" if stock == 0 else ("LOW_STOCK" if stock <= 5 else "IN_STOCK")
        
        writer.writerow([
            item_id, p["sku"], p["name"], "Default",
            p["normal_price"], stock, reserved, status
        ])

# Write 3: TikTok Shop Inventory Export (50 rows)
# Formatted like standard TikTok Shop Seller Center "Manage Stock" export
tiktok_inv_file = os.path.join(data_dir, "tiktok_inventory.csv")
with open(tiktok_inv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "product_id", "seller_sku", "product_name", "variation",
        "retail_price", "available_stock", "locked_stock", "inventory_status"
    ])
    for idx, p in enumerate(PRODUCTS, 1):
        prod_id = f"TT-PROD-{20000 + idx}"
        # TikTok has stock remaining for most hero items (imbalance!)
        if p["sku"] in ["SKU-SUNSCREEN-01", "SKU-CUSHION-02"]:
            stock = 0 # couple items sold out on TikTok too
        elif p["hero"]:
            stock = random.randint(25, 75)
        else:
            stock = random.randint(12, 90)
        locked = random.randint(0, 6) if stock > 0 else 0
        status = "OUT_OF_STOCK" if stock == 0 else ("LOW_STOCK" if stock <= 5 else "IN_STOCK")
        
        writer.writerow([
            prod_id, p["sku"], p["name"], "Standard",
            p["normal_price"], stock, locked, status
        ])

# Base time for Midnight Double-Day Mega Campaign (10.10)
base_time = datetime(2026, 10, 10, 0, 0, 0)

# Write 4: Shopee Orders Export (50 transactions)
# Shopee Seller Centre Order Report schema
# Includes stacked voucher cases where real price < COGS!
shopee_orders_file = os.path.join(data_dir, "shopee_orders.csv")
with open(shopee_orders_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "order_id", "order_creation_time", "order_status", "sku_reference_no",
        "product_name", "variation_name", "quantity", "original_price",
        "deal_price", "seller_voucher_discount", "seller_rebate",
        "shopee_voucher_subsidy", "seller_absorbed_discount_total",
        "real_selling_price_per_unit", "buyer_total_payment"
    ])
    
    # 50 Shopee transactions
    for i in range(1, 51):
        order_id = f"261010SP{i:04d}"
        created_time = (base_time + timedelta(minutes=random.randint(1, 115), seconds=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S")
        status = "Completed" if i > 30 else ("To Ship" if i > 5 else "Unpaid")
        
        # Pick a product
        # Prioritize hero products for midnight surge
        if i <= 30:
            prod = random.choice([p for p in PRODUCTS if p["hero"]])
        else:
            prod = random.choice(PRODUCTS)
            
        qty = 1 if random.random() < 0.85 else 2
        orig_price = prod["normal_price"]
        cogs = prod["cogs"]
        
        # Determine voucher stacking behavior:
        # In ~20% of orders, double voucher / flash deal stacking error happens selling BELOW COGS!
        is_stacked_error = (i in [3, 7, 12, 18, 22, 29, 36, 43, 49])
        
        if is_stacked_error:
            # Massive seller-absorbed stacked discounts:
            # e.g., Flash Sale deal price (20-30% off) + Store Voucher (Rp 30,000 - 50,000 off) + Seller Rebate
            deal_price = int(orig_price * random.uniform(0.70, 0.78))
            seller_deal_discount = (orig_price - deal_price) * qty
            seller_voucher = random.choice([35000, 40000, 50000]) * qty
            seller_rebate = random.choice([10000, 15000]) * qty
            # Total seller absorbed discount is so big that unit price drops below COGS
            seller_absorbed_total = seller_deal_discount + seller_voucher + seller_rebate
            shopee_subsidized_voucher = random.choice([10000, 20000]) # absorbed by Shopee, not seller
            
            # Ensure it is definitely below COGS
            real_unit_price = orig_price - (seller_absorbed_total // qty)
            if real_unit_price >= cogs:
                # Force below COGS by Rp 5,000 to Rp 25,000
                deficit = random.randint(8000, 22000)
                real_unit_price = cogs - deficit
                seller_absorbed_total = (orig_price - real_unit_price) * qty
        else:
            # Normal healthy transaction: Deal discount ~10-15% or small voucher
            deal_price = int(orig_price * random.uniform(0.85, 0.95))
            seller_deal_discount = (orig_price - deal_price) * qty
            has_voucher = random.random() < 0.4
            seller_voucher = (random.choice([10000, 15000, 20000]) * qty) if has_voucher else 0
            seller_rebate = 0
            shopee_subsidized_voucher = random.choice([0, 10000, 15000])
            seller_absorbed_total = seller_deal_discount + seller_voucher + seller_rebate
            real_unit_price = orig_price - (seller_absorbed_total // qty)
            
            # Safeguard healthy orders are comfortably above COGS
            if real_unit_price <= cogs:
                real_unit_price = int(cogs * 1.25)
                seller_absorbed_total = (orig_price - real_unit_price) * qty
                
        buyer_payment = (deal_price * qty) - seller_voucher - seller_rebate - shopee_subsidized_voucher
        if buyer_payment < 10000:
            buyer_payment = 10000
            
        writer.writerow([
            order_id, created_time, status, prod["sku"], prod["name"],
            "Default", qty, orig_price, deal_price, seller_voucher,
            seller_rebate, shopee_subsidized_voucher, seller_absorbed_total,
            real_unit_price, buyer_payment
        ])

# Write 5: TikTok Shop Orders Export (50 transactions)
# TikTok Shop Seller Center Order List schema
# Includes double voucher stacking error selling below COGS!
tiktok_orders_file = os.path.join(data_dir, "tiktok_orders.csv")
with open(tiktok_orders_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "order_id", "created_time", "order_status", "seller_sku",
        "product_name", "variation", "quantity", "retail_price",
        "seller_discount", "shop_voucher_discount", "platform_discount",
        "platform_voucher", "seller_absorbed_discount_total",
        "net_unit_settlement_price", "total_settlement_amount"
    ])
    
    for i in range(1, 51):
        order_id = f"5789102{i:04d}98"
        created_time = (base_time + timedelta(minutes=random.randint(1, 118), seconds=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S")
        status = "Completed" if i > 35 else ("Awaiting Shipment" if i > 8 else "Pending")
        
        # Product selection
        if i <= 28:
            prod = random.choice([p for p in PRODUCTS if p["hero"]])
        else:
            prod = random.choice(PRODUCTS)
            
        qty = 1 if random.random() < 0.8 else 2
        orig_price = prod["normal_price"]
        cogs = prod["cogs"]
        
        # Voucher stacking error simulation on TikTok
        is_stacked_error = (i in [2, 6, 11, 19, 25, 33, 40, 46])
        
        if is_stacked_error:
            # TikTok live / flash promo discount + Shop coupon stacked!
            seller_discount = int(orig_price * random.uniform(0.20, 0.30)) * qty
            shop_voucher = random.choice([30000, 45000, 50000]) * qty
            platform_discount = random.choice([10000, 15000]) * qty # TikTok co-funded
            platform_voucher = random.choice([10000, 20000]) # TikTok co-funded
            
            seller_absorbed = seller_discount + shop_voucher
            net_unit_price = orig_price - (seller_absorbed // qty)
            
            # Force below COGS
            if net_unit_price >= cogs:
                deficit = random.randint(9000, 25000)
                net_unit_price = cogs - deficit
                seller_absorbed = (orig_price - net_unit_price) * qty
        else:
            # Healthy TikTok order
            seller_discount = int(orig_price * random.uniform(0.08, 0.15)) * qty
            has_coupon = random.random() < 0.35
            shop_voucher = (random.choice([10000, 15000, 20000]) * qty) if has_coupon else 0
            platform_discount = random.choice([0, 10000]) * qty
            platform_voucher = random.choice([0, 15000])
            
            seller_absorbed = seller_discount + shop_voucher
            net_unit_price = orig_price - (seller_absorbed // qty)
            
            if net_unit_price <= cogs:
                net_unit_price = int(cogs * 1.28)
                seller_absorbed = (orig_price - net_unit_price) * qty
                
        total_settlement = net_unit_price * qty
        
        writer.writerow([
            order_id, created_time, status, prod["sku"], prod["name"],
            "Standard", qty, orig_price, seller_discount, shop_voucher,
            platform_discount, platform_voucher, seller_absorbed,
            net_unit_price, total_settlement
        ])

print("Simulation data generated successfully!")
print("Files created in:", data_dir)
