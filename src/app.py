import os
import json
import glob
import time
from datetime import datetime
import uuid
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, render_template, Response, stream_with_context
import ctypes
from config import Config

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)

# Setup logging
try:
    if not os.path.exists(Config.LOG_DIR):
        os.makedirs(Config.LOG_DIR, exist_ok=True)
    logger = logging.getLogger('InspectGG')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(os.path.join(Config.LOG_DIR, 'app.log'), maxBytes=1000000, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
except Exception as e:
    print(f"Logging setup failed: {e}")

@app.route('/api/ping')
def ping():
    return jsonify({"status": "online", "time": time.time()})

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

@app.route('/')
def index():
    admin_status = is_admin()
    session_id = str(uuid.uuid4())
    logger.info(f"New session established: {session_id} (Admin: {admin_status})")
    return render_template('index.html', admin_status=admin_status, session_id=session_id)

@app.route('/api/thermals')
def live_thermals():
    import psutil
    import pynvml
    def generate():
        while True:
            cpu_temp = 0
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps and temps['coretemp']:
                    cpu_temp = max(t.current for t in temps['coretemp'])
            
            gpu_temp = 0
            try:
                pynvml.nvmlInit()
                h = pynvml.nvmlDeviceGetHandleByIndex(0)
                gpu_temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
                pynvml.nvmlShutdown()
            except:
                pass
            
            yield "data: " + json.dumps({'cpu_temp': cpu_temp, 'gpu_temp': gpu_temp}) + "\n\n"
            time.sleep(2)
    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route('/api/run_all_sse')
def run_all_sse():
    session_id = request.args.get('session_id', 'default')
    logger.info(f"Starting hardware scans and benchmarks for session: {session_id}")
    
    def generate():
        from utils.system_info import get_all_info
        from utils.benchmarks import run_cpu_benchmark, run_gpu_benchmark, run_disk_benchmark, run_ram_benchmark
        
        # 1. System Scan
        yield "data: " + json.dumps({"step": "scan", "status": "running"}) + "\n\n"
        try:
            sys_info = get_all_info()
            yield "data: " + json.dumps({"step": "scan", "status": "complete", "data": sys_info}) + "\n\n"
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            yield "data: " + json.dumps({"step": "scan", "status": "error", "message": str(e)}) + "\n\n"

        # 2. CPU
        yield "data: " + json.dumps({"step": "cpu", "status": "running"}) + "\n\n"
        try:
            cpu_res = run_cpu_benchmark()
            yield "data: " + json.dumps({"step": "cpu", "status": "complete", "data": cpu_res}) + "\n\n"
        except Exception as e:
            logger.error(f"CPU Bench failed: {e}")
            yield "data: " + json.dumps({"step": "cpu", "status": "error", "message": str(e)}) + "\n\n"
            
        # 3. GPU
        yield "data: " + json.dumps({"step": "gpu", "status": "running"}) + "\n\n"
        try:
            gpu_res = run_gpu_benchmark()
            yield "data: " + json.dumps({"step": "gpu", "status": "complete", "data": gpu_res}) + "\n\n"
        except Exception as e:
            logger.error(f"GPU Bench failed: {e}")
            yield "data: " + json.dumps({"step": "gpu", "status": "error", "message": str(e)}) + "\n\n"
            
        # 4. Disk
        yield "data: " + json.dumps({"step": "disk", "status": "running"}) + "\n\n"
        try:
            disk_res = run_disk_benchmark()
            yield "data: " + json.dumps({"step": "disk", "status": "complete", "data": disk_res}) + "\n\n"
        except Exception as e:
            logger.error(f"Disk Bench failed: {e}")
            yield "data: " + json.dumps({"step": "disk", "status": "error", "message": str(e)}) + "\n\n"
            
        # 5. RAM
        yield "data: " + json.dumps({"step": "ram", "status": "running"}) + "\n\n"
        try:
            ram_res = run_ram_benchmark()
            yield "data: " + json.dumps({"step": "ram", "status": "complete", "data": ram_res}) + "\n\n"
        except Exception as e:
            logger.error(f"RAM Bench failed: {e}")
            yield "data: " + json.dumps({"step": "ram", "status": "error", "message": str(e)}) + "\n\n"

        yield "data: " + json.dumps({"step": "done", "status": "complete"}) + "\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route('/api/price', methods=['POST'])
def calculate_price():
    from utils.pricing import calculate_fair_price
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        
        # Calculate with Internal Logic + Build Prompt
        result = calculate_fair_price(data)
        
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_path = os.path.join(Config.RESULTS_DIR, f'scan_{ts}_{session_id}.json')
        with open(save_path, 'w') as f:
            full_data = {"request": data, "result": result}
            json.dump(full_data, f, indent=4)
            
        logger.info(f"Saved session {session_id} valuation data to {save_path}")
        
        return jsonify({"success": True, "data": result, "saved_to": save_path})
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Price calculation failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/export/<session_id>')
def export_html(session_id):
    files = glob.glob(os.path.join(Config.RESULTS_DIR, f'*_{session_id}.json'))
    if not files:
        return "No scan data found. Please run Calculate Price first.", 404
        
    latest_file = sorted(files)[-1]
    with open(latest_file, 'r') as f:
        data = json.load(f)
        
    html = render_template('report.html', data=data, json_dumps=json.dumps)
    return Response(html, mimetype="text/html", headers={"Content-Disposition": f"attachment; filename=inspectgg_report_{session_id}.html"})

if __name__ == '__main__':
    logger.info("Initializing Inspect.gg Flask Server...")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
