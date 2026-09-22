import numpy as np
import datetime

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

        pressure_altitude = int(line[25:30]) if line[25:30].strip() else int(line[30:35])
        return lat, lon, pressure_altitude, time_str
    except ValueError:
        return None

def haversine_distance_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0)**2
    return R * (2 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a)))


def _time_difference_seconds(previous_time, current_time):
    previous = datetime.datetime.strptime(previous_time, '%H:%M:%S')
    current = datetime.datetime.strptime(current_time, '%H:%M:%S')
    difference = (current - previous).total_seconds()
    return difference if difference >= 0 else difference + 24 * 60 * 60


def find_max_altitude_gain(altitudes, times, max_gap_seconds=10):
    """Find the largest net altitude gain within a continuous track run."""
    if len(altitudes) < 2:
        return {
            'altitude_gain_m': 0,
            'altitude_start_m': 0,
            'altitude_end_m': 0,
            'altitude_start_time': '',
            'altitude_end_time': '',
            'altitude_duration_s': 0
        }

    best = None
    run_min_altitude = float(altitudes[0])
    run_min_index = 0

    for index in range(1, len(altitudes)):
        gap_seconds = _time_difference_seconds(times[index - 1], times[index])
        if gap_seconds > max_gap_seconds:
            run_min_altitude = float(altitudes[index])
            run_min_index = index
            continue

        altitude_gain = float(altitudes[index]) - run_min_altitude
        if altitude_gain > 0 and (best is None or altitude_gain > best['altitude_gain_m']):
            best = {
                'altitude_gain_m': round(altitude_gain, 2),
                'altitude_start_m': round(run_min_altitude, 2),
                'altitude_end_m': round(float(altitudes[index]), 2),
                'altitude_start_time': times[run_min_index],
                'altitude_end_time': times[index],
                'altitude_duration_s': round(
                    _time_difference_seconds(times[run_min_index], times[index]), 2
                )
            }

        if float(altitudes[index]) < run_min_altitude:
            run_min_altitude = float(altitudes[index])
            run_min_index = index

    return best or {
        'altitude_gain_m': 0,
        'altitude_start_m': 0,
        'altitude_end_m': 0,
        'altitude_start_time': '',
        'altitude_end_time': '',
        'altitude_duration_s': 0
    }


def find_fastest_altitude_loss(altitudes, times, window_seconds=3, max_gap_seconds=10):
    """Find the fastest altitude loss over an exact fixed-duration window."""
    empty_result = {
        'altitude_loss_rate_mps': 0,
        'altitude_loss_m': 0,
        'altitude_loss_start_time': '',
        'altitude_loss_end_time': '',
        'altitude_loss_duration_s': 0
    }
    if len(altitudes) < 2:
        return empty_result

    filtered_altitudes = np.asarray(altitudes, dtype=float).copy()
    for index in range(2, len(altitudes) - 2):
        gaps = [
            _time_difference_seconds(times[index - 1], times[index]),
            _time_difference_seconds(times[index], times[index + 1]),
            _time_difference_seconds(times[index - 2], times[index - 1]),
            _time_difference_seconds(times[index + 1], times[index + 2])
        ]
        if max(gaps) <= max_gap_seconds:
            filtered_altitudes[index] = np.median(altitudes[index - 2:index + 3])

    elapsed_seconds = [0.0]
    for index in range(1, len(times)):
        elapsed_seconds.append(
            elapsed_seconds[-1] + _time_difference_seconds(times[index - 1], times[index])
        )
    elapsed_seconds = np.array(elapsed_seconds)

    # Mark the last point reachable without crossing a recording gap.
    run_end = np.full(len(times), len(times) - 1, dtype=int)
    for index in range(len(times) - 2, -1, -1):
        if _time_difference_seconds(times[index], times[index + 1]) > max_gap_seconds:
            run_end[index] = index
        else:
            run_end[index] = run_end[index + 1]

    best = None
    for start in range(len(altitudes) - 1):
        target_time = elapsed_seconds[start] + window_seconds
        end = int(np.searchsorted(elapsed_seconds, target_time, side='left'))
        if end >= len(altitudes) or end > run_end[start] or end == start:
            continue

        previous_time = elapsed_seconds[end - 1]
        next_time = elapsed_seconds[end]
        if next_time == previous_time:
            continue
        fraction = (target_time - previous_time) / (next_time - previous_time)
        target_altitude = (
            filtered_altitudes[end - 1]
            + fraction * (filtered_altitudes[end] - filtered_altitudes[end - 1])
        )
        altitude_loss = filtered_altitudes[start] - target_altitude
        if altitude_loss <= 0:
            continue

        rate = altitude_loss / window_seconds
        if best is None or rate > best['altitude_loss_rate_mps']:
            end_datetime = datetime.datetime.strptime(
                times[start], '%H:%M:%S'
            ) + datetime.timedelta(seconds=window_seconds)
            best = {
                'altitude_loss_rate_mps': round(rate, 2),
                'altitude_loss_m': round(altitude_loss, 2),
                'altitude_loss_start_time': times[start],
                'altitude_loss_end_time': end_datetime.strftime('%H:%M:%S'),
                'altitude_loss_duration_s': window_seconds
            }

    return best or empty_result


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
    angles = np.unwrap(np.arctan2(y - center_y, x - center_y))
    return {
        'center_x': float(center_x),
        'center_y': float(center_y),
        'radius_m': radius,
        'max_error_m': float(errors.max()),
        'rms_error_m': float(np.sqrt(np.mean(errors**2))),
        'angular_span_deg': float(np.degrees(np.max(angles) - np.min(angles)))
    }


