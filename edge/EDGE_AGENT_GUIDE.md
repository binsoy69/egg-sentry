# EggSentry Edge Agent Guide

This guide covers:

- Setting up the edge agent environment
- Running the edge agent manually
- Running the live camera diagnostic
- Creating and managing the `systemd` service
- Stopping the service before diagnostics, then starting it again

All commands below assume a Raspberry Pi or Linux host.

## Repo Layout

Important paths in this repo:

- Edge agent script: `edge/agent.py`
- Camera diagnostic: `edge/camera_diagnostic.py`
- Edge config: `edge/config.json`
- Edge Python requirements: `edge/requirements.txt`
- Model path currently referenced by config: `models/counter-yolo26n_ncnn_model`

## 1. First-Time Setup

Run these commands from the Pi after cloning the repo:

```bash
cd ~/egg-sentry
sudo apt update
sudo apt install -y python3-pip python3-venv libgl1 libglib2.0-0
python3 -m venv edge/.venv
source edge/.venv/bin/activate
pip install --upgrade pip
pip install -r edge/requirements.txt
```

If you need to confirm the model directory exists:

```bash
cd ~/egg-sentry
ls -lah models
```

## 2. Configure the Edge Agent

The agent reads `edge/config.json` by default.

Open it:

```bash
cd ~/egg-sentry
nano edge/config.json
```

Review these fields:

- `backend_api_base_url`
- `device_id`
- `device_api_key`
- `capture_interval_seconds`
- `confidence_threshold`
- `model_path`

Quick check:

```bash
cd ~/egg-sentry
cat edge/config.json
```

## 3. Run the Edge Agent Manually

Use this when testing before enabling the service:

```bash
cd ~/egg-sentry
source edge/.venv/bin/activate
python edge/agent.py --config edge/config.json --source 0
```

Useful override example:

```bash
cd ~/egg-sentry
source edge/.venv/bin/activate
python edge/agent.py \
  --config edge/config.json \
  --source 0 \
  --interval 120 \
  --conf 0.50 \
  --heartbeat-interval 60
```

If you want an OpenCV preview while testing manually:

```bash
cd ~/egg-sentry
source edge/.venv/bin/activate
python edge/agent.py --config edge/config.json --source 0 --display
```

To stop a manual run:

```bash
Ctrl+C
```

## 4. Run the Camera Diagnostic

The diagnostic opens a live OpenCV preview window. Run it from a session that has access to a display.

Basic diagnostic command:

```bash
cd ~/egg-sentry
source edge/.venv/bin/activate
python edge/camera_diagnostic.py --config edge/config.json --source 0
```

Recommended diagnostic command for manual camera adjustment:

```bash
cd ~/egg-sentry
source edge/.venv/bin/activate
python edge/camera_diagnostic.py \
  --config edge/config.json \
  --source 0 \
  --width 1280 \
  --height 720 \
  --mirror \
  --infer-every 5
```

Diagnostic with a recorded video instead of a live camera:

```bash
cd ~/egg-sentry
source edge/.venv/bin/activate
python edge/camera_diagnostic.py \
  --config edge/config.json \
  --source vids/sample.mp4 \
  --loop-video \
  --track
```

Diagnostic controls:

- `q`: quit
- `g`: show or hide guides
- `d`: pause or resume detection
- `s`: save a snapshot into `edge/diagnostic_snapshots/`

## 5. Stop the Service Before Running Diagnostics

Do not run the live diagnostic while the edge service is already using the same camera.

Stop the service first:

```bash
sudo systemctl stop egg-sentry.service
```

Then run the diagnostic:

```bash
cd ~/egg-sentry
source edge/.venv/bin/activate
python edge/camera_diagnostic.py --config edge/config.json --source 0 --width 1280 --height 720 --mirror
```

When finished, start the service again:

```bash
sudo systemctl start egg-sentry.service
```

## 6. Create the systemd Service

Create the unit file:

```bash
sudo tee /etc/systemd/system/egg-sentry.service > /dev/null <<'EOF'
[Unit]
Description=EggSentry Edge Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/egg-sentry
ExecStart=/home/pi/egg-sentry/edge/.venv/bin/python /home/pi/egg-sentry/edge/agent.py --config /home/pi/egg-sentry/edge/config.json --source 0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

Reload `systemd` after creating or editing the unit:

```bash
sudo systemctl daemon-reload
```

Enable the service at boot:

```bash
sudo systemctl enable egg-sentry.service
```

Start the service now:

```bash
sudo systemctl start egg-sentry.service
```

## 7. systemd Commands

Check status:

```bash
sudo systemctl status egg-sentry.service
```

Start:

```bash
sudo systemctl start egg-sentry.service
```

Stop:

```bash
sudo systemctl stop egg-sentry.service
```

Restart:

```bash
sudo systemctl restart egg-sentry.service
```

Disable auto-start on boot:

```bash
sudo systemctl disable egg-sentry.service
```

Check recent logs:

```bash
sudo journalctl -u egg-sentry.service -n 100 --no-pager
```

Follow logs live:

```bash
sudo journalctl -u egg-sentry.service -f
```

## 8. Common Run Sequences

Start service on boot and run now:

```bash
sudo systemctl daemon-reload
sudo systemctl enable egg-sentry.service
sudo systemctl start egg-sentry.service
sudo systemctl status egg-sentry.service
```

Stop service, run diagnostic, then resume service:

```bash
sudo systemctl stop egg-sentry.service
cd ~/egg-sentry
source edge/.venv/bin/activate
python edge/camera_diagnostic.py --config edge/config.json --source 0 --width 1280 --height 720 --mirror
sudo systemctl start egg-sentry.service
sudo systemctl status egg-sentry.service
```

Manual agent run without `systemd`:

```bash
cd ~/egg-sentry
source edge/.venv/bin/activate
python edge/agent.py --config edge/config.json --source 0
```

## 9. Notes

- The edge agent prints JSON status output for each capture cycle.
- The diagnostic is interactive and requires a display because it uses `cv2.imshow(...)`.
- The agent camera source accepts a numeric camera index like `0` or a video file path.
- If you change the service file, always run `sudo systemctl daemon-reload` before restarting the service.
