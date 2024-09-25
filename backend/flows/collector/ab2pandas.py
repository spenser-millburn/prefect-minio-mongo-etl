"""
Convert Alert Innovation Alphabot data log files to various formats and explore data
"""
from base64 import b64decode
from glob import iglob
from os import path
from pathlib import Path
from tempfile import NamedTemporaryFile

from numpy import fromfile
from pandas import DataFrame, HDFStore

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


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        "-o",
        "--output",
        choices=["csv", "dta", "fea", "h5", "json", "parquet", "pkl", "pqt"],
    )
    parser.add_argument("filename")

    args = parser.parse_args()
    user_path = Path(args.filename)

    df = convert(user_path)

    out_funcs = {
        "csv": df.to_csv,
        "dta": df.to_stata,
        "fea": df.to_feather,
        "h5": lambda fn: HDFStore(fn).put('df', df),
        "json": df.to_json,
        "parquet": df.to_parquet,
        "pkl": df.to_pickle,
        "pqt": df.to_parquet,
    }

    if args.output:
        out_funcs[args.output](user_path.with_suffix("." + args.output))
    else:
        try:
            from pandasgui import show
            gui = show(df)
        except ImportError:
            raise ImportError('Install PandasGUI or specify output format')
