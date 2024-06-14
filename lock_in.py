#!/usr/bin/env python3

import argparse
import validators
import subprocess
import os
from datetime import datetime, timedelta
import logging

xdg_data_home = os.getenv('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
log_dir = os.path.join(xdg_data_home, 'lockin')
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, 'lockin.log')

logging.basicConfig(filename=log_file_path, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def usage():
    print("Usage: lockin -t number m/h/d/w -s site")
    print("       lockin -ls")
    print("       lockin -u site")
    print("       lockin -u all")
    exit(1)

def calculate_duration(number, unit):
    if unit == 'm':
        return timedelta(minutes=number)
    elif unit == 'h':
        return timedelta(hours=number)
    elif unit == 'd':
        return timedelta(days=number)
    elif unit == 'w':
        return timedelta(weeks=number)
    else:
        raise ValueError("Invalid time unit")

def validate_url(site):
    if not validators.domain(site):
        logging.error(f"Invalid site: {site}")
        print(f"Invalid site: {site}")
        exit(1)

def list_blocked_sites():
    print("Sites blocked by this tool:")
    try:
        with open("/etc/hosts", "r") as hosts_file:
            lines = hosts_file.readlines()
            for line in lines:
                if "# managed by lockin" in line:
                    print(line.split()[1])
    except Exception as e:
        logging.error(f"Failed to list blocked sites: {e}")
        print(f"Failed to list blocked sites: {e}")

def manual_unblock_site(site):
    try:
        subprocess.run(["sudo", "sed", "-i", f"/127.0.0.1 {site} # managed by lockin/d", "/etc/hosts"], check=True)
        subprocess.run(["sudo", "sed", "-i", f"/127.0.0.1 www.{site} # managed by lockin/d", "/etc/hosts"], check=True)
        logging.info(f"Unblocked {site}")
        print(f"Unblocked {site}")
    except Exception as e:
        logging.error(f"Failed to unblock site {site}: {e}")
        print(f"Failed to unblock site {site}: {e}")

def unblock_all_sites():
    try:
        subprocess.run(["sudo", "sed", "-i", "/# managed by lockin/d", "/etc/hosts"], check=True)
        logging.info("Unblocked all sites managed by lockin")
        print("Unblocked all sites managed by lockin")
    except Exception as e:
        logging.error(f"Failed to unblock all sites: {e}")
        print(f"Failed to unblock all sites: {e}")

def is_site_blocked(site):
    try:
        with open("/etc/hosts", "r") as hosts_file:
            lines = hosts_file.readlines()
            for line in lines:
                if f"127.0.0.1 {site} # managed by lockin" in line or f"127.0.0.1 www.{site} # managed by lockin" in line:
                    return True
        return False
    except Exception as e:
        logging.error(f"Failed to check if site is blocked: {e}")
        print(f"Failed to check if site is blocked: {e}")
        return False

def block_site(site):
    if is_site_blocked(site):
        print(f"{site} is already blocked.")
        return
    try:
        print(f"Blocking {site}...")
        subprocess.run(["sudo", "bash", "-c", f"echo '127.0.0.1 {site} # managed by lockin' >> /etc/hosts"], check=True)
        logging.info(f"Blocked {site}")
        print(f"Blocked {site}")
        if not site.startswith("www."):
            print(f"Blocking www.{site}...")
            subprocess.run(["sudo", "bash", "-c", f"echo '127.0.0.1 www.{site} # managed by lockin' >> /etc/hosts"], check=True)
            logging.info(f"Blocked www.{site}")
            print(f"Blocked www.{site}")
    except Exception as e:
        logging.error(f"Failed to block site {site}: {e}")
        print(f"Failed to block site {site}: {e}")

def create_unblock_script(site):
    script_path = f"/usr/local/bin/unblock_{site}.sh"
    try:
        with open(script_path, "w") as script_file:
            script_file.write(f"#!/bin/bash\n")
            script_file.write(f"sudo sed -i '/127.0.0.1 {site} # managed by lockin/d' /etc/hosts\n")
            script_file.write(f"sudo sed -i '/127.0.0.1 www.{site} # managed by lockin/d' /etc/hosts\n")
            script_file.write(f"rm -- \"$0\"\n")  # This line deletes the script after it runs
        subprocess.run(["sudo", "chmod", "+x", script_path], check=True)
        logging.info(f"Created unblock script {script_path}")
    except Exception as e:
        logging.error(f"Failed to create unblock script for {site}: {e}")
        print(f"Failed to create unblock script for {site}: {e}")
    return script_path

def schedule_unblock(site, duration):
    try:
        unblock_script = create_unblock_script(site)
        delay_minutes = int(duration.total_seconds() // 60)
        now = datetime.now()
        run_time = now + timedelta(minutes=delay_minutes)
        run_time_str = run_time.strftime('%H:%M %Y-%m-%d')

        subprocess.run(["sudo", "at", run_time_str], input=f"{unblock_script}\n", text=True, check=True)
        logging.info(f"Scheduled to unblock {site} after {duration}")
        print(f"Scheduled to unblock {site} after {duration}")
    except Exception as e:
        logging.error(f"Failed to schedule unblock for {site}: {e}")
        print(f"Failed to schedule unblock for {site}: {e}")

parser = argparse.ArgumentParser(description="Block a website for a specified duration")
parser.add_argument('-t', '--time', type=int, help='Duration to block the site')
parser.add_argument('-s', '--site', type=str, help='Site to block')
parser.add_argument('unit', nargs='?', choices=['m', 'h', 'd', 'w'], help='Unit of time (minutes, hours, days, weeks)')
parser.add_argument('-ls', '--list', action='store_true', help='List blocked sites')
parser.add_argument('-u', '--unblock', type=str, help='Unblock a specific site or "all" to unblock all sites')

args = parser.parse_args()

if args.list:
    list_blocked_sites()
    exit(0)

if args.unblock:
    if args.unblock == "all":
        unblock_all_sites()
    else:
        manual_unblock_site(args.unblock)
    exit(0)

if not args.time or not args.site or not args.unit:
    usage()

validate_url(args.site)

block_duration = calculate_duration(args.time, args.unit)

block_site(args.site)

if not is_site_blocked(args.site):
    schedule_unblock(args.site, block_duration)
else:
    print(f"{args.site} is already blocked.")
