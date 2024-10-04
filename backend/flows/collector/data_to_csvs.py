import os
import re
import sys
from pathlib import Path
from base64 import b64decode
from glob import iglob
from os import path
from pathlib import Path
from tempfile import NamedTemporaryFile
from numpy import fromfile
from pandas import DataFrame, HDFStore
import typer

""" Convert Alert Innovation Alphabot data log files to various formats and explore data """

# NumPy type conversions for the `datalogkey` codes
TYPEKEY = ["u1", "u2", "u4", "u8", "i1", "i2", "i4", "i8", "?", "f4", "f8"]

def convert(user_path: Path) -> DataFrame:
    """Convert a log data file to a dataframe"""
    b = path.splitext(path.basename(user_path))
    data_file_paths = sorted(set(iglob(path.join(path.dirname(user_path), b[0] + '*' + b[-1]))), reverse=True)

    # file without number is newest. move it to the end
    data_file_paths.append(data_file_paths.pop(0))

    with NamedTemporaryFile(mode="w+b") as temp_file:
        for data_file_path in data_file_paths:
            with open(data_file_path, "r", encoding="ascii") as data_file:
                # Search for the `datalogkey` defining the fields and format for the
                # base64 encoded binary data.
                for line in data_file:
                    if line.startswith("datalogkey:"):
                        datalogkey = [
                            (k, TYPEKEY[int(v)])
                            for k, v in [pair.split(",") for pair in line[11:].split(";")[:-1]]
                        ]
                        break

                # Immediately after the line containing the data log key, start reading
                # space-delimited pairs of timestamps and base64 encoded binary chunks.
                # Start a temporary file to preserve RAM
                for line in data_file:
                    try:
                        _, encoded = line.split()
                        temp_file.write(b64decode(encoded))
                    except ValueError:
                        break

        return DataFrame.from_records(
            fromfile(temp_file.name, dtype=datalogkey), index="thl_ts"
        )

def convert_all_datalogs_to_csv(directory: Path, remove_source_files:bool):
    pattern = re.compile(r'alphabot_.*-data\.txt')

    files = os.listdir(directory)

    # Filter files that match the pattern
    matching_files = [f for f in files if pattern.match(f)]

    # Execute the conversion for each matching file
    for file in matching_files:
        print ("Converting [", file, "] to csv format")
        user_path = Path(directory) / file
        df = convert(user_path)
        df.to_csv(user_path.with_suffix(".csv"))

    #  Delete the source files
    if(remove_source_files):
        for file in files:
            if '-data.' in file: # gpt please make this also delete files like alphabot_000106_2024_09_09_23_40_43-data.1.txt 
                os.remove(Path(directory) / file)

def main(directory: Path):
    convert_all_datalogs_to_csv(directory)

if __name__ == "__main__":
    typer.run(main)
