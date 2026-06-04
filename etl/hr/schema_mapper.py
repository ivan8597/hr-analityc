import json

from rapidfuzz import fuzz

from ..logger import logger
from .config import HRConfig


class HRSchemaMapper:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.threshold = HRConfig.FUZZY_THRESHOLD

    def map_columns(self, df_columns: list, reject_logger=None) -> dict:
        mapping = {}
        for target, meta in self.config['columns'].items():
            best_match = None
            best_score = 0
            for col in df_columns:
                col_norm = col.strip().lower()
                for pattern in meta['patterns']:
                    pattern_low = pattern.lower()
                    if col_norm == pattern_low:
                        best_match = col
                        best_score = 100
                        break
                    score = fuzz.token_sort_ratio(col_norm, pattern_low)
                    if score > best_score:
                        best_score = score
                        best_match = col
                if best_score == 100:
                    break
            if best_match and best_score >= self.threshold:
                mapping[target] = best_match
                logger.info(f"HR mapped '{target}' -> '{best_match}' (score {best_score})")
            else:
                if reject_logger:
                    reject_logger.log_reject(
                        row={'all_columns': list(df_columns)},
                        column_name=target,
                        raw_value=str(df_columns),
                        reason=f"Column mapping failed: best match score {best_score} < {self.threshold}"
                    )
                if meta.get('required'):
                    raise ValueError(
                        f"Required HR column '{target}' not found (closest match score {best_score})"
                    )
                logger.warning(f"Optional HR column '{target}' not found (score {best_score})")
        return mapping