def find_circular_segment(
    X, Y, lats, lons, times, max_circle_deviation_m=5.0,
    min_circle_angle_deg=180.0, max_circle_radius_m=5000.0
):
    """Find the longest track window that stays close to a fitted circle."""
    n = len(X)
    if n < 8:
        return {
            'circular_arc_length_m': 0,
            'circle_radius_m': 0,
            'circle_center': None,
            'circle_max_error_m': 0,
            'circle_rms_error_m': 0,
            'circle_angular_span_deg': 0,
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
            if fit is None:
                continue
            if fit['max_error_m'] > max_circle_deviation_m:
                continue
            if fit['radius_m'] > max_circle_radius_m:
                continue
            if fit['angular_span_deg'] < min_circle_angle_deg:
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
                    'circle_angular_span_deg': round(fit['angular_span_deg'], 2),
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
        'circle_angular_span_deg': 0,
        'circle_closeness_pct': 0,
        'circle_start_time': '',
        'circle_end_time': '',
        'circular_segment_coords': []
    }

def analyze_igc_track(file_path, max_dev_meters=3.0, max_circle_deviation_m=50.0, min_circle_angle_deg=180.0):
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
    altitudes = np.array([pt[2] for pt in coords])
    times = [pt[3] for pt in coords]
    n = len(coords)

    # Total distance along track
    step_distances = haversine_distance_meters(lats[:-1], lons[:-1], lats[1:], lons[1:])
    total_track_length_m = np.sum(step_distances)

    # Local Tangential Projection to meters (XY plane)
    R = 6371000.0
    mean_lat = np.mean(lats)
    mean_lon = np.mean(lons)
    lat0_rad, lon0_rad = np.radians(mean_lat), np.radians(mean_lon)
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
        'full_track_times': times,
        'origin_lat': mean_lat,
        'origin_lon': mean_lon,
        'straight_segment_coords': []
    }

    best.update(find_max_altitude_gain(altitudes, times, max_gap_seconds=10))
    best.update(find_fastest_altitude_loss(altitudes, times, window_seconds=3, max_gap_seconds=10))

    # Pass through the parameters from analyze_igc_track to find_circular_segment
    best.update(find_circular_segment(
        X, Y, lats, lons, times, max_circle_deviation_m=max_circle_deviation_m, min_circle_angle_deg=min_circle_angle_deg))

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