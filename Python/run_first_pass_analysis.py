"""Пробный запуск постобработки первого измерительного проезда."""

# System imports
from pathlib import Path
from typing import Iterable

# External imports
import matplotlib
import numpy as np

matplotlib.use("Agg")

# User imports
from data_analys import ProcessingConfig, RunFiles, discover_run_files, load_run_csv, process_run
from data_analys.data_loader import ACC_COLUMNS, GYRO_DEG_COLUMNS
from data_analys.math_tools import Vector
from plotting import CanvasConfig, Plotter

##########################################################

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "Проезды" / "Тест"
OUTPUT_DIR = DATA_DIR / "results"

RUN_NUMBER = 1
SAMPLE_RATE_HZ = 10.0
PERIOD_S = 1.0 / SAMPLE_RATE_HZ

# TODO: Уточнить фактическую широту участка испытаний.
LATITUDE_DEG = 55.7558

CSV_SEPARATOR = r"\s+"
OUTPUT_CSV_SEPARATOR = " "

##########################################################

RGB_CLASSIC = ["tab:blue", "tab:red", "tab:green"]
RGB_DARK = ["navy", "darkred", "darkgreen"]
GYRO_CLASSIC = ["tab:purple", "tab:orange", "tab:brown"]
GYRO_DARK = ["indigo", "darkorange", "saddlebrown"]
NAV_CLASSIC = ["tab:cyan", "tab:pink", "tab:olive"]

##########################################################


def main() -> int:
    """Запускает pipeline для первого проезда и сохраняет диагностические графики."""

    config = ProcessingConfig(
        period=PERIOD_S,
        latitude_deg=LATITUDE_DEG,
        output_dir=OUTPUT_DIR / "pipeline",
        csv_separator=CSV_SEPARATOR,
        output_csv_separator=OUTPUT_CSV_SEPARATOR,
        save_results=True,
    )

    plots_dir = OUTPUT_DIR / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    run_files = _get_run_files(DATA_DIR, RUN_NUMBER)
    static_data = load_run_csv(run_files.static_path, config)

    print_header("Исходные данные")
    print(f"Папка данных: {DATA_DIR}")
    print(f"Статический буфер: {run_files.static_path.name}")
    print(f"Измерительный проезд: {run_files.measuring_path.name}")
    print(f"Частота выдачи данных: {SAMPLE_RATE_HZ:.3f} Гц")
    print(f"Период дискретизации: {PERIOD_S:.6f} с")
    print(f"Широта для учета вращения Земли: {LATITUDE_DEG:.6f} град")

    result = process_run(run_files, config)

    acc_mean_body = _mean_vector(static_data.dataframe, ACC_COLUMNS)
    acc_mean_nav = result.initialization.q_body_to_nav.rotate_vector(acc_mean_body)

    print_header("Проверка начальной выставки")
    print(f"Кватернион body -> ENU: {result.initialization.q_body_to_nav}")
    print(f"Было: {acc_mean_body}.\nСтало: {acc_mean_nav}")
    print(f"Норма до поворота: {acc_mean_body.norm:.6f} м/с**2")
    print(f"Норма после поворота: {acc_mean_nav.norm:.6f} м/с**2")
    print(f"Смещение акселерометра: {result.initialization.bias_acc}")
    print(f"Смещение гироскопа, рад/с: {result.initialization.bias_gyro}")

    print_header("Результат pipeline")
    print(f"Фактическое направление по DppCode: {result.direction.value}")
    print(f"Количество отсчетов проезда: {len(result.detailed_dataframe)}")
    print(
        "Диапазон DppCode: "
        f"{int(result.detailed_dataframe['DppCode'].min())} .. "
        f"{int(result.detailed_dataframe['DppCode'].max())}"
    )
    print(f"Подробный CSV: {result.detailed_output_path}")
    print(f"CSV по DppCode: {result.dpp_output_path}")

    print_header("Построение графиков")
    _plot_static_buffer(static_data.dataframe, plots_dir)
    _plot_measuring_acceleration(result.detailed_dataframe, plots_dir)
    print(f"Графики сохранены в: {plots_dir}")

    print_header("Готово")
    return 0


##########################################################


def _get_run_files(directory: Path, run_number: int) -> RunFiles:
    """Возвращает пару файлов заданного проезда из результата авторазметки."""

    discovery = discover_run_files(directory)
    for run_files in discovery.runs:
        if run_files.run_number == run_number:
            return run_files

    available = [str(run.run_number) for run in discovery.runs]
    raise RuntimeError(
        f"Run {run_number} was not found in {directory}. Available runs: {', '.join(available)}"
    )


