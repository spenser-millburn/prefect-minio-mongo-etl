
#!/usr/bin/env python3

import csv
import re
import typing as t
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from toml import load
import os
import importlib.resources as pkg_resources

# environment variable to check if in Docker
AM_I_DOCKER = os.getenv('AM_I_DOCKER', False)
# paths
PATH_ROOT = Path(os.getcwd())
PATH_CONFIG = PATH_ROOT
PATH_SRC = PATH_ROOT / "src"

# constants
ALERTINNOVATIONCLOUD_TENANT_ID = "4242507b-7c2b-4bc9-93f8-d016d27ceb9b"
ACCOUNT_URL_PROD_GLOBAL = "https://adx-adm-prod-global.eastus2.kusto.windows.net"
BLOB_STORAGE_URL_LAB = "https://dladmdeveus.blob.core.windows.net"
CONTAINER_NAME = "walmart"

LOG_GLOB_ALPHABOT = "alphabot*.key.thl"
LOG_GLOB_VIZIER = "vizier*.key.thl"
SUMMARY_NAME_ALPHABOT = "summary.txt"
SUMMARY_NAME_VIZIER = "vizier-summary.txt"

# TODO retrieve this dynamically? Ask Devops to add column to ClusterSiteInfo, or figure out query/api call
# could also regex or similar to put together storage account name from cluster name but that seems like a hack
CLUSTER_TO_STORAGE_ACCOUNT_MAP = {
    "adx-adm-dev.eastus":               "adxadmdev",
    "adx-adm-prod-grp1.southcentralus": "dladmprodscusgrp1",
    "adx-adm-prod-grp2.southcentralus": "dladmprodscusgrp2",
    "adx-adm-prod-grp3.eastus2":        "dladmprodeus2grp3",
    "adx-adm-prod-grp4.westus2":        "dladmprodwus2grp4",
}

TELEMETRY_MAP = [
    ["ONLINE", "HOMED", "TOTE PRES", "LOW CONFIDENCE TOTE"],
    ["SAFE TO AUTO HOME", "BRAKE ON", "E-STOP 1", "E-STOP 0"],
    ["OPERATION", "LOADING", "UNLOADING", "TRAVELING"],
    ["ENGAGE FAILED", "DISENGAGE FAILED", "LOW CONFIDENCE MOVE", "HOMING"],
    ["PINIONS OUT", "PINIONS IN", "WHEELS OUT", "WHEELS IN"],
    ["DEINIT", "LP LEFT", "LP MID", "LP RIGHT"],
    ["RESERVED", "RESERVED", "RESERVED", "RESERVED"],
    ["SEND GYRO", "SEND PROX", "SEND TEMP", "SEND SSID"],
]

VIZIER_TELEMETRY_FUNCTIONS = (
    "01 08",  # s1f8     init complete ack
    "01 42",  # s1f66    telemetry data report
    "06 41",  # s6f65    telemetry data report
    "40 02",  # s64f2    move command ack
    "c0 03",  # s64f3    move initiated
    "c0 05",  # s64f5    move complete
    "40 0c",  # s64f12   load/unload ack
    "c0 0d",  # s64f13   load/unload complete
)

# defaults
with pkg_resources.open_text(__package__, 'config.toml') as conf_file:
    defaults = load(conf_file)

DATE = datetime.today()
DIRECTORY = defaults.get("dir")
SITE = defaults.get("site")

# load files
BOT_CSV_PATH = PATH_CONFIG / "bots.csv"

def get_acp() -> t.Dict[str, t.Dict[str, str]]:
    """Read in ACP table doc"""
    with pkg_resources.open_text(__package__, 'ACPTable.txt') as acp_file:
        acp = {  # row[0]=msg_id, row[1]=msg_type, row[3]=dir, row[4]=desc
            row[1].lower(): {"msg_id": row[0], "dir": row[3], "desc": row[4]}
            for row in csv.reader(acp_file, delimiter="\t")
        }
    return acp

def get_faults() -> t.Dict[str, str]:
    """Read in embedded fault table csv"""
    with pkg_resources.open_text(__package__, 'EmbeddedFaultTable.csv') as fault_file:
        faults = {  # row[1]=fault_num, row[16]=fault_description
            row['ID sent to MCS']: row['Short Description of Fault'] for row in csv.DictReader(fault_file, delimiter="\t")
        }
    return faults

# regular expressions
@dataclass
class Patterns:
    # bot logs
    MOVE_REQUEST = re.compile(  # move request
        r"(?P<timestamp>....-..-.. ..:..:..\....).*MOVE_REQUEST.*cmd_ID: (?P<cmd_id>\d+).*src: (?P<src>.*) dest: (?P<dest>.*) weight.*UUID\((?P<uuid>\w+-\w+-\w+-\w+-\w+)"
    )
    MOVE_COMPLETE = re.compile(  # move complete
        r".*Outgoing msup command response CMD_RESPONSE\(\d+#\d+ (?P<status>COMPLETE \w+)\).*cmd_ID: (?P<cmd_id>\d+) ucco? :.*UUID\((?P<uuid>\w+-\w+-\w+-\w+-\w+)"
    )
    TOTE_COMMANDS = re.compile(  # tote command
        r"(?P<timestamp>....-..-.. ..:..:..\....).*TCOM0.*NEW_COMMAND : Command ID .* , (?P<action>.*)\(\d+\) , (?P<side>.*)\(\d+\) , Grid ID (?P<grid_id>.*) , UUID"
    )
    FAULTS = re.compile(  # faults
        r".*(?P<timestamp>....-..-.. ..:..:..\....).* Fault Cache id:fault_(?P<fault_num>\w+) Type:(?P<type>\w+)"
    )
    SPLC = re.compile(  # fpga / splc
        r".*(?P<timestamp>....-..-.. ..:..:..\....).*FPGA1 safety debug change: (?P<fpga_msg>.*SPLC=0x[^F].*)$"
    )

    # vizier logs
    VIZIER = re.compile(
        r".*(?P<timestamp>....-..-.. ..:..:..\....).*(?P<id>Packet ID: -?\d+) - Bytes: 41 42 (?:[0-9a-fA-F]+ ){4}(?P<func>[0-9a-fA-F]+ [0-9a-fA-F]+)"
    )
    VIZIER_TELEMETRY = re.compile(
        r".*\| .*41 08 (?P<telemetry_block>(?:3[a-zA-Z0-9] ){8})"
    )

def get_telemetry(telemetry_block: str):
    """Given a Vizier telemetry block in hex, return list of high telemetry bits"""
    telem = []
    telemetry_bytes = [int(c[1], 16) for c in telemetry_block.split()]
    for byte, status_row in zip(telemetry_bytes, TELEMETRY_MAP):
        if byte & 8:
            telem.append(status_row[0])
        if byte & 4:
            telem.append(status_row[1])
        if byte & 2:
            telem.append(status_row[2])
        if byte & 1:
            telem.append(status_row[3])
    return telem

