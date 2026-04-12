let healthChartInstance = null;
let scanData = {};
let benchData = {};
let sessionId = 'default';
let thermalsSource = null;

document.addEventListener('DOMContentLoaded', () => {
    initChart();
    
    const sidEl = document.getElementById('session_id');
    if(sidEl) sessionId = sidEl.value;
    
    document.getElementById('runAllBtn').addEventListener('click', runAllTestsSSE);
    document.getElementById('displayTestBtn').addEventListener('click', runDisplayTest);
    document.getElementById('generateValuationBtn').addEventListener('click', calculatePrice);
    document.getElementById('copyPromptBtn').addEventListener('click', copyPromptToClipboard);
    document.getElementById('openAIBtn').addEventListener('click', openAIExternal);
    
    // Check missing badges early
    document.querySelectorAll('.badge').forEach(b => {
        if(b.innerText === 'Pending') b.classList.add('warn');
    });
});

function initChart() {
    const canvas = document.getElementById('healthChart');
    if(!canvas) return;
    
    if (typeof Chart === 'undefined') {
        console.warn("Chart.js not loaded. Skipping doughnut chart.");
        document.getElementById('healthScoreText').innerText = "Offline";
        return;
    }

    const ctx = canvas.getContext('2d');
    healthChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Health Score', 'Issues'],
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#447F98', '#DADEE1'],
                borderWidth: 0,
                cutout: '80%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { tooltip: { enabled: false }, legend: { display: false } },
            animation: { animateScale: true, animateRotate: true }
        }
    });
}

function updateChart(score) {
    let color = '#447F98';
    if(score < 50) color = '#dc3545';
    else if(score < 75) color = '#ffc107';
    else if(score >= 90) color = '#28a745';
    
    if(healthChartInstance) {
        healthChartInstance.data.datasets[0].data = [score, 100 - score];
        healthChartInstance.data.datasets[0].backgroundColor = [color, '#DADEE1'];
        healthChartInstance.update();
    }
    
    const textEl = document.getElementById('healthScoreText');
    if(textEl) {
        textEl.innerText = score;
        textEl.style.color = color;
    }
}

async function runAllTestsSSE() {
    document.getElementById('runAllBtn').style.display = 'none';
    document.getElementById('mainProgressContainer').style.display = 'block';
    document.getElementById('resultsSections').style.display = 'block';
    
    const thermalsDiv = document.getElementById('liveThermals');
    thermalsDiv.style.display = 'block';
    if(thermalsSource) thermalsSource.close();
    thermalsSource = new EventSource('/api/thermals');
    thermalsSource.onmessage = function(e) {
        const d = JSON.parse(e.data);
        thermalsDiv.innerText = `🔥 LIVE THERMALS: CPU ${d.cpu_temp}°C | GPU ${d.gpu_temp}°C`;
    };
    
    const pb = document.getElementById('mainProgressBar');
    const status = document.getElementById('statusText');
    
    pb.style.width = '5%';
    status.innerText = "Connecting to benchmark server...";
    
    const source = new EventSource(`/api/run_all_sse?session_id=${sessionId}`);
    
    source.onmessage = function(event) {
        const payload = JSON.parse(event.data);
        const st = payload.step;
        const stat = payload.status;
        
        if(stat === 'error') {
            console.error(`Error in ${st}:`, payload.message);
            updateBadge(`badge-${st === 'scan' ? 'os' : st}`, 'Could not read', 'bad');
        }
        
        if (st === 'scan') {
            if(stat === 'running') { pb.style.width = '10%'; status.innerText = "Scanning System Info..."; }
            if(stat === 'complete') {
                scanData = payload.data;
                renderSystemInfo(scanData);
                pb.style.width = '30%';
            }
        } 
        else if (st === 'cpu') {
            if(stat === 'running') { status.innerText = "Running CPU Stress Test (this takes a few seconds)..."; }
            if(stat === 'complete') {
                benchData.cpu = payload.data;
                renderCpuBench(payload.data);
                pb.style.width = '55%';
            }
        }
        else if (st === 'gpu') {
            if(stat === 'running') { status.innerText = "Running GPU Benchmark..."; }
            if(stat === 'complete') {
                benchData.gpu = payload.data;
                renderGpuBench(payload.data);
                pb.style.width = '70%';
            }
        }
        else if (st === 'disk') {
            if(stat === 'running') { status.innerText = "Running Disk I/O Benchmark..."; }
            if(stat === 'complete') {
                benchData.disk = payload.data;
                renderDiskBench(payload.data);
                pb.style.width = '85%';
            }
        }
        else if (st === 'ram') {
            if(stat === 'running') { status.innerText = "Running RAM Bandwidth Test..."; }
            if(stat === 'complete') {
                benchData.ram = payload.data;
                renderRamBench(payload.data);
                pb.style.width = '95%';
            }
        }
        else if (st === 'done') {
            pb.style.width = '100%';
            status.innerText = "Tests Complete! Please complete Manual Checks and calculate Fair Price.";
            source.close();
            if(thermalsSource) thermalsSource.close();
            document.getElementById('liveThermals').innerText = "Tests finished. Thermals monitoring idle.";
            
            // Show manually prompted calculation message
            const promptBox = document.getElementById('manualPrompt');
            if(promptBox) { promptBox.style.display = 'block'; }
        }
    };
    
    source.onerror = function() {
        console.error("SSE Connection error.");
        status.innerText = "Connection lost or tests failed midway.";
        source.close();
    };
}

