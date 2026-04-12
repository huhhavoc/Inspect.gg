import platform
import psutil
import wmi
import pythoncom
import pynvml
from datetime import datetime
import cpuinfo
from concurrent.futures import ThreadPoolExecutor

_CACHE = {}

def clear_cache():
    global _CACHE
    _CACHE = {}

def get_wmi():
    # CoInitialize handled in the caller's thread now
    return wmi.WMI()

def get_all_info():
    clear_cache()
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        f_os = executor.submit(get_os_info)
        f_bios = executor.submit(get_bios_info)
        f_cpu = executor.submit(get_cpu_info)
        f_gpu = executor.submit(get_gpu_info)
        f_ram = executor.submit(get_ram_info)
        f_disk = executor.submit(get_disk_info)
        f_battery = executor.submit(get_battery_info)
        f_display = executor.submit(get_display_info)
        f_network = executor.submit(get_network_info)
        f_thermals = executor.submit(get_thermal_info)
        
        return {
            "os": f_os.result(),
            "bios": f_bios.result(),
            "cpu": f_cpu.result(),
            "gpu": f_gpu.result(),
            "ram": f_ram.result(),
            "disk": f_disk.result(),
            "battery": f_battery.result(),
            "display": f_display.result(),
            "network": f_network.result(),
            "thermals": f_thermals.result()
        }

def _wmi_thread_wrapper(func):
    """Decorator to ensure COM threads are safely uninitialized."""
    def wrapper(*args, **kwargs):
        pythoncom.CoInitialize()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {"error": str(e)}
        finally:
            pythoncom.CoUninitialize()
    return wrapper

@_wmi_thread_wrapper
def get_os_info():
    w = get_wmi()
    os_data_list = w.Win32_OperatingSystem()
    if not os_data_list:
        return {"error": "OS data missing"}
    
    os_data = os_data_list[0]
    install_date_str = os_data.InstallDate.split('.')[0] if os_data.InstallDate else "20200101000000"
    install_date = datetime.strptime(install_date_str, '%Y%m%d%H%M%S')
    days_since_install = (datetime.now() - install_date).days
    
    return {
        "name": os_data.Caption,
        "version": os_data.Version,
        "build": os_data.BuildNumber,
        "install_date": install_date.strftime('%Y-%m-%d'),
        "days_since_install": days_since_install,
        "recently_wiped": days_since_install < 30
    }

@_wmi_thread_wrapper
def get_bios_info():
    if 'bios' in _CACHE:
        return _CACHE['bios']
    w = get_wmi()
    bios_list = w.Win32_BIOS()
    system_list = w.Win32_ComputerSystem()
    
    if not bios_list or not system_list:
        return {"error": "BIOS data missing"}
        
    bios = bios_list[0]
    system = system_list[0]
    
    bios_date_str = bios.ReleaseDate.split('.')[0] if bios.ReleaseDate else "20200101000000"
    bios_date = datetime.strptime(bios_date_str, '%Y%m%d%H%M%S')
    age_years = round((datetime.now() - bios_date).days / 365.25, 1)
    
    _CACHE['bios'] = {
        "manufacturer": system.Manufacturer,
        "model": system.Model,
        "bios_version": bios.SMBIOSBIOSVersion,
        "bios_date": bios_date.strftime('%Y-%m-%d'),
        "estimated_age_years": age_years
    }
    return _CACHE['bios']

@_wmi_thread_wrapper
def get_cpu_info():
    if 'cpu_meta' not in _CACHE:
        w = get_wmi()
        cpu_meta = cpuinfo.get_cpu_info()
        cpu_list = w.Win32_Processor()
        if not cpu_list:
            return {"error": "CPU data missing"}
            
        cpu_wmi = cpu_list[0]
        _CACHE['cpu_meta'] = {
            "name": cpu_meta.get('brand_raw', cpu_wmi.Name),
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "base_clock_mhz": cpu_wmi.MaxClockSpeed
        }
    
    data = dict(_CACHE['cpu_meta'])
    data["usage_percent"] = psutil.cpu_percent(interval=0.5)
    return data

