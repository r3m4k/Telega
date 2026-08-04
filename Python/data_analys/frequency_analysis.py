# System imports

# External imports
import numpy as np

# User imports
from plotting import CanvasConfig, Canvas

#########################

class FrequencyAnalyser:
    def __init__(self, data: np.typing.NDArray, t_array: np.typing.NDArray, sample_rate: float):
        self._time: np.typing.NDArray = t_array     # Массив времени
        self._sample_rate: float = sample_rate      # Частота дискретизации
        self._data: np.typing.NDArray = data        # Массив данных

        self._spectrum_calculated: bool = False     # Флаг вычисления спектра

        self.canvas: Canvas = Canvas(n_rows=2)      # Инструмент для визуализации данных

    def get_spectrum(self) -> (np.typing.NDArray, np.typing.NDArray):
        spectrum = np.abs(np.fft.rfft(self._data - np.mean(self._data))) / len(self._data)
        freq = np.fft.rfftfreq(len(self._data), 1/self._sample_rate)
        self._spectrum_calculated = True
        return freq, spectrum

    def visualisation(self, suptitle: str, time_color: str = 'tab:blue', freq_color: str = 'tab:red'):
        freq, spectrum = self.get_spectrum()
        self.canvas.plot(self._time,
                         [self._data, [None for _ in range(len(self._time))]],
                         color_names=[time_color, freq_color])

        self.canvas.plot(freq,
                         [[None for _ in range(len(freq))], spectrum],
                         color_names=[time_color, freq_color])

        self.canvas.set_axis_labels(x_label=['Время (с)', 'Частота (Гц)'])
        self.canvas.suptitle(suptitle, weight='bold', fontsize=16)
        self.canvas.grid_all_axes()
        self.canvas.tight_layout()

    def show_plot(self):
        if self._spectrum_calculated:
            self.canvas.show()
        else:
            raise RuntimeError('Visualise data before show_plot()')


if __name__ == "__main__":
    fs = 1000 # Частота дискретизации, Гц
    t = np.arange(0, 1, 1/fs) # 1 секунда сигнала

    # Создаем сигнал с несколькими частотными компонентами
    components = [
        (1.0, 5), # амплитуда 1.0, частота 5 Гц
        (0.5, 50), # амплитуда 0.5, частота 50 Гц
        (0.3, 120), # амплитуда 0.3, частота 120 Гц
    ]

    signal = np.zeros_like(t)
    for amplitude, freq in components:
        signal += amplitude * np.sin(2 * np.pi * freq * t)

    # Добавляем шум
    signal += 0.2 * np.random.randn(len(t))

    analyser = FrequencyAnalyser(signal, t, fs)
    analyser.visualisation(suptitle='Частотный анализ', time_color='tab:green')
    analyser.show_plot()
