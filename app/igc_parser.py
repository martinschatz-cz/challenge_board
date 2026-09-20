import numpy as np

def parse_igc_b_record(line):
    if len(line) < 35 or line[0] != 'B':
        return None
    try:
        time_str = f"{line[1:3]}:{line[3:5]}:{line[5:7]}"
        lat_deg, lat_min = float(line[7:9]), float(line[9:14]) / 1000.0
        lat = lat_deg + (lat_min / 60.0)
        if line[14] == 'S': lat = -lat
            
        lon_deg, lon_min = float(line[15:18]), float(line[18:23]) / 1000.0
        lon = lon_deg + (lon_min / 60.0)
        if line[23] == 'W': lon = -lon
            
        alt_gps = int(line[30:35]) if len(line) >= 35 else 0
        return lat, lon, alt_gps, time_str
    except ValueError:
        return None

def haversine_distance_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    
    a = np.sin(dphi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0)**2
    return R * (2 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a)))

def analyze_igc_track(file_path, max_dev_meters=3.0):
    coords = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parsed = parse_igc_b_record(line.strip())
            if parsed:
                coords.append(parsed)
                
    if not coords:
        return None

    lats = np.array([pt[0] for pt in coords])
    lons = np.array([pt[1] for pt in coords])
    times = [pt[3] for pt in coords]
    n = len(coords)

    # Total distance along track
    step_distances = haversine_distance_meters(lats[:-1], lons[:-1], lats[1:], lons[1:])
    total_track_length_m = np.sum(step_distances)

    # Local Tangential Projection to meters (XY plane)
    R = 6371000.0
    lat0_rad, lon0_rad = np.radians(np.mean(lats)), np.radians(np.mean(lons))
    X = R * (np.radians(lons) - lon0_rad) * np.cos(lat0_rad)
    Y = R * (np.radians(lats) - lat0_rad)

    best = {
        'total_track_length_km': round(total_track_length_m / 1000.0, 2),
        'straight_displacement_m': 0,
        'segment_path_length_m': 0,
        'start_time': '',
        'end_time': '',
        'max_dev_m': 0,
        'rms_dev_m': 0,
        'full_track_coords': list(zip(lats, lons)),
        'straight_segment_coords': []
    }

    # Sliding window evaluation
    for start in range(n):
        for end in range(start + 5, n):
            p1 = np.array([X[start], Y[start]])
            p2 = np.array([X[end], Y[end]])
            vec = p2 - p1
            seg_len = np.linalg.norm(vec)
            
            if seg_len == 0:
                continue
                
            pts = np.column_stack((X[start:end+1], Y[start:end+1])) - p1
            proj = np.outer(np.dot(pts, vec) / (seg_len**2), vec)
            devs = np.linalg.norm(pts - proj, axis=1)
            
            max_d = devs.max()
            if max_d <= max_dev_meters:
                if seg_len > best['straight_displacement_m']:
                    best.update({
                        'straight_displacement_m': round(seg_len, 2),
                        'segment_path_length_m': round(np.sum(step_distances[start:end]), 2),
                        'start_time': times[start],
                        'end_time': times[end],
                        'max_dev_m': round(max_d, 2),
                        'rms_dev_m': round(np.sqrt(np.mean(devs**2)), 2),
                        'straight_segment_coords': list(zip(lats[start:end+1], lons[start:end+1]))
                    })
            else:
                break

    return best