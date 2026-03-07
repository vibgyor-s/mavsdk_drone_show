#!/usr/bin/env python3
"""One-time migration script: convert config/swarm CSV files to JSON."""
import csv, json, sys, os, glob

def csv_to_config_json(csv_path):
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        drones = []
        for row in reader:
            drone = {}
            for k, v in row.items():
                k = k.strip()
                if k in ('hw_id', 'pos_id', 'mavlink_port', 'baudrate'):
                    drone[k] = int(v) if v.strip() else 0
                else:
                    drone[k] = v.strip()
            drones.append(drone)
    return {"version": 1, "drones": drones}

def csv_to_swarm_json(csv_path):
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        assignments = []
        for row in reader:
            a = {}
            for k, v in row.items():
                k = k.strip()
                if k in ('hw_id', 'follow'):
                    a[k] = int(v) if v.strip() else 0
                elif k == 'body_coord':
                    a['frame'] = 'body' if (v.strip() and int(v)) else 'ned'
                elif k == 'offset_n':
                    a['offset_x'] = float(v) if v.strip() else 0.0
                elif k == 'offset_e':
                    a['offset_y'] = float(v) if v.strip() else 0.0
                elif k == 'offset_alt':
                    a['offset_z'] = float(v) if v.strip() else 0.0
                else:
                    a[k] = v.strip()
            assignments.append(a)
    return {"version": 1, "assignments": assignments}

def convert(csv_path, converter):
    json_path = csv_path.rsplit('.csv', 1)[0] + '.json'
    data = converter(csv_path)
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    key = 'drones' if 'drones' in data else 'assignments'
    print(f"  {csv_path} -> {json_path} ({len(data[key])} entries)")
    return json_path

if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print("Converting config files...")
    for name in ['config.csv', 'config_sitl.csv']:
        path = os.path.join(base, name)
        if os.path.exists(path):
            convert(path, csv_to_config_json)

    print("Converting swarm files...")
    for name in ['swarm.csv', 'swarm_sitl.csv']:
        path = os.path.join(base, name)
        if os.path.exists(path):
            convert(path, csv_to_swarm_json)

    print("Converting resource templates...")
    for csv_path in sorted(glob.glob(os.path.join(base, 'resources', 'config_*.csv'))):
        convert(csv_path, csv_to_config_json)
    for csv_path in sorted(glob.glob(os.path.join(base, 'resources', 'swarm_*.csv'))):
        convert(csv_path, csv_to_swarm_json)

    print("\nDone. Verify JSON files, then delete old CSVs.")
