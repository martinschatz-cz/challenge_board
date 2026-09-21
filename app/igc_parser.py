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


def fit_circle(points):
    """Fit a circle to XY points and return its center, radius, and errors."""
    if len(points) < 3:
        return None

    x = points[:, 0]
    y = points[:, 1]
    matrix = np.column_stack((2.0 * x, 2.0 * y, np.ones(len(points))))
    target = x**2 + y**2

    try:
        center_x, center_y, constant = np.linalg.lstsq(matrix, target, rcond=None)[0]
    except np.linalg.LinAlgError:
        return None

    radius_squared = constant + center_x**2 + center_y**2
    if radius_squared <= 0:
        return None

    radius = float(np.sqrt(radius_squared))
    radial_distances = np.hypot(x - center_x, y - center_y)
    errors = np.abs(radial_distances - radius)
    return {
        'center_x': float(center_x),
        'center_y': float(center_y),
        'radius_m': radius,
        'max_error_m': float(errors.max()),
        'rms_error_m': float(np.sqrt(np.mean(errors**2)))
    }


def find_circular_segment(X, Y, lats, lons, times, max_circle_deviation_m=20.0):
    """Find the longest track window that stays close to a fitted circle."""
    n = len(X)
    if n < 8:
        return {
            'circular_arc_length_m': 0,
            'circle_radius_m': 0,
            'circle_center': None,
            'circle_max_error_m': 0,
            'circle_rms_error_m': 0,
            'circle_closeness_pct': 0,
            'circle_start_time': '',
            'circle_end_time': '',
            'circular_segment_coords': []
        }

    # Keep the quadratic window search responsive for high-frequency IGC logs.
    sample_step = max(1, int(np.ceil(n / 1200)))
    search_indices = np.arange(0, n, sample_step)
    if search_indices[-1] != n - 1:
        search_indices = np.append(search_indices, n - 1)

    best = None
    for start_pos in range(0, len(search_indices) - 7, 3):
        start = search_indices[start_pos]
        for end_pos in range(start_pos + 7, len(search_indices), 3):
            end = search_indices[end_pos]
            fit = fit_circle(np.column_stack((X[start:end + 1], Y[start:end + 1])))
            if fit is None or fit['max_error_m'] > max_circle_deviation_m:
                continue

            arc_length = float(np.sum(haversine_distance_meters(
                lats[start:end], lons[start:end], lats[start + 1:end + 1], lons[start + 1:end + 1])))
            if best is None or arc_length > best['circular_arc_length_m']:
                closeness = max(0.0, 100.0 * (1.0 - fit['rms_error_m'] / fit['radius_m']))
                best = {
                    'circular_arc_length_m': round(arc_length, 2),
                    'circle_radius_m': round(fit['radius_m'], 2),
                    'circle_center': (round(fit['center_y'], 2), round(fit['center_x'], 2)),
                    'circle_max_error_m': round(fit['max_error_m'], 2),
                    'circle_rms_error_m': round(fit['rms_error_m'], 2),
                    'circle_closeness_pct': round(closeness, 2),
                    'circle_start_time': times[start],
                    'circle_end_time': times[end],
                    'circular_segment_coords': list(zip(lats[start:end + 1], lons[start:end + 1]))
                }

    return best or {
        'circular_arc_length_m': 0,
        'circle_radius_m': 0,
        'circle_center': None,
        'circle_max_error_m': 0,
        'circle_rms_error_m': 0,
        'circle_closeness_pct': 0,
        'circle_start_time': '',
        'circle_end_time': '',
        'circular_segment_coords': []
    }

def analyze_igc_track(file_path, max_dev_meters=3.0, max_circle_deviation_m=20.0):
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

    best.update(find_circular_segment(
        X, Y, lats, lons, times, max_circle_deviation_m=max_circle_deviation_m))

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