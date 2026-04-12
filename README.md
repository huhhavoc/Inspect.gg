# 💻 Inspect.gg 

<p align="center">
  <b>A hardware inspection and fair price calculator for second-hand laptops — built for Indian buyers.</b><br>
  ![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)
  ![Platform: Windows](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
  ![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
  ![Made with Flask](https://img.shields.io/badge/Made%20with-Flask-black.svg)
</p>

---

## 📌 What it does

**Inspect.gg** is a powerful diagnostic utility designed to protect buyers from "lemon" deals in the Indian second-hand market. It runs locally on the target machine, performing deep hardware telemetry scans via WMI and pynvml to audit system health. Beyond just reporting specs, it runs isolated stress tests on the CPU, GPU, RAM, and storage to detect hidden performance bottlenecks or thermal throttling. Finally, it calculates a fair market valuation in INR based on your customizable pricing rules and generates a high-fidelity **AI Valuation Prompt** to get a second opinion from services like ChatGPT or Gemini.

## 📸 Screenshots

![Inspect.gg UI](docs/screenshot.png)
> **Note**: Replace with actual screenshot before publishing.

## 🚀 Quick Start

1. **Clone the repo**:
   ```powershell
   git clone https://github.com/yourusername/inspect.gg.git
   cd inspect.gg
   ```
2. **Launch with 1-Click**:
   Double-click **`launcher.bat`**. This script will automatically check for Python, install a virtual environment, resolve all dependencies, and launch the application.
3. **Automatic Access**:
   Your browser will open to `http://localhost:5000` automatically once the server is ready.
4. **Inspect**:
   Click **"Run All Tests"** to begin the full diagnostic sweep.

> [!WARNING]
> **Must be run as Administrator**: Low-level hardware telemetry (WMI and CPU thermal headers) requires elevated privileges to access complete data.

## 🛠️ Manual Setup

For developers who prefer manual control:
1. Open PowerShell/CMD as **Administrator**.
2. `python -m venv venv`
3. `venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `cd src && python app.py`

## 📊 What gets tested

| Component | Method | What it checks |
| :--- | :--- | :--- |
| **CPU** | Subprocess Workers | Base clock, thermal throttling, raw operations/sec |
| **GPU** | NVML / WMI | VRAM throughput, rendering health, model identity |
| **RAM** | Array Allocation | Bandwidth (GB/s), dual-channel config, total capacity |
| **Disk** | I/O Temporary Chunks | Read/Write speeds, S.M.A.R.T failure prediction |
| **Battery** | Win32_Battery | Wear level percentage, design capacity vs current |
| **Thermals** | Native WMI Maps | CPU/GPU temperatures under load |
| **OS / BIOS** | Registry & WMI | OS "Recently Wiped" status, BIOS age, build version |
| **Manual** | UI Checkbox Grid | USB ports, HDMI, Webcam, Mic, Speakers, WiFi/BT |
| **Display** | Fullscreen Overlay | Dead pixels, color bleeding, refresh rate |

## 💰 Fair Price Calculator

Inspect.gg uses a transparent, tiered pricing engine located in `src/pricing.json`. You can modify this file to adjust base prices for different CPU/GPU generations, customize deduction amounts for specific flaws (e.g., -₹6,000 for high battery wear), and tune the annual depreciation rate. The tool aggregates all benchmark failures and hardware flaws to calculate an instant buyer's valuation in INR.

## 📁 Project Structure

```text
inspect.gg/
├── launcher.bat       # 1-Click entry point & auto-configurator
├── requirements.txt   # Python dependency list
├── pricing.json       # User-editable pricing & deduction matrix
├── docs/              # Documentation, changelogs, and images
├── src/
│   ├── app.py         # Flask server & SSE event stream
│   ├── config.py      # App paths & log configuration
│   └── utils/
│       ├── pricing.py # Valuation logic & AI prompt engine
│       ├── system_info.py # WMI hardware audit logic
│       └── benchmarks.py  # Isolated subsystem stress tests
├── templates/
│   └── index.html     # Claymorphism dashboard UI
└── static/
    ├── style.css      # Custom UI design system
    └── app.js         # Frontend telemetry processing logic
```

## ⚠️ Known Limitations

- **Windows only**: Relies on WMI and Win32 APIs which are exclusive to Windows.
- **NVIDIA Focus**: The GPU benchmark is optimized for NVIDIA via pynvml; AMD/Intel iGPUs use a lighter WMI fallback.
- **Battery Data**: Telemetry accuracy depends on the OEM's WMI implementation level.
- **Thermals**: Specific thermal headers may not be accessible on all motherboard combinations.
- **Permissions**: **Must be run as Administrator** for the most accurate diagnostic data.

## 🤝 Contributing

Pull requests are welcome! If you are adding new hardware checks, please implement them in `system_info.py` and ensure they handle `None` returns gracefully to prevent stream crashes. If you are tuning market prices for a specific region, please update `pricing.json` only.

## 📜 License

This project is licensed under the **MIT License** — feel free to use, modify, and distribute it as you see fit.
