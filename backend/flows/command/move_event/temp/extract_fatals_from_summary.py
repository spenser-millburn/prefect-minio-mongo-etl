from pprint import pp
def extract_fatal_faults(file_path):
    fatal_faults = {}
    lines_buffer = []
    fault_triggered = False
    
    with open(file_path, 'r') as file:
        for line in file:
            lines_buffer.append(line.strip())
            
            # Keep buffer size to last 10 lines
            if len(lines_buffer) > 10:
                lines_buffer.pop(0)
                
            if "[FAULT]" in line and "fatal" in line.lower():
                # Extract fault code
                fault_code = line.split()[3]
                # Store the last 10 lines (inclusive of the fault line)
                fatal_faults[fault_code] = lines_buffer[:]
                fault_triggered = True

        if not fault_triggered:
            print("No fatal fault detected.")
    
    return fatal_faults

# Usage example:
file_path = './summary.txt'
fatal_fault_logs = extract_fatal_faults(file_path)
pp (fatal_fault_logs)
#  for fault_code, logs in fatal_fault_logs.items():
    #  print(f"Fault Code: {fault_code}")
    #  for log in logs:
        #  print(log)
