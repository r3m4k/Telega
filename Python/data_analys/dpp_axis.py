"""Операции с кодами ДПП и сведение результатов нескольких проездов."""

# System imports
from typing import Optional

# External imports
import pandas as pd

# User imports
from .models import DppDownsampleMode, ProcessingResult, RunDirection

##########################################################


DPP_RESULT_COLUMNS = [
    "Time",
    "VelocityE",
    "VelocityN",
    "VelocityU",
    "PositionE",
    "PositionN",
    "PositionU",
]

##########################################################


def detect_direction_from_dpp(df: pd.DataFrame) -> RunDirection:
    """Определяет направление движения по начальному и конечному коду ДПП."""

    start = int(df["DppCode"].iloc[0])
    end = int(df["DppCode"].iloc[-1])
    if end > start:
        return RunDirection.FORWARD
    if end < start:
        return RunDirection.BACKWARD
    return RunDirection.UNKNOWN


def aggregate_by_dpp(
    df: pd.DataFrame,
    value_columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Сводит повторяющиеся коды ДПП, усредняя значения по каждому коду."""

    if value_columns is None:
        value_columns = DPP_RESULT_COLUMNS
    selected_columns = ["DppCode", *value_columns]
    missing = [column for column in selected_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Cannot aggregate by DppCode, missing columns: {', '.join(missing)}")
    grouped = df[selected_columns].groupby("DppCode", as_index=False).mean(numeric_only=True)
    grouped["DppCode"] = grouped["DppCode"].astype(int)
    return grouped.sort_values("DppCode").reset_index(drop=True)


def build_common_dpp_table(
    results: list[ProcessingResult],
    value_columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Строит общую таблицу по всем кодам ДПП, встречающимся в проездах."""

    if value_columns is None:
        value_columns = DPP_RESULT_COLUMNS
    if not results:
        return pd.DataFrame(columns=["DppCode"])

    dpp_min = min(int(result.dpp_dataframe["DppCode"].min()) for result in results)
    dpp_max = max(int(result.dpp_dataframe["DppCode"].max()) for result in results)
    common = pd.DataFrame({"DppCode": range(dpp_min, dpp_max + 1)}).set_index("DppCode")

    for result in results:
        label = _run_label(result)
        run_df = result.dpp_dataframe.set_index("DppCode")
        # TODO: PositionENU is currently relative to each run start. For
        # backward runs and non-zero endpoint constraints, convert positions
        # to a common A->B reference frame before cross-run comparison.
        run_df = run_df[value_columns].rename(
            columns={column: f"{label}_{column}" for column in value_columns}
        )
        common = common.join(run_df, how="left")

    return common.reset_index()


def downsample_common_dpp_table(
    common_df: pd.DataFrame,
    step: int,
    mode: DppDownsampleMode = DppDownsampleMode.TAKE_EVERY_N,
) -> pd.DataFrame:
    """Прореживает общую таблицу по кодам ДПП с заданным шагом."""

    if step <= 1 or common_df.empty:
        return common_df.copy()

    start = int(common_df["DppCode"].min())
    if mode == DppDownsampleMode.TAKE_EVERY_N:
        mask = ((common_df["DppCode"] - start) % step) == 0
        return common_df.loc[mask].reset_index(drop=True)

    if mode == DppDownsampleMode.MEAN_BY_BIN:
        result = common_df.copy()
        result["DppGroup"] = start + ((result["DppCode"] - start) // step) * step
        grouped = result.drop(columns=["DppCode"]).groupby("DppGroup", as_index=False).mean(
            numeric_only=True
        )
        return grouped.rename(columns={"DppGroup": "DppCode"}).reset_index(drop=True)

    raise ValueError(f"Unsupported DPP downsample mode: {mode}")


##########################################################


def _run_label(result: ProcessingResult) -> str:
    """Формирует префикс колонок для одного проезда в общей таблице."""

    run_number = result.run_files.run_number
    if run_number is not None:
        return f"Run{run_number}"
    return result.run_files.measuring_path.stem