def _mean_vector(df, columns: Iterable[str]) -> Vector:
    """Считает покомпонентное среднее по трем заданным колонкам."""

    return Vector(df[list(columns)].to_numpy(dtype=float).mean(axis=0))


def _plot_static_buffer(df, output_dir: Path) -> None:
    """Строит графики ускорений и угловых скоростей статического буфера."""

    x_data = np.arange(len(df), dtype=float)
    _plot_static_3d(
        x_data=x_data,
        y_data=[df[column].to_numpy(dtype=float) for column in ACC_COLUMNS],
        title="Статический буфер: ускорения",
        y_labels=["AccX, м/с**2", "AccY, м/с**2", "AccZ, м/с**2"],
        colors=RGB_CLASSIC,
        dark_colors=RGB_DARK,
        output_path=output_dir / "run_1_static_acc.png",
    )
    _plot_static_3d(
        x_data=x_data,
        y_data=[df[column].to_numpy(dtype=float) for column in GYRO_DEG_COLUMNS],
        title="Статический буфер: угловые скорости",
        y_labels=["GyroX, град/с", "GyroY, град/с", "GyroZ, град/с"],
        colors=GYRO_CLASSIC,
        dark_colors=GYRO_DARK,
        output_path=output_dir / "run_1_static_gyro.png",
    )


def _plot_measuring_acceleration(df, output_dir: Path) -> None:
    """Строит графики ускорений измерительного проезда."""

    time = df["Time"].to_numpy(dtype=float)
    _plot_dynamic_3d(
        x_data=time,
        y_data=[df[column].to_numpy(dtype=float) for column in ACC_COLUMNS],
        title="Проезд 1: исходные ускорения",
        y_labels=["AccX, м/с**2", "AccY, м/с**2", "AccZ, м/с**2"],
        colors=RGB_CLASSIC,
        output_path=output_dir / "run_1_measuring_acc_body.png",
    )
    _plot_dynamic_3d(
        x_data=time,
        y_data=[
            df["AccNavE"].to_numpy(dtype=float),
            df["AccNavN"].to_numpy(dtype=float),
            df["AccNavU"].to_numpy(dtype=float),
        ],
        title="Проезд 1: ускорения после перевода в ENU",
        y_labels=["AccE, м/с**2", "AccN, м/с**2", "AccU, м/с**2"],
        colors=NAV_CLASSIC,
        output_path=output_dir / "run_1_measuring_acc_enu.png",
    )


def _plot_static_3d(
    x_data: np.ndarray,
    y_data: list[np.ndarray],
    title: str,
    y_labels: list[str],
    colors: list[str],
    dark_colors: list[str],
    output_path: Path,
) -> None:
    """Сохраняет три статических графика с гистограммами распределений."""

    config = CanvasConfig()
    config.n_rows = 3
    config.n_cols = 2
    config.ax_kwargs["width_ratios"] = [3, 1]
    config.x_data = x_data
    config.y_data = y_data
    config.x_label = "Номер отсчета"
    config.y_label = y_labels
    config.suptitle = title
    config.color_names = colors
    config.dark_color_names = dark_colors
    config.annotation = [
        f"Mean = {np.mean(component):.6f}" for component in y_data
    ]

    plotter = Plotter(config)
    plotter.plotting_3d_static()
    plotter.save(str(output_path))


def _plot_dynamic_3d(
    x_data: np.ndarray,
    y_data: list[np.ndarray],
    title: str,
    y_labels: list[str],
    colors: list[str],
    output_path: Path,
) -> None:
    """Сохраняет три временных графика компонент вектора."""

    config = CanvasConfig()
    config.n_rows = 3
    config.n_cols = 1
    config.x_data = x_data
    config.y_data = y_data
    config.x_label = "Time, с"
    config.y_label = y_labels
    config.suptitle = title
    config.color_names = colors

    plotter = Plotter(config)
    plotter.plotting_3d()
    plotter.save(str(output_path))


def print_header(text: str) -> None:
    """Печатает аккуратный заголовок информационного блока."""

    print()
    print("#" * 72)
    print(f"# {text}")
    print("#" * 72)


##########################################################


if __name__ == "__main__":
    raise SystemExit(main())
