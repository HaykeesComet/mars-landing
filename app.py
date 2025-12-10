from flask import Flask, jsonify, request, render_template_string
import time
from mars_landing import MarsLandingFuelSystem

app = Flask(__name__)

SCENARIOS = {
  "nominal": {"name": "Nominal Operations", "initialFuel": 853, "phase": "constant_deceleration", "altitude": 2000, "velocity": 45, "fuelDelta": -3.0},
  "anomalous": {"name": "Thruster Leak", "initialFuel": 627, "phase": "constant_deceleration", "altitude": 1200, "velocity": 38, "fuelDelta": -7.0},
  "critical": {"name": "Critical Shortage", "initialFuel": 178, "phase": "final_approach", "altitude": 450, "velocity": 12, "fuelDelta": -3.0},
  "emergency": {"name": "Depletion Imminent", "initialFuel": 118, "phase": "landing", "altitude": 95, "velocity": 3, "fuelDelta": -6.0},
}

state = {"system": None, "scenario": "nominal", "is_running": False, "tick": 0}

def init_system(key):
  s = SCENARIOS[key]
  sys = MarsLandingFuelSystem(initial_fuel=s["initialFuel"], mission_phase=s["phase"])
  sys.altitude = s["altitude"]
  sys.velocity = s["velocity"]
  state["system"] = sys
  state["tick"] = 0

