#!/usr/bin/env python3
import os
import glob
import datetime
import subprocess
import re
import sys
import argparse
import random
import tempfile

FALLBACK_PRINTER = "DeskJet_3630"
LOG_DIR = "/var/log/cups"
LOG_GLOB = "page_log*"
THRESHOLD_DAYS = 7

def get_last_print_time(printer_name, log_dir, log_glob):
    """Search all page_log* files (including rotated) for the most recent print."""
    last_print_time = None
    pattern = os.path.join(log_dir, log_glob)
    files = sorted(glob.glob(pattern))

    if not files:
        return None

    for log_file in files:
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    parts = line.split()
                    if not parts:
                        continue
                    if parts[0] == printer_name:
                        match = re.search(r'\[(.*?)]', line)
                        if match:
                            timestamp_str = match.group(1)
                            try:
                                dt = datetime.datetime.strptime(timestamp_str, "%d/%b/%Y:%H:%M:%S %z")
                                if last_print_time is None or dt > last_print_time:
                                    last_print_time = dt
                            except ValueError:
                                continue
        except PermissionError:
            print(f"Permission denied reading {log_file}.")
        except OSError as e:
            print(f"Warning: could not read {log_file}: {e}")

    return last_print_time

def get_default_printer():
    """Return the system default CUPS printer, or None."""
    try:
        result = subprocess.run(["lpstat", "-d"], capture_output=True, text=True, check=True)
        line = result.stdout.strip()
        prefix = "system default destination: "
        if line.startswith(prefix):
            name = line[len(prefix):].strip()
            if name:
                return name
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None

def generate_test_page_image(output_path):
    width = 595
    height = 842
    
    pat_w = 300
    pat_h = 50
    
    max_x = width - pat_w - 20
    max_y = height - pat_h - 20
    pos_x = random.randint(20, max_x)
    pos_y = random.randint(20, max_y)
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = f"Maintenance: {timestamp}"

    cmd = [
        "convert",
        "-size", f"{width}x{height}", "xc:white", 
        "(", 
            "-size", f"{pat_w//4}x{pat_h}", "xc:cyan", "xc:magenta", "xc:yellow", "xc:black", "+append",
            "+size", "-background", "white", "-fill", "black", "-pointsize", "12", 
            f"label:{label}", "-append",
        ")",
        "-geometry", f"+{pos_x}+{pos_y}", 
        "-composite",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating image: {e}")
        return False
    except FileNotFoundError:
        print("Error: 'convert' command (ImageMagick) not found.")
        return False

def print_test_page(printer_name):
    """Generate and send a maintenance test page to *printer_name*."""
    with tempfile.NamedTemporaryFile(suffix=".png", prefix="jorka_", delete=False) as tmp:
        temp_file = tmp.name

    try:
        print("Generating dynamic test page...")
        if not generate_test_page_image(temp_file):
            print("Failed to generate test page. Aborting.")
            return

        print(f"Sending test page to {printer_name} ...")
        try:
            result = subprocess.run(
                ["lp", "-d", printer_name, "-o", "media=A4", temp_file],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            job_id = "Unknown"
            match = re.search(r"request id is ([\w_-]+)", result.stdout)
            if match:
                job_id = match.group(1)

            print(f"✔ Test page sent successfully (Job ID: {job_id})")

        except subprocess.CalledProcessError as e:
            print(f"Failed to print: {e.stderr.strip()}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def _report_status(last_print, threshold_days):
    """Print a human-readable status summary — never triggers a print."""
    if last_print:
        now = datetime.datetime.now(last_print.tzinfo)
        delta = now - last_print
        print(f"Last print was on: {last_print}")
        print(f"Time elapsed:     {delta.days} days, {delta.seconds // 3600} hours ago")
        if delta.days >= threshold_days:
            print(f"Status:           MAINTENANCE DUE (threshold: {threshold_days} days)")
        else:
            days_left = threshold_days - delta.days
            print(f"Status:           OK — maintenance not needed yet ({days_left} day(s) until threshold)")
    else:
        print("Last print:       never (no CUPS log entries found)")
        print(f"Status:           MAINTENANCE DUE (threshold: {threshold_days} days)")


def main():
    parser = argparse.ArgumentParser(description="Printer maintenance script.")
    parser.add_argument("--force", action="store_true", help="Force print test page ignoring history.")
    parser.add_argument("--printer", type=str, help="CUPS Printer Name (Auto-detects default if omitted)")
    parser.add_argument("--days", type=int, default=THRESHOLD_DAYS, help="Days threshold")
    parser.add_argument(
        "--check", action="store_true", dest="check",
        help="Show last-print info and whether maintenance is due (no printing)",
    )
    parser.add_argument(
        "--status", action="store_true", dest="check",
        help=argparse.SUPPRESS,
    )

    args = parser.parse_args()

    printer_name = args.printer or get_default_printer() or FALLBACK_PRINTER

    if not printer_name:
        print("Error: Could not detect a default printer. Please specify one with --printer.")
        sys.exit(1)

    print(f"Printer: {printer_name}")

    if args.check:
        print(f"Checking CUPS logs for recent activity (threshold: {args.days} days)...")
        last_print = get_last_print_time(printer_name, LOG_DIR, LOG_GLOB)
        _report_status(last_print, args.days)
        return

    if args.force:
        print("Force mode enabled — skipping activity check.")
        print_test_page(printer_name)
        return

    print(f"Checking CUPS logs for recent activity (threshold: {args.days} days)...")
    last_print = get_last_print_time(printer_name, LOG_DIR, LOG_GLOB)

    if last_print:
        now = datetime.datetime.now(last_print.tzinfo)
        delta = now - last_print
        print(f"Last print was on: {last_print} ({delta.days} days ago)")

        if delta.days >= args.days:
            print(f"Printer not used for {delta.days} days. Initiating maintenance print.")
            print_test_page(printer_name)
        else:
            print("Printer used recently. No maintenance needed.")
    else:
        print("No print history found. Initiating maintenance print.")
        print_test_page(printer_name)

if __name__ == "__main__":
    main()
