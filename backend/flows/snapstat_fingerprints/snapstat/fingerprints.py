#!/usr/bin/env python3
# fingerprints.py
from collections import namedtuple
import re
from snapstat.actions import *
from snapstat.constants import *

#Fingerprint
Sequence = namedtuple('Sequence', ['name', 'patterns', 'window', 'action', 'filter_actions'], defaults=[None, None])

sequences = [
     Sequence(
         name="0C_05_00_signatures",
         patterns=[
             timestamp_re + r"[A-Z] FAPR0 Sent fault to MCS for Id=fault_0C_05_00",
         ],
         window=100,
         action=extract_faults_sent_to_mcs_during_window
     ),
     Sequence(
         name="05_12_00",
         patterns=[
             timestamp_re + r"[A-Z] FAPR0 Sent fault to MCS for Id=fault_0C_05_00",
         ],
         window=100,
     ),
     Sequence(
         name="0C_05_00_high_wheel_velocity_failure",
         patterns=[
             timestamp_re + r"[A-Z] FMON0 Sent fault to MCS for Id=fault_05_0[67]_00",
             timestamp_re + r"[A-Z] FAPR0 Sent fault to MCS for Id=fault_0C_05_00",
         ],
         window=100,
     ),
      Sequence(
          name="0C_05_00_large_slip",
          patterns=[
              timestamp_re + r"[A-Z] FAPR0 Sent fault to MCS for Id=fault_0C_05_00",
          ],
          window=20,
          action=check_max_error
      ),
     Sequence(
         name="0C_05_00_small_slip",
         patterns=[
             timestamp_re + r"[A-Z] FAPR0 Sent fault to MCS for Id=fault_0C_05_00",
         ],
         window=50,
         action=check_max_smaller_error
     ),
    Sequence(
        name="IMU_impact_detected",
        patterns=[
            timestamp_re + r"[A-Z] _IMU0 Impact detected",
            timestamp_re + r"[A-Z] FAPR0 Sent fault to MCS for Id=fault_0C_05_00",
        ],
        window=50,
        action=process_impact_event,
        filter_actions=True
    ),
]
