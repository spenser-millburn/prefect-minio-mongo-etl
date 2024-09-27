import re
from typing import List
from snapstat.constants import *


# Define the action to check if the max ERROR exceeds the threshold
def check_max_smaller_error(window: List[str]) -> str:
    """
    Action function to check if any ERROR value in the log window exceeds the threshold (0.05).
    If it does, it returns a string showing the maximum error value.
    Otherwise, returns 'False' for no error above the threshold.
    """
    error_pattern = re.compile(r'ERROR \[ x_pos : ([\d\.\-]+) \]')
    max_error = 0.0
    
    # Iterate through the log window to find ERROR values
    for line in window:
        match = error_pattern.search(line)
        if match:
            error_value = float(match.group(1))
            max_error = max(max_error, error_value)
    
    # Return a custom message if max_error exceeds the threshold
    if max_error < SMALL_FPO_SLIP_THRESHOLD:
        return f"Max ERROR : {max_error:.3f}"
    else:
        return False  # No error exceeds the threshold

# Define the action to check if the max ERROR exceeds the threshold
def check_max_error(window: List[str]) -> str:
    """
    Action function to check if any ERROR value in the log window exceeds the threshold (0.05).
    If it does, it returns a string showing the maximum error value.
    Otherwise, returns 'False' for no error above the threshold.
    """
    error_pattern = re.compile(r'ERROR \[ x_pos : ([\d\.\-]+) \]')
    max_error = 0.0
    
    # Iterate through the log window to find ERROR values
    for line in window:
        match = error_pattern.search(line)
        if match:
            error_value = float(match.group(1))
            max_error = max(max_error, error_value)
    
    # Return a custom message if max_error exceeds the threshold
    if max_error > LARGE_FPO_SLIP_THRESHOLD:
        return f"Max ERROR : {max_error:.3f}"
    else:
        return False  # No error exceeds the threshold

# Regex pattern to detect any IMU impact event
impact_pattern = timestamp_re + r"[A-Z] _IMU0 Impact detected on [A-Z]+ IMU of ([\d\.]+) G" #at TS=\d+. Pos=\[x:([\d\.\-]+), y:([\d\.\-]+), z:([\d\.\-]+), roll:([\d\.\-]+), pitch:([\d\.\-]+), yaw:([\d\.\-]+)\] Vel=\[x:([\d\.\-]+), y:([\d\.\-]+), z:([\d\.\-]+), roll:([\d\.\-]+), pitch:([\d\.\-]+), yaw:([\d\.\-]+)\]"

# Action to process impact event
def process_impact_event(window: List[str]) -> str:
    """
    Action to extract and process impact event details.
    """
    max_g_force = 0
    for line in window:
        match = re.search(impact_pattern, line)
        if match:
            g_force = float(match.group(1))
            if g_force > max_g_force:
                max_g_force = g_force

    if max_g_force > 5:
        return f"Impact detected with {max_g_force} G."
    else:
        return None

# Updated regex pattern to detect the sequence of "Sent fault to MCS for Id" with dynamic content
fault_to_mcs_pattern = re.compile(r"\bSent fault to MCS for Id[=\s](\S+)")

# Action to extract the sequence of fault events
def extract_faults_sent_to_mcs_during_window(window: List[str]) -> List[str]:
    """
    Action to extract all occurrences of 'Sent fault to MCS for Id' events from the log window.
    Returns a list of fault IDs.
    """
    fault_ids = []
    for line in window:
        match = fault_to_mcs_pattern.search(line)
        if match:
            fault_ids.append(match.group(1))
    
    return str(fault_ids) if fault_ids else None