function safeSetInnerHtml(id, html) {
    const el = document.getElementById(id);
    if(el) el.innerHTML = html;
}

function generateTrafficLightHTML(healthLabel) {
    // Red / Yellow / Green indicator
    const h = healthLabel ? healthLabel.toLowerCase() : '';
    let red = '', yellow = '', green = '';
    
    if (h.includes('excellent') || h.includes('good') || h.includes('pass') || h.includes('healthy')) green = 'active-tl';
    else if (h.includes('fair') || h.includes('warn') || h.includes('aging') || h.includes('suspicious')) yellow = 'active-tl';
    else red = 'active-tl';
    
    return `<div class="traffic-light"><div class="tl-circle red ${red}"></div><div class="tl-circle yellow ${yellow}"></div><div class="tl-circle green ${green}"></div></div>`;
}

function renderSystemInfo(data) {
    if(data.os && data.os.error) {
        safeSetInnerHtml('content-os', `<p style="color:red;">Error: ${data.os.error}</p>`);
        updateBadge('badge-os', 'Error', 'bad');
    } else if (data.os) {
        safeSetInnerHtml('content-os', `
            <p><strong>Name:</strong> ${data.os.name}</p>
            <p><strong>Version:</strong> ${data.os.version} (Build ${data.os.build})</p>
            <p><strong>Installed:</strong> ${data.os.install_date} (${data.os.days_since_install} days ago)</p>
            ${data.os.recently_wiped ? '<p style="color:#ff6b6b;font-weight:bold;">⚠️ Recently Wiped</p>' : ''}
        `);
        updateBadge('badge-os', data.os.recently_wiped ? 'Suspicious' : 'Clean', data.os.recently_wiped ? 'warn' : 'good');
    }

    if(data.bios && data.bios.error) {
        safeSetInnerHtml('content-bios', `<p style="color:red;">Error: ${data.bios.error}</p>`);
        updateBadge('badge-bios', 'Error', 'bad');
    } else if (data.bios) {
        safeSetInnerHtml('content-bios', `
            <p><strong>Manufacturer:</strong> ${data.bios.manufacturer}</p>
            <p><strong>Model:</strong> ${data.bios.model}</p>
            <p><strong>Version:</strong> ${data.bios.bios_version}</p>
            <p><strong>Date:</strong> ${data.bios.bios_date}</p>
            <p><strong>Est. Age:</strong> ${data.bios.estimated_age_years} years</p>
        `);
        let ageLabel = data.bios.estimated_age_years > 3 ? 'Old' : (data.bios.estimated_age_years > 1 ? 'Mid' : 'New');
        updateBadge('badge-bios', ageLabel, ageLabel==='Old' ? 'warn' : 'good');
    }

    if(data.cpu && data.cpu.error) {
        safeSetInnerHtml('content-cpu', `<p style="color:red;">Error: ${data.cpu.error}</p>`);
        updateBadge('badge-cpu', 'Error', 'bad');
    } else if (data.cpu) {
        safeSetInnerHtml('content-cpu', `
            <p><strong>CPU:</strong> ${data.cpu.name}</p>
            <p><strong>Cores/Threads:</strong> ${data.cpu.cores} / ${data.cpu.threads}</p>
            <p><strong>Base Clock:</strong> ${data.cpu.base_clock_mhz} MHz</p>
            <p><strong>Current Usage:</strong> ${data.cpu.usage_percent}%</p>
            <hr/>
            <div id="cpu-bench-content">Waiting for benchmark...</div>
        `);
        updateBadge('badge-cpu', 'OK', 'good');
    }

    if(data.gpu && data.gpu.error) {
        safeSetInnerHtml('content-gpu', `<p style="color:red;">Error: ${data.gpu.error}</p>`);
        updateBadge('badge-gpu', 'Error', 'bad');
    } else if (data.gpu) {
        let gpuHtml = '';
        data.gpu.forEach((g, i) => {
            gpuHtml += `
                <p><strong>GPU ${i+1}:</strong> ${g.name}</p>
                <p>VRAM: ${g.vram_total_mb} MB</p>
                <p>Usage: ${g.usage_percent}% | Temp: ${g.temp_c}°C</p>
                <hr>
            `;
        });
        gpuHtml += '<div id="gpu-bench-content">Waiting for benchmark...</div>';
        safeSetInnerHtml('content-gpu', gpuHtml);
        updateBadge('badge-gpu', 'OK', 'good');
    }

    safeSetInnerHtml('content-ram', `
        <p><strong>Total RAM:</strong> ${data.ram ? (data.ram.total_gb || '?') : '?'} GB</p>
        <p><strong>Used Slots:</strong> ${data.ram ? (data.ram.slots_used || '?') : '?'} | <strong>Speed:</strong> ${data.ram ? (data.ram.speed_mhz || '?') : '?'} MHz</p>
        <p><strong>Dual Channel:</strong> ${data.ram ? (data.ram.dual_channel ? 'Yes' : 'No') : '?'}</p>
        <hr/>
        <div id="ram-bench-content">Waiting for benchmark...</div>
    `);

    let diskHtml = `<p><strong>C: Drive Capacity:</strong> ${data.disk ? (data.disk.c_drive_total_gb || '?') : '?'} GB Total (${data.disk ? (data.disk.c_drive_free_gb || '?') : '?'} GB Free)</p>`;
    diskHtml += '<hr/><div id="disk-bench-content">Waiting for benchmark...</div>';
    safeSetInnerHtml('content-disk', diskHtml);

    let batHtml = `<p>Battery present: ${data.battery ? (data.battery.present ? 'Yes' : 'No') : 'No'}</p>`;
    if(data.battery && data.battery.present) {
        batHtml += `
            ${generateTrafficLightHTML(data.battery.health_label)}
            <p><strong>Charge:</strong> ${data.battery.charge_percent}%</p>
            <p><strong>Wear Level:</strong> ${data.battery.wear_level_percent}%</p>
            <p><strong>Health:</strong> ${data.battery.health_label}</p>
        `;
        updateBadge('badge-battery', data.battery.health_label, data.battery.needs_replacement ? 'bad' : 'good');
    } else {
        updateBadge('badge-battery', 'No Battery', 'warn');
    }
    safeSetInnerHtml('content-battery', batHtml);
    
    let dispHtml = data.display && data.display.length > 0 ? data.display.map(d => `<p>Display: ${d.resolution} @ ${d.refresh_rate}Hz</p>`).join('') : '<p>Could not read display</p>';
    let netHtml = data.network && data.network.length > 0 ? data.network.map(n => `<p>Adapter: ${n.name} (WiFi 6: ${n.is_wifi6 ? 'Yes' : 'No'})</p>`).join('') : '<p>No active network adapters</p>';

    const tc = data.thermals || {};
    const cpuT = tc.cpu_temp_c ? `${tc.cpu_temp_c}°C` : '<span style="color:#888;">Could not read</span>';
    const gpuT = tc.gpu_temp_c ? `${tc.gpu_temp_c}°C` : '<span style="color:#888;">Could not read</span>';

    safeSetInnerHtml('content-thermals', `
        <h3>Live Thermal Readings</h3>
        <p>CPU Temperature: ${cpuT}</p>
        <p>GPU Temperature: ${gpuT}</p>
        <hr/>
        <h3>Display Data</h3>
        ${dispHtml}
        <h3>Network Interfaces</h3>
        ${netHtml}
    `);
    
    if(data.display && data.display.length > 0) {
        const resEl = document.getElementById('screenResSpan');
        const refEl = document.getElementById('screenRefSpan');
        if(resEl) resEl.innerText = `Resolution: ${data.display[0].resolution}`;
        if(refEl) refEl.innerText = `Refresh Rate: ${data.display[0].refresh_rate}Hz`;
    }
    updateBadge('badge-thermals', 'Details Parsed', 'good');
}

