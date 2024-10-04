#!/usr/bin/env python3
from pprint import pp
import io
import os
import re
import subprocess
import typing as t
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

from logfisher_summary_flow import config


def thl_logs_in_dir(dir_: Path, console: Console, vizier: bool = False):
    with console.status("Running THL on logs...", spinner="aesthetic"):
        vizier_keys = [dir_ / f.name for f in dir_.glob(config.LOG_GLOB_VIZIER)]
        bot_log_keys = [dir_ / f.name for f in dir_.glob(config.LOG_GLOB_ALPHABOT)]
        errors = []
        warnings = []

        for log_key in vizier_keys + bot_log_keys:
            log_base_name = log_key.name.replace(".key.thl", "")
            log_files = [f for f in dir_.glob(f"{log_base_name}.thl*")]

            if (vizier and log_key in vizier_keys) or (log_key in bot_log_keys):
                console.print(f"        {log_base_name}")

            with (dir_ / f"{log_base_name}.txt").open("w") as out:
                command = ["thl", "--ts", "utc", log_key]
                command.extend(log_files)
                ret = subprocess.run(
                    command, stdout=out, stderr=subprocess.PIPE, text=True
                )
                if ret.returncode != 0:
                    errors.append(f"Unable to thl {log_key.name}:")
                    errors.append(ret.stderr.splitlines())
                elif not ret.stderr.isspace() and ret.stderr != "":
                    warnings.append(ret.stderr.splitlines())

        if len(errors) > 0:
            console.print("    THL errors:", style="red")
            for err in errors:
                console.print(f"        {err}", style="red")

        if len(warnings) > 0:
            console.print("    THL warnings:", style="yellow")
            for warn in warnings:
                console.print(f"        {warn}", style="yellow")


def parse_alphabot_summary(log: io.StringIO, faults: t.Dict[str, str], _):
    move_requests, move_completes = {}, {}

    lines = []
    pwd  = os.getcwd()
    with log as log_file:
        log = log_file.read().splitlines()
        for line in log:
            move_req_match = re.match(config.Patterns.MOVE_REQUEST, line)
            if move_req_match:
                move_requests[
                    (move_req_match.group("cmd_id"), move_req_match.group("uuid"))
                ] = {
                    "timestamp": move_req_match.group("timestamp"),
                    "src": move_req_match.group("src"),
                    "dest": move_req_match.group("dest"),
                }
                continue

            move_complete_match = re.match(config.Patterns.MOVE_COMPLETE, line)
            if move_complete_match:
                move_completes[
                    (
                        move_complete_match.group("cmd_id"),
                        move_complete_match.group("uuid"),
                    )
                ] = move_complete_match.group("status")
                continue

            tote_match = re.match(config.Patterns.TOTE_COMMANDS, line)
            if tote_match:
                lines.append(
                    f"{tote_match.group('timestamp')} [TOTE] {tote_match.group('action'):<13} {tote_match.group('side'):<17} | {tote_match.group('grid_id')}"
                )
                continue

            fault_match = re.match(config.Patterns.FAULTS, line)
            if fault_match:
                lines.append(
                    f"{fault_match.group('timestamp')} [FAULT] {fault_match.group('fault_num'):<12} {fault_match.group('type'):<17} | {faults.get(fault_match.group('fault_num'), 'Fault description was not found')}"
                )
                continue

            splc_match = re.match(config.Patterns.SPLC, line)
            if splc_match:
                lines.append(
                    f"{splc_match.group('timestamp')} W [FPGA1 safety debug change]          | {splc_match.group('fpga_msg')}"
                )
                continue

    for key in move_requests.keys():
        if key[0] == "0":
            status = "Bot Initializing"
        else:
            status = move_completes.get(key)
            if status is None:
                status = "Move Blended or only received ACK"
        move = move_requests[key]
        lines.append(
            f"{move['timestamp']} {move['src']:<17} -> {move['dest']:<17} | {status}"
        )

    return lines


def parse_vizier_summary(log_path: Path, _, acp: t.Dict[str, dict]):
    lines = []
    seen = set()

    with open(log_path) as log_file:
        log = log_file.read().splitlines()
        for line in log:
            telemetry = None
            match = re.match(config.Patterns.VIZIER, line)
            if match:
                ts = match.group("timestamp")
                func = match.group("func")

                # message handlers in vizier reprint bytes, causing duplicate lines in summary
                # use tuple with set to deduplicate: (timestamp to the second, packet ID, function id)
                key = (str(ts).split(".")[0], match.group("id"), match.group("func"))
                if key in seen:
                    continue
                else:
                    seen.add(key)

                if func in config.VIZIER_TELEMETRY_FUNCTIONS:
                    telem_match = re.match(config.Patterns.VIZIER_TELEMETRY, line)
                    if telem_match:
                        telemetry = f" | TELEMETRY: {config.get_telemetry(telem_match.group('telemetry_block'))}"

                acp_data = acp.get(func)
                if acp_data:
                    lines.append(
                        f"{ts} {match.group('id'):<14} | DIR: {acp_data['dir']:<4} | MSG TYPE: {match.group('func')} | ID: {acp_data['msg_id']:<6} | DESC: {acp_data['desc']:<34}{telemetry or ''}"
                    )
                else:
                    lines.append(
                        f"{ts} {match.group('id'):<14} | MSG TYPE: {match.group('func')}{telemetry or ''}"
                    )
    return lines

def generate_summary_for_single_file(
    log_file: io.StringIO,
):
   lines = []
   faults = config.get_faults()
   acp = config.get_acp()
   lines = parse_alphabot_summary( log_file, faults, acp)
   return lines


def generate_summary(
    process_pool: ProcessPoolExecutor,
    log_dir: Path,
    log_glob: str,
    desc: str,
    summary_name: str,
    worker_func,
):
    futures = []
    lines = []
    progress = Progress(
        TextColumn("    {task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    )

    faults = config.get_faults()
    acp = config.get_acp()

    for log in log_dir.glob(log_glob):
        # exclude data logs...
        if "data" not in log.name:
            futures.append(process_pool.submit(worker_func, log, faults, acp))

    with progress:
        for future in progress.track(
            as_completed(futures),
            total=len(futures),
            description=desc,
        ):
            lines.extend(future.result())

    with open(log_dir / summary_name, "w") as summary_file:
        summary_file.writelines(line + "\n" for line in sorted(lines))


def summarize(pool: ProcessPoolExecutor, log_dir: Path, vizier: bool = False):
    generate_summary(
        process_pool=pool,
        log_dir=log_dir,
        log_glob="alphabot*.txt",
        desc=f"{log_dir.name}         ",
        summary_name=config.SUMMARY_NAME_ALPHABOT,
        worker_func=parse_alphabot_summary,
    )

    if vizier:
        generate_summary(
            process_pool=pool,
            log_dir=log_dir,
            log_glob=f"vizier*.txt",
            desc=f"{log_dir.name} (vizier)",
            summary_name=config.SUMMARY_NAME_VIZIER,
            worker_func=parse_vizier_summary,
        )
