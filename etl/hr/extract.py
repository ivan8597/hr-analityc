import zipfile

import pandas as pd

from ..logger import logger
from ..retry import with_io_retry
from .config import HRConfig
from .schema_mapper import HRSchemaMapper


def _excel_engine(file_path: str) -> str | None:
    with open(file_path, "rb") as f:
        signature = f.read(4)
    if signature.startswith(b"PK"):
        with zipfile.ZipFile(file_path) as archive:
            names = set(archive.namelist())
        if "Index/Document.iwa" in names:
            raise ValueError(
                "HR file is saved in Apple Numbers format. "
                "Export it as Excel (.xlsx or .xls) before running ETL."
            )
        if "[Content_Types].xml" not in names:
            raise ValueError("HR file is a ZIP archive, but not a valid Excel workbook.")
        return "openpyxl"
    if signature == b"\xd0\xcf\x11\xe0":
        return "xlrd"
    return None


@with_io_retry
def extract(mapper: HRSchemaMapper, reject_logger=None, excel_path: str = None) -> pd.DataFrame:
    file_path = excel_path or HRConfig.HR_EXCEL_PATH
    logger.info(f"Extracting HR data from {file_path}")
    df = pd.read_excel(file_path, sheet_name=0, dtype=str, engine=_excel_engine(file_path))
    logger.info(f"Raw HR columns: {list(df.columns)}")

    col_map = mapper.map_columns(df.columns, reject_logger=reject_logger)
    rename_map = {v: k for k, v in col_map.items()}
    df = df.rename(columns=rename_map)

    target_cols = [c for c in col_map.keys() if c in df.columns]
    df = df[target_cols]

    df = df.replace(r'^\s*$', None, regex=True)
    df = df.where(pd.notnull(df), None)

    logger.info(f"Extracted {len(df)} HR rows, columns: {list(df.columns)}")
    return df