function renderCpuBench(data) {
    safeSetInnerHtml('cpu-bench-content', `
        ${generateTrafficLightHTML(data.health_label)}
        <p><strong>Stress Test Score:</strong> ${data.ops_per_second} ops/s</p>
        <p><strong>Throttling Detected:</strong> ${data.throttling_detected ? 'Yes' : 'No'}</p>
        <p><strong>Performance Label:</strong> ${data.health_label}</p>
    `);
    updateBadge('badge-cpu', data.health_label, data.health_label === "Degraded" ? 'bad' : 'good');
}

function renderGpuBench(data) {
    safeSetInnerHtml('gpu-bench-content', `
        ${generateTrafficLightHTML(data.health_label)}
        <p><strong>Compute Score:</strong> ${data.score}</p>
        <p><strong>Label:</strong> ${data.health_label}</p>
    `);
    updateBadge('badge-gpu', data.health_label, data.underperforming ? 'bad' : 'good');
}

function renderDiskBench(data) {
    safeSetInnerHtml('disk-bench-content', `
        ${generateTrafficLightHTML(data.health_label)}
        <p><strong>Write Speed:</strong> ${data.write_speed_mb_s} MB/s</p>
        <p><strong>Read Speed:</strong> ${data.read_speed_mb_s} MB/s</p>
        <p><strong>Type Label:</strong> ${data.health_label}</p>
    `);
    updateBadge('badge-disk', data.health_label, data.health_label.includes('Slow') ? 'bad' : 'good');
}

