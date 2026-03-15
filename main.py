from flask import Flask, request, jsonify, render_template
import xml.etree.ElementTree as ET
import threading
import os

app = Flask(__name__, template_folder='public', static_folder='public')

# Сховище в пам'яті для роздільних даних
data_store = {
    "json": None,
    "xml_raw": None,
    "table_data": []  # Спільний список для візуалізації на сайті
}
data_lock = threading.Lock()

def parse_xml_to_list(xml_string):
    try:
        root = ET.fromstring(xml_string)
        lanes = []
        for idx, lane in enumerate(root.findall('lane'), 1):
            lanes.append({
                "lane_id": f"lane{idx:02d}",
                "number": lane.find('number').text or "",
                "shots": lane.find('shots').text or "0",
                "flaps": [lane.find(f'flap{i}').text for i in range(1, 6)]
            })
        return lanes
    except Exception:
        return []

# --- JSON API ---
@app.route('/api/push/json', methods=['POST'])
def push_json():
    with data_lock:
        data = request.json
        data_store["json"] = data
        # Оновлюємо спільну таблицю для вебу
        data_store["table_data"] = [
            {
                "lane_id": k,
                "number": v.get("number"),
                "shots": v.get("shots"),
                "flaps": [v["flaps"][f"flap{i}"] for i in range(1, 6)]
            } for k, v in data.items()
        ]
    return "JSON updated", 200

@app.route('/api/get/json', methods=['GET'])
def get_json():
    with data_lock:
        return jsonify(data_store["json"] or {"status": "no data"})

# --- XML API ---
@app.route('/api/push/xml', methods=['POST'])
def push_xml():
    with data_lock:
        raw_xml = request.data.decode('utf-8')
        data_store["xml_raw"] = raw_xml
        # Оновлюємо спільну таблицю для вебу
        data_store["table_data"] = parse_xml_to_list(raw_xml)
    return "XML updated", 200

@app.route('/api/get/xml', methods=['GET'])
def get_xml():
    with data_lock:
        if data_store["xml_raw"]:
            return data_store["xml_raw"], 200, {'Content-Type': 'application/xml'}
        return "<status>no data</status>", 200, {'Content-Type': 'application/xml'}

# --- WEB UI ---
@app.route('/')
def index():
    with data_lock:
        return render_template('index.html', results=data_store["table_data"])

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
