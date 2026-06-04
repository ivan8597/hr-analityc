import pandas as pd

from ..logger import logger


def transform(df: pd.DataFrame, reject_logger=None) -> pd.DataFrame:
    df = df.copy()

    date_fields = ['hire_date', 'return_date']
    for field in date_fields:
        if field in df.columns:
            raw_series = df[field].copy()
            parsed = pd.to_datetime(
                raw_series,
                errors='coerce',
                dayfirst=True,
                format='mixed'
            ).dt.date
            invalid_mask = raw_series.notna() & parsed.isna()
            if invalid_mask.any() and reject_logger:
                for idx in df[invalid_mask].index:
                    reject_logger.log_reject(
                        row=df.loc[idx].to_dict(),
                        column_name=field,
                        raw_value=raw_series[idx],
                        reason=f'Invalid date format: {raw_series[idx]}'
                    )
            df[field] = parsed

    if 'harmful' in df.columns:
        df['harmful'] = df['harmful'].notna()
    else:
        df['harmful'] = False

    if 'source_id' in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=['source_id'], keep='last')
        after = len(df)
        if before != after:
            logger.warning(f"Removed {before - after} duplicate rows based on source_id")

    required_fields = ['source_id', 'full_name']
    for field in required_fields:
        if field in df.columns:
            invalid = df[field].isna()
            if invalid.any() and reject_logger:
                for idx in df[invalid].index:
                    reject_logger.log_reject(
                        row=df.loc[idx].to_dict(),
                        column_name=field,
                        raw_value=df.loc[idx].get(field),
                        reason=f'Missing mandatory field: {field}'
                    )
            df = df[~invalid]
        else:
            raise ValueError(f"Required field '{field}' missing after mapping")

    logger.info(f"Transformed {len(df)} HR records")
    return df