function renderRamBench(data) {
    safeSetInnerHtml('ram-bench-content', `
        ${generateTrafficLightHTML(data.health_label)}
        <p><strong>Bandwidth:</strong> ${data.bandwidth_gb_s} GB/s</p>
        <p><strong>Health:</strong> ${data.health_label}</p>
    `);
    updateBadge('badge-ram', data.health_label, 'good');
}

function updateBadge(id, text, type) {
    const b = document.getElementById(id);
    if(b) {
        b.innerText = text;
        b.className = `badge ${type}`;
    }
}

async function calculatePrice() {
    const btn = document.getElementById('generateValuationBtn');
    if(btn) {
        btn.disabled = true;
        btn.innerText = 'Analyzing...';
    }
    
    // Only count failures from Group A (.port-check) for deductions
    const failedPortsCount = document.querySelectorAll('.port-check:not(:checked)').length;
    const dispIssues = document.getElementById('chkDisplay').checked;

    const payload = {
        session_id: sessionId,
        system_info: scanData,
        benchmarks: benchData,
        manual_checks: {
            failed_ports: failedPortsCount,
            display_issues: dispIssues
        }
    };

    try {
        const response = await fetch('/api/price', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const res = await response.json();
        
        if (res.success) {
            renderValuationPrompt(res.data.valuation_prompt);
            updateChart(res.data.overall_health_score);
            calculateIntegrityVerdict(res.data.overall_health_score);
            
            const promptBox = document.getElementById('manualPrompt');
            if(promptBox) { promptBox.style.display = 'none'; }
        }
    } catch (err) {
        console.error("Valuation failed:", err);
        alert("Error contacting the diagnostic server.");
    } finally {
        if(btn) {
            btn.disabled = false;
            btn.innerText = 'Generate AI Valuation Prompt';
        }
    }
}

function copyPromptToClipboard() {
    const prompt = document.getElementById('valuationPrompt').value;
    navigator.clipboard.writeText(prompt);
    const btn = document.getElementById('copyPromptBtn');
    const oldText = btn.innerText;
    btn.innerText = '✅ Copied!';
    btn.classList.add('good');
    setTimeout(() => {
        btn.innerText = oldText;
        btn.classList.remove('good');
    }, 2000);
}

function openAIExternal() {
    window.open('https://chatgpt.com', '_blank');
}

function renderValuationPrompt(prompt) {
    const promptArea = document.getElementById('valuationPrompt');
    if(promptArea) {
        promptArea.value = prompt;
    }
    
    document.getElementById('copyPromptBtn').disabled = false;
    document.getElementById('openAIBtn').disabled = false;
}

function calculateIntegrityVerdict(score) {
    const box = document.getElementById('finalVerdictBox');
    const text = document.getElementById('verdictText');
    if(box) box.style.display = 'block';
    
    box.classList.remove('pop-animate');
    void box.offsetWidth; 
    box.classList.add('pop-animate');
    
    if(score >= 90) {
        text.innerText = "EXCELLENT INTEGRITY ✅";
        box.style.border = "4px solid #28a745";
        text.style.color = "#28a745";
    } else if(score >= 70) {
        text.innerText = "GOOD INTEGRITY ⚠️";
        box.style.border = "4px solid #ffc107";
        text.style.color = "#856404";
    } else if(score >= 40) {
        text.innerText = "FAIR / AGING ❌";
        box.style.border = "4px solid #fd7e14";
        text.style.color = "#fd7e14";
    } else {
        text.innerText = "POOR INTEGRITY 🚨";
        box.style.border = "4px solid #dc3545";
        text.style.color = "#dc3545";
    }
}

const colors = ['#ffffff', '#000000', '#ff0000', '#00ff00', '#0000ff'];
let currentColor = 0;
function runDisplayTest() {
    const overlay = document.getElementById('colorTestOverlay');
    overlay.style.display = 'block';
    currentColor = 0;
    
    overlay.onclick = () => {
        currentColor++;
        if(currentColor >= colors.length) {
            overlay.style.display = 'none';
        } else {
            overlay.style.backgroundColor = colors[currentColor];
        }
    };
    overlay.style.backgroundColor = colors[0];
}

function exportPDF() {
    window.print();
}

function exportHTML() {
    window.location.href = `/api/export/${sessionId}`;
}
