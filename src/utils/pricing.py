import json
import os
import sys
from datetime import datetime

def calculate_fair_price(data):
    """
    Calculates an internal fair price based on pricing.json matrix.
    Also returns the AI Valuation Prompt as a secondary value.
    """
    try:
        # Resolve path to pricing.json (assumed to be in src/ root)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, 'pricing.json')
        
        with open(json_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading pricing.json: {e}")
        # Fallback minimal config
        config = {"base_tiers": {"default": 25000}, "deductions": {}, "depreciation_per_year": 0.15}

    sys_info = data.get('system_info') or {}
    bench = data.get('benchmarks') or {}
    manual = data.get('manual_checks') or {}
    
    cpu = sys_info.get('cpu', {}).get('name', '').lower()
    gpu_list = sys_info.get('gpu', [])
    gpu = gpu_list[0].get('name', '').lower() if gpu_list else 'integrated'
    age = sys_info.get('bios', {}).get('estimated_age_years', 1)
    
    # 1. Base Price from Tiers
    base_p = 0
    for tier, val in config.get('base_tiers', {}).items():
        if tier in cpu:
            base_p = val
            break
    if base_p == 0: 
        base_p = config.get('base_tiers', {}).get('default', 25000)
        
    gpu_bonus = 0
    for tier, val in config.get('gpu_tiers', {}).items():
        if tier in gpu:
            gpu_bonus = val
            break
    
    initial_value = base_p + gpu_bonus
    
    # 2. Apply Depreciation
    dep_rate = config.get('depreciation_per_year', 0.15)
    depreciated_value = initial_value * ((1 - dep_rate) ** age)
    
    # 3. Deductions
    deductions = 0
    deduction_details = []
    
    # Robust fallback for deduction mapping
    DEFAULT_DEDUCTIONS = {
        "battery_wear_high": 6000,
        "battery_critical": 10000,
        "disk_smart_warning": 8000,
        "thermal_throttling": 4000,
        "ram_single_channel": 1500,
        "manual_check_failure": 2000,
        "display_issue": 5000,
        "recent_wipe_penalty": 2500
    }
    
    raw_ded_map = config.get('deductions', {})
    if not isinstance(raw_ded_map, dict): raw_ded_map = {}
    
    def get_ded(key):
        return raw_ded_map.get(key, DEFAULT_DEDUCTIONS.get(key, 0))
    
    # Battery
    bat_wear = sys_info.get('battery', {}).get('wear_level_percent', 0)
    if bat_wear > 40:
        amt = get_ded('battery_critical')
        deductions += amt
        deduction_details.append({"reason": "Critical Battery Wear", "amount": amt})
    elif bat_wear > 15:
        amt = get_ded('battery_wear_high')
        deductions += amt
        deduction_details.append({"reason": "High Battery Wear", "amount": amt})
        
    # Disk
    if sys_info.get('disk', {}).get('smart_warning'):
        amt = get_ded('disk_smart_warning')
        deductions += amt
        deduction_details.append({"reason": "S.M.A.R.T. Warning (Disk Failure Risk)", "amount": amt})
        
    # Thermal
    if bench.get('cpu', {}).get('throttling_detected'):
        amt = get_ded('thermal_throttling')
        deductions += amt
        deduction_details.append({"reason": "Thermal Throttling Detected", "amount": amt})
        
    # RAM
    if not sys_info.get('ram', {}).get('dual_channel'):
        amt = get_ded('ram_single_channel')
        deductions += amt
        deduction_details.append({"reason": "Single Channel RAM (Performance loss)", "amount": amt})
        
    # OS Status
    if sys_info.get('os', {}).get('recently_wiped'):
        amt = get_ded('recent_wipe_penalty')
        deductions += amt
        deduction_details.append({"reason": "Recently Wiped OS (Suspicious)", "amount": amt})

    # Manual Checks
    failed_p = manual.get('failed_ports', 0)
    if failed_p > 0:
        amt = get_ded('manual_check_failure') * failed_p
        deductions += amt
        deduction_details.append({"reason": f"{failed_p} Manual Check Failures", "amount": amt})

    # Display Issues
    if not manual.get('display_issues', True):
        amt = get_ded('display_issue')
        deductions += amt
        deduction_details.append({"reason": "Display Defects (Pixels/Bleed)", "amount": amt})

    fair_price = max(0, depreciated_value - deductions)
    
    # Generate Integrity Score (0-100)
    score = 100
    score -= (sys_info.get('battery', {}).get('wear_level_percent', 0) * 0.5)
    if sys_info.get('disk', {}).get('smart_warning'): score -= 30
    if bench.get('cpu', {}).get('throttling_detected'): score -= 15
    score -= (failed_p * 5)
    score = max(0, min(100, int(score)))

    # Construct the AI valuation Prompt
    valuation_prompt = generate_ai_valuation_prompt(data, {
        "base_price": int(depreciated_value),
        "total_deductions": int(deductions),
        "estimated_fair_price": int(fair_price),
        "overall_health_score": score
    })

    return {
        "base_price": int(depreciated_value),
        "total_deductions": int(deductions),
        "estimated_fair_price": int(fair_price),
        "overall_health_score": score,
        "deductions": deduction_details,
        "valuation_prompt": valuation_prompt
    }

def generate_ai_valuation_prompt(data, price_metrics):
    """
    Helper to generate the multi-line text prompt for AI.
    """
    sys_info = data.get('system_info') or {}
    bench = data.get('benchmarks') or {}
    manual = data.get('manual_checks', {})
    
    # Extract sub-sections
    cpu = sys_info.get('cpu', {})
    gpu_list = sys_info.get('gpu', [])
    gpu = gpu_list[0] if gpu_list else {}
    ram = sys_info.get('ram', {})
    disk = sys_info.get('disk', {})
    battery = sys_info.get('battery', {})
    bios = sys_info.get('bios', {})
    os_info = sys_info.get('os', {})
    display_list = sys_info.get('display', [])
    display = display_list[0] if display_list else {}
    thermals = sys_info.get('thermals', {})
    
    prompt = f"""You are an expert in the Indian second-hand laptop market with deep knowledge of current resale prices.

I am inspecting a used laptop before buying it. Below is the full hardware diagnostic report generated by Inspect.gg. Your job is to give me a precise, fair market valuation in INR.

== DEVICE IDENTITY ==
Manufacturer: {bios.get('manufacturer', 'Unknown')}
Model: {bios.get('model', 'Unknown')}
Estimated Hardware Age: {bios.get('estimated_age_years', 1)} years
BIOS Date: {bios.get('bios_date', 'Unknown')}

== OPERATING SYSTEM ==
OS: {os_info.get('name', 'Unknown')}
Recently Wiped: {'Yes' if os_info.get('recently_wiped') else 'No'}

== CPU ==
Model: {cpu.get('name', 'Unknown')}
Cores / Threads: {cpu.get('cores', '0')} / {cpu.get('threads', '0')}
Stress Test Score: {bench.get('cpu', {}).get('ops_per_second', '0')} ops/sec
Thermal Throttling Detected: {'Yes' if bench.get('cpu', {}).get('throttling_detected') else 'No'}

== GPU ==
Model: {gpu.get('name', 'Integrated')}
GPU Health: {bench.get('gpu', {}).get('health_label', 'Pending')}

== RAM ==
Total: {ram.get('total_gb', '0')} GB
Dual Channel: {'Yes' if ram.get('dual_channel') else 'No'}

== STORAGE ==
Read Speed: {bench.get('disk', {}).get('read_speed_mb_s', '0')} MB/s
Write Speed: {bench.get('disk', {}).get('write_speed_mb_s', '0')} MB/s
SMART Status: {'Warning' if disk.get('smart_warning') else 'Healthy'}

== BATTERY ==
Wear Level: {battery.get('wear_level_percent', '0')}%
Health Label: {battery.get('health_label', 'N/A')}

== INSPECT.GG CALCULATED ESTIMATE ==
Base Depreciated Value: ₹{price_metrics['base_price']:,}
Total Deductions: -₹{price_metrics['total_deductions']:,}
Inspect.gg Fair Price: ₹{price_metrics['estimated_fair_price']:,}
Overall Health Score: {price_metrics['overall_health_score']}/100

Please provide:
1. FAIR MARKET PRICE (INR RANGE)
2. NEGOTIATION TARGET
3. RED FLAGS
4. HIDDEN COST ESTIMATE
5. FINAL VERDICT"""

    return prompt