@app.route("/")
def index():
  html = """
  <!doctype html>
  <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Mars Landing Fuel Management (Python)</title>
      <style>
        body{background:#0f172a;color:#fff;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;margin:0}
        .container{max-width:1120px;margin:0 auto;padding:24px}
        .card{background:#1f2937;border:1px solid #334155;border-radius:12px;padding:24px}
        .grid{display:grid;gap:16px}
        .grid-4{grid-template-columns:repeat(4,minmax(0,1fr))}
        .grid-3{grid-template-columns:repeat(3,minmax(0,1fr))}
        .btn{border:none;border-radius:10px;padding:12px 16px;font-weight:600;cursor:pointer}
        .btn-green{background:#16a34a}
        .btn-green:hover{background:#15803d}
        .btn-red{background:#dc2626}
        .btn-red:hover{background:#b91c1c}
        .btn-gray{background:#374151}
        .btn-gray:hover{background:#4b5563}
        .badge{display:inline-block;padding:6px 10px;border-radius:8px;font-weight:600}
        .status-nominal{border:2px solid #22c55e;background:#052e16;color:#86efac}
        .status-caution{border:2px solid #f59e0b;background:#3b2900;color:#fde68a}
        .status-critical{border:2px solid #ef4444;background:#450a0a;color:#fca5a5}
        .title{font-size:28px;font-weight:800;text-align:center;margin-bottom:8px}
        .subtitle{color:#94a3b8;text-align:center;margin-bottom:24px}
        .label{font-size:12px;color:#94a3b8}
        .value{font-size:22px;font-weight:700}
        .warnings{border-color:#ef4444}
        .recs{border-color:#3b82f6}
        .flex{display:flex;gap:12px}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="title">Mars Landing Fuel Management System</div>
        <div class="subtitle">Real-time fuel monitoring during powered descent (Python)</div>

        <div class="card" style="margin-bottom:16px">
          <div style="font-size:18px;font-weight:700;margin-bottom:12px">Test Scenarios</div>
          <div class="grid grid-4" id="scenarios"></div>
          <div class="flex" style="margin-top:12px">
            <button id="toggle" type="button" class="btn btn-green" onclick="handleToggle()">▶ Start Monitoring</button>
            <button type="button" class="btn btn-gray" onclick="handleReset()">🔄 Reset</button>
          </div>
        </div>

        <div id="statusPanel" class="card status-critical" style="margin-bottom:16px;display:none"></div>

        <div class="grid grid-3" style="margin-bottom:16px">
          <div class="card">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px"><div style="color:#60a5fa">⛽</div><div style="font-weight:700">Fuel State</div></div>
            <div class="grid" style="gap:8px">
              <div><div class="label">Current Fuel</div><div class="value" id="currentFuel">—</div></div>
              <div><div class="label">Required Fuel</div><div class="value" id="requiredFuel">—</div></div>
              <div><div class="label">Fuel Margin</div><div class="value" id="fuelMargin">—</div></div>
              <div><div class="label">Est. at Touchdown</div><div class="value" id="fuelTouchdown">—</div></div>
            </div>
          </div>
          <div class="card">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px"><div style="color:#a78bfa">📈</div><div style="font-weight:700">Performance</div></div>
            <div class="grid" style="gap:8px">
              <div><div class="label">Burn Rate</div><div class="value" id="burnRate">—</div></div>
              <div><div class="label">Deviation</div><div class="value" id="deviation">—</div></div>
              <div><div class="label">Anomaly Detected</div><div class="value" id="anomaly">—</div></div>
              <div><div class="label">Prediction Confidence</div><div class="value" id="confidence">—</div></div>
            </div>
          </div>
          <div class="card">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px"><div style="color:#fb923c">🧭</div><div style="font-weight:700">Safety Metrics</div></div>
            <div class="grid" style="gap:8px">
              <div><div class="label">Time to Depletion</div><div class="value" id="timeRemaining">—</div></div>
              <div><div class="label">Abort Capable</div><div class="value" id="abort">—</div></div>
              <div><div class="label">Altitude</div><div class="value" id="altitude">—</div></div>
              <div><div class="label">Velocity</div><div class="value" id="velocity">—</div></div>
            </div>
          </div>
        </div>

        <div class="grid" style="grid-template-columns:repeat(2,minmax(0,1fr))" id="alerts"></div>
      </div>
      <script>
        const scenarios = {{ scenarios|tojson }}
        const scEl = document.getElementById('scenarios')
        const statusPanel = document.getElementById('statusPanel')
        const alertsEl = document.getElementById('alerts')
        const toggleBtn = document.getElementById('toggle')
        let polling = null
        let isRunning = false

        function renderScenarios(selected){
          scEl.innerHTML = ''
          Object.entries(scenarios).forEach(([key, s]) => {
            const b = document.createElement('button')
            b.className = 'btn btn-gray'
            b.textContent = s.name + ' (' + s.initialFuel + ' kg)'
            if (selected === key) b.style.border = '2px solid #a78bfa'
            b.type = 'button'
            b.onclick = () => handleScenario(key)
            scEl.appendChild(b)
          })
        }

        function handleScenario(key){
          // keep current run state; just switch scenario
          renderScenarios(key)
          fetch('/scenario', {method:'POST', headers:{'Content-Type':'application/json','Accept':'application/json'}, cache:'no-store', body: JSON.stringify({key})})
            .then(()=>updateOnce())
            .catch(()=>updateOnce())
        }

        function handleToggle(){
          const path = isRunning ? '/pause' : '/start'
          // optimistic UI update
          isRunning = !isRunning
          toggleBtn.textContent = isRunning ? '⏸ Pause Monitoring' : '▶ Start Monitoring'
          setPolling(isRunning)
          fetch(path, {method:'POST', headers:{'Accept':'application/json'}, cache:'no-store'})
            .then(()=>updateOnce())
            .catch(()=>updateOnce())
        }

        function handleReset(){
          isRunning = false
          toggleBtn.textContent = '▶ Start Monitoring'
          setPolling(false)
          fetch('/reset', {method:'POST', headers:{'Accept':'application/json'}, cache:'no-store'})
            .then(()=>window.location.reload())
            .catch(()=>window.location.reload())
        }

        function setPolling(run){
          if (polling) { clearInterval(polling); polling = null }
          if (run) { polling = setInterval(updateOnce, 500) }
        }

        function updateUI(d){
          renderScenarios(d.selectedScenario)
          isRunning = d.is_running
          toggleBtn.textContent = isRunning ? '⏸ Pause Monitoring' : '▶ Start Monitoring'
          setPolling(isRunning)
          if (!d.status) return
          statusPanel.style.display = 'block'
          const cls = d.status.status === 'NOMINAL' ? 'card status-nominal' : d.status.status === 'CAUTION' ? 'card status-caution' : 'card status-critical'
          statusPanel.className = cls
          statusPanel.innerHTML = '<div style="display:flex;justify-content:space-between"><div><div style="font-size:22px;font-weight:800">System Status: <span>' + d.status.status + '</span></div><div class="label">Phase: ' + d.status.mission_phase.toUpperCase().replaceAll('_',' ') + '</div></div><div style="text-align:right"><div class="label">Last Update</div><div class="value">' + d.status.timestamp + '</div></div></div>'
          document.getElementById('currentFuel').textContent = d.status.current_fuel.toFixed(1) + ' kg'
          document.getElementById('requiredFuel').textContent = d.status.required_fuel.toFixed(1) + ' kg'
          document.getElementById('fuelMargin').textContent = (d.status.fuel_margin >= 0 ? '+' : '') + d.status.fuel_margin.toFixed(1) + ' kg'
          document.getElementById('fuelTouchdown').textContent = d.status.fuel_at_touchdown.toFixed(1) + ' kg'
          document.getElementById('burnRate').textContent = d.status.burn_rate.toFixed(2) + ' kg/s'
          document.getElementById('deviation').textContent = (d.status.burn_rate_deviation >= 0 ? '+' : '') + d.status.burn_rate_deviation.toFixed(1) + '%'
          document.getElementById('anomaly').textContent = d.status.anomaly_detected ? 'YES' : 'NO'
          document.getElementById('confidence').textContent = d.status.confidence.toFixed(1) + '%'
          document.getElementById('timeRemaining').textContent = (d.status.time_remaining === Infinity ? '∞' : d.status.time_remaining.toFixed(1) + 's')
          document.getElementById('abort').textContent = d.status.abort_capable ? 'YES' : 'NO'
          document.getElementById('altitude').textContent = d.status.altitude.toFixed(0) + ' m'
          document.getElementById('velocity').textContent = d.status.velocity.toFixed(0) + ' m/s'
          alertsEl.innerHTML = ''
          if (d.status.warnings.length){
            const w = document.createElement('div')
            w.className = 'card warnings'
            w.innerHTML = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px"><div style="color:#ef4444">⚠</div><div style="font-weight:700;color:#ef4444">Warnings</div></div>' + d.status.warnings.map(x=>'<div style="display:flex;gap:8px;margin-bottom:6px"><span style="color:#ef4444">⚠</span><span>'+x+'</span></div>').join('')
            alertsEl.appendChild(w)
          }
          if (d.status.recommendations.length){
            const r = document.createElement('div')
            r.className = 'card recs'
            r.innerHTML = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px"><div style="color:#3b82f6">→</div><div style="font-weight:700;color:#3b82f6">Recommendations</div></div>' + d.status.recommendations.map(x=>'<div style="display:flex;gap:8px;margin-bottom:6px"><span style="color:#3b82f6">→</span><span>'+x+'</span></div>').join('')
            alertsEl.appendChild(r)
          }
        }

        function updateOnce(){
          const ts = Date.now()
          fetch('/status?ts='+ts, {cache:'no-store'})
            .then(r=>r.json())
            .then(updateUI)
        }

        updateOnce()
      </script>
    </body>
  </html>
  """
  return render_template_string(html, scenarios=SCENARIOS)

