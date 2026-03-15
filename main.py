from flask import Flask, request, jsonify, render_template
import xml.etree.ElementTree as ET
import threading

app = Flask(__name__)

# Сховище в пам'яті та замок для безпеки потоків
data_store = {
    "last_json": None,
    "last_xml_raw": None,
    "table_data": []  # Оброблений список для веб-сторінки
}
data_lock = threading.Lock()

def parse_xml(xml_string):
    """Конвертує XML у зручний список словників"""
    try:
        root = ET.fromstring(xml_string)
        lanes = []
        for idx, lane in enumerate(root.findall('lane'), 1):
            lane_dict = {
                "lane_id": f"lane{idx:02d}",
                "number": lane.find('number').text or "",
                "shots": lane.find('shots').text or "0",
                "flaps": [
                    lane.find('flap1').text,
                    lane.find('flap2').text,
                    lane.find('flap3').text,
                    lane.find('flap4').text,
                    lane.find('flap5').text
                ]
            }
            lanes.append(lane_dict)
        return lanes
    except Exception as e:
        print(f"XML Parse Error: {e}")
        return []

@app.route('/api/push', methods=['POST'])
def push_data():
    content_type = request.headers.get('Content-Type')
    
    with data_lock:
        if 'application/json' in content_type:
            raw_data = request.json
            data_store["last_json"] = raw_data
            # Трансформація JSON для таблиці
            table_results = []
            for key, val in raw_data.items():
                table_results.append({
                    "lane_id": key,
                    "number": val.get("number"),
                    "shots": val.get("shots"),
                    "flaps": [val["flaps"][f"flap{i}"] for i in range(1, 6)]
                })
            data_store["table_data"] = table_results
            
        elif 'application/xml' in content_type or 'text/xml' in content_type:
            raw_xml = request.data.decode('utf-8')
            data_store["last_xml_raw"] = raw_xml
            data_store["table_data"] = parse_xml(raw_xml)
            
        else:
            return "Unsupported Media Type", 415
            
    return "Data updated", 200

@app.route('/api/get', methods=['GET'])
def get_data():
    with data_lock:
        return jsonify({
            "json": data_store["last_json"],
            "xml": data_store["last_xml_raw"]
        })

@app.route('/')
def index():
    with data_lock:
        return render_template('index.html', results=data_store["table_data"])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
