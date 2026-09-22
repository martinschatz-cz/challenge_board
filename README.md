# challenge_board

A small web app for a gliding competition where pilots upload IGC flight logs and the system ranks them by the longest straight section of their track.

## What this project does

The app is designed around a simple idea: a glider pilot uploads an IGC file, the program reads the recorded GPS points, and it finds the longest segment of the flight that can be considered a near-straight line.

It then stores the result in a leaderboard and shows the track and the winning straight segment on a map.

This is useful for soaring and competition-style challenges where the goal is not just total distance, but the most impressive straight flight segment.

## Main features

- Upload IGC files through a Streamlit interface
- Parse GPS position records from the IGC format
- Calculate total flight distance, the longest straight segment, and the longest circular segment
- Accept a “maximum deviation tolerance” to control how strict the straightness check is
- Save leaderboard results to SQLite
- Display the ranking in a table
- Visualize the full route and the detected straight segment on a map
- Estimate circular-track quality using radial error and a closeness percentage

## How it works

### 1. IGC parsing
The parser reads lines that start with B, which are standard IGC position records. For each one it extracts:

- time
- latitude
- longitude
- altitude

The coordinates are converted from IGC format into decimal degrees so they can be processed numerically.

### 2. Distance calculation
The app uses haversine distance to compute real-world distances between consecutive GPS points. This gives the total path length of the track.

### 3. Straight-line detection
The analysis then projects the flight into a local planar coordinate system and checks sliding windows of points. For each segment, it measures how far the surrounding points deviate from the straight-line axis.

If the maximum deviation stays below the configured tolerance, the segment is treated as a valid straight track. The longest such segment becomes the winner for that flight.

Circular detection fits a circle to sliding windows of the projected track. A window is accepted when its maximum radial error is below the selected tolerance. The result reports the fitted radius, maximum and RMS radial error, and a closeness percentage based on RMS error relative to the radius.

### 4. Leaderboard
The app stores each submission in a SQLite database and orders the results by straight-line length in descending order.

Circular detections are stored as a separate `circle_track` challenge and ranked by circular arc length.

### 5. Visualization
The latest uploaded flight is shown on a Folium map:

- blue line for the whole track
- red line for the longest straight segment
- green line for the longest circular segment
- green and red markers for the segment start and end

## Project structure

- app/main.py — Streamlit frontend, file upload flow, SQLite database, leaderboard UI, map rendering
- app/igc_parser.py — IGC parsing and track geometry analysis
- data/ — folder for uploaded IGC files and the local SQLite database
- docker-compose.yml — Docker setup for running the app
- Dockerfile — container definition
- pixi.toml — dependency and task configuration for local development

## Local development

This project uses Pixi for dependency management.

### Install dependencies

```bash
pixi install
```

### Run the app

```bash
pixi run start
```

Then open the app in a browser at:

```text
http://localhost:8501
```

## Docker run

You can also run the app with Docker:

```bash
docker compose up --build
```

The app will be exposed on port 8501.

## Notes

- The app stores the leaderboard in the local file data/leaderboard.db.
- Uploaded IGC files are saved in the data directory as well.
- The detection logic depends on the selected maximum deviation tolerance; a smaller value makes the straight segment stricter.

## Summary

This is a lightweight flight-analysis competition app for soaring enthusiasts. It turns raw IGC logs into a leaderboard based on the longest clean straight track, while also giving a visual interpretation of the flight path.