@app.route("/start", methods=["POST"])
def start():
  state["is_running"] = True
  return jsonify({"ok": True})

@app.route("/pause", methods=["POST"])
def pause():
  state["is_running"] = False
  return jsonify({"ok": True})

@app.route("/reset", methods=["POST"])
def reset():
  init_system(state["scenario"])
  state["is_running"] = False
  return jsonify({"ok": True})

@app.route("/scenario", methods=["POST"])
def scenario():
  data = request.get_json(silent=True) or {}
  key = data.get("key", "nominal")
  if key not in SCENARIOS:
    key = "nominal"
  prev_running = state.get("is_running", False)
  state["scenario"] = key
  init_system(key)
  state["is_running"] = prev_running
  return jsonify({"ok": True})

@app.route("/status")
def status():
  if state["system"] is None:
    init_system(state["scenario"])
  s = SCENARIOS[state["scenario"]]
  sys = state["system"]
  if state["is_running"]:
    sys.update_sensors(fuel_delta=s["fuelDelta"], altitude_delta=-50, velocity_delta=-2)
  st = sys.monitor_cycle()
  state["tick"] += 1
  return jsonify({"is_running": state["is_running"], "selectedScenario": state["scenario"], "status": st})

@app.route("/health")
def health():
  return jsonify({"status": "ok"})

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=8000)