@_wmi_thread_wrapper
def get_gpu_info():
    gpu_list = []
    nvml_success = False
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            meminfo = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            gpu_list.append({
                "name": name,
                "vram_total_mb": meminfo.total / (1024*1024),
                "usage_percent": util.gpu,
                "temp_c": temp
            })
        pynvml.nvmlShutdown()
        if len(gpu_list) > 0:
            nvml_success = True
    except:
        pass

    if not nvml_success:
        try:
            w = get_wmi()
            for v in w.Win32_VideoController():
                gpu_list.append({
                    "name": v.Name,
                    "vram_total_mb": int(v.AdapterRAM or 0) / (1024*1024),
                    "driver_version": v.DriverVersion,
                    "usage_percent": 0,
                    "temp_c": 0
                })
        except:
            pass

    if not gpu_list:
        return {"error": "Could not read GPU data"}
    return gpu_list

@_wmi_thread_wrapper
def get_ram_info():
    mem = psutil.virtual_memory()
    total_gb = round(mem.total / (1024**3), 2)
    used_gb = round(mem.used / (1024**3), 2)
    
    if 'ram_sticks' not in _CACHE:
        w = get_wmi()
        stick_speeds = []
        try:
            for m in w.Win32_PhysicalMemory():
                if m.Speed:
                    stick_speeds.append(m.Speed)
        except:
            pass
        _CACHE['ram_sticks'] = {
            "slots_used": len(stick_speeds),
            "speed_mhz": stick_speeds[0] if stick_speeds else "Unknown",
            "dual_channel": len(stick_speeds) > 1 and len(stick_speeds) % 2 == 0
        }
        
    return {
        "total_gb": total_gb,
        "used_gb": used_gb,
        "percent": mem.percent,
        **_CACHE['ram_sticks']
    }

@_wmi_thread_wrapper
def get_disk_info():
    import subprocess
    smart_status = {}
    smart_warning = False
    try:
        # Try wmic first (older Windows 10 support)
        output = subprocess.check_output(
            r'wmic /namespace:\\root\wmi path MSStorageDriver_FailurePredictStatus get InstanceName,PredictFailure /format:csv',
            shell=True, stderr=subprocess.DEVNULL, text=True
        )
        for line in output.split('\n'):
            parts = line.strip().split(',')
            if len(parts) >= 3 and 'PredictFailure' not in parts:
                inst = parts[1].lower()
                predict = parts[2].strip().upper() == 'TRUE'
                smart_status[inst] = predict
                if predict: smart_warning = True
    except:
        try:
            # Fallback to PowerShell (Modern Windows 10/11)
            ps_cmd = 'Get-CimInstance -Namespace root/WMI -ClassName MSStorageDriver_FailurePredictStatus | Select-Object InstanceName,PredictFailure | ConvertTo-Csv -NoTypeInformation'
            output = subprocess.check_output(['powershell', '-Command', ps_cmd], text=True, stderr=subprocess.DEVNULL)
            for line in output.strip().split('\n'):
                parts = line.strip().replace('"', '').split(',')
                if len(parts) >= 2 and 'PredictFailure' not in parts:
                    inst = parts[0].lower()
                    predict = parts[1].strip().upper() == 'TRUE'
                    smart_status[inst] = predict
                    if predict: smart_warning = True
        except:
            pass # No SMART data available through these methods

    w = get_wmi()
    disks = []
    for disk in w.Win32_DiskDrive():
        is_failing = False
        try:
            pnp = disk.PNPDeviceID.lower() if disk.PNPDeviceID else ""
            for k, v in smart_status.items():
                if pnp in k or k in pnp:
                    is_failing = v
        except:
            pass

        disks.append({
            "model": disk.Model,
            "type": disk.MediaType,
            "size_gb": round(int(disk.Size) / (1024**3), 2) if disk.Size else 0,
            "status": disk.Status,
            "smart_failing": is_failing
        })
    
    partitions = psutil.disk_usage('C:\\')
    
    return {
        "drives": disks,
        "c_drive_total_gb": round(partitions.total / (1024**3), 2),
        "c_drive_free_gb": round(partitions.free / (1024**3), 2),
        "smart_warning": smart_warning
    }

@_wmi_thread_wrapper
def get_battery_info():
    design_cap = 0
    full_cap = 0
    
    try:
        w_root = wmi.WMI(namespace="root\\WMI")
        static_data = w_root.BatteryStaticData()
        if static_data:
            design_cap = static_data[0].DesignedCapacity
            
        full_data = w_root.BatteryFullChargedCapacity()
        if full_data:
            full_cap = full_data[0].FullChargedCapacity
    except:
        pass

    w = get_wmi()
    batteries = w.Win32_Battery()
    
    ps_bat = psutil.sensors_battery()
    
    if full_cap == 0 and batteries and hasattr(batteries[0], 'FullChargeCapacity'):
        full_cap = batteries[0].FullChargeCapacity or 0
    if design_cap == 0 and batteries and hasattr(batteries[0], 'DesignCapacity'):
        design_cap = batteries[0].DesignCapacity or 0
        
    wear_level = 0.0
    if design_cap and full_cap and design_cap > 0:
        wear_level = max(0.0, float(((design_cap - full_cap) / design_cap) * 100))
        
    charge_percent = ps_bat.percent if ps_bat else (batteries[0].EstimatedChargeRemaining if batteries else 0)
    present = True if (design_cap > 0 or batteries or ps_bat) else False
    
    if not present:
        return {"present": False, "wear_level_percent": 0.0}

    if wear_level < 15:
        health = "Excellent"
    elif wear_level < 30:
        health = "Good"
    elif wear_level < 50:
        health = "Fair (Replace Soon)"
    else:
        health = "Poor (Replace Now)"
        
    return {
        "present": present,
        "charge_percent": charge_percent,
        "charging": ps_bat.power_plugged if ps_bat else False,
        "wear_level_percent": round(wear_level, 2),
        "health_label": health,
        "needs_replacement": wear_level > 40
    }

@_wmi_thread_wrapper
def get_display_info():
    w = get_wmi()
    displays = []
    for monitor in w.Win32_VideoController():
        if monitor.CurrentHorizontalResolution and monitor.CurrentVerticalResolution:
            displays.append({
                "resolution": f"{monitor.CurrentHorizontalResolution}x{monitor.CurrentVerticalResolution}",
                "refresh_rate": monitor.CurrentRefreshRate or 60
            })
    return displays

@_wmi_thread_wrapper
def get_network_info():
    w = get_wmi()
    adapters = []
    for net in w.Win32_NetworkAdapter(PhysicalAdapter=True):
        if net.NetEnabled: # Only connected/active ones maybe, or just enabled
            name = net.Name or ""
            # Filter as requested
            if "Ethernet 802.3" in name or "Wi-Fi" in name or "Wireless" in name or "AX" in name:
                wifi6 = "AX" in name.upper() or "WIFI 6" in name.upper() or "802.11AX" in name.upper()
                adapters.append({
                    "name": name,
                    "is_wifi6": wifi6
                })
    return adapters

def get_thermal_info():
    cpu_temp_c = None
    gpu_temp_c = None
    
    try:
        temps = psutil.sensors_temperatures()
        if 'coretemp' in temps and temps['coretemp']:
            cpu_temp_c = int(max(t.current for t in temps['coretemp']))
    except:
        pass
        
    try:
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_temp_c = int(pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU))
        pynvml.nvmlShutdown()
    except:
        pass
        
    return {
        "cpu_temp_c": cpu_temp_c,
        "gpu_temp_c": gpu_temp_c
    }
