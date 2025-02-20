# encoding = utf-8

import os
import wx
import sys
import time
import shutil
import fnmatch
import logging
import datetime
import platform
import threading
import configparser
from pathlib import Path
from pystray import Icon, Menu, MenuItem
from PIL import Image



def resource_path(relative_path, is_output_dir=False):
    """
    Возвращает абсолютный путь к ресурсам, работающий как для скрипта, так и для .exe.
    
    :param relative_path: Относительный путь к ресурсу.
    :param is_output_dir: Если True, возвращает путь к директории, где находится .exe-файл.
                          Если False, возвращает путь к временной директории _MEIPASS.
    """
    try:
        # Если программа запущена как .exe (PyInstaller)
        if hasattr(sys, "_MEIPASS"):
            if is_output_dir:
                base_path = Path(os.path.dirname(sys.executable))  # Директория .exe
            else:
                base_path = Path(sys._MEIPASS)  # Временная директория
        else:
            # Если программа запущена как скрипт
            base_path = Path(os.path.abspath(__file__)).parent  # Директория скрипта

        return os.path.join(base_path, relative_path)
    except Exception as e:
        logging.error(f"Ошибка при определении пути к ресурсу: {e}")
        raise


def get_days_ending(number):
    if number % 100 in [11, 12, 13, 14]:  # Обработка исключений для чисел 11-14
        return "дней"
    elif number % 10 == 1:  # Числа, заканчивающиеся на 1 (кроме 11)
        return "день"
    elif number % 10 in [2, 3, 4]:  # Числа, заканчивающиеся на 2, 3, 4 (кроме 12, 13, 14)
        return "дня"
    else:
        return "дней"


class Mr_Clean:
    def __init__(self):
        """
        Инициализация программы.
        """
        self.PROGRAM_NAME = "Mr. Clean"
        self.PROGRAM_VERSION = "1.2"

        # Временный базовый логгер
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        logging.getLogger("PIL").setLevel(logging.INFO)
        self.logger = logging.getLogger(__name__)  # Используется до setup_logging()

        try:
            self.create_default_configs()  # Создание файлов конфигурации, если они отсутствуют

            # Загрузка конфигураций
            self.config = self.load_config("config.cfg")
            self.values_config = self.load_config("values.ini")

            # Инициализация параметров
            self.cycle_time_limit_sec = int(self.config["SETTINGS"]["cycle-time-limit-sec"])
            self.logging_enabled = self.config["LOG"]["logging"].lower() == "true"
            self.log_level = self.config["LOG"]["log-level"].upper()
            self.log_days_limit = int(self.config["LOG"]["log-days-limit"])

            # Создаем GUI окно
            self.app = wx.App(False)
            self.main_window = MainWindow(
                None,
                title=f"{self.PROGRAM_NAME} v{self.PROGRAM_VERSION}",
                log_level=self.log_level  # Передаем уровень логирования
            )
            #self.main_window.Show(False)  # Сначала скрываем окно

            self.setup_logging()  # Настройка основного логгера
            self.icon = self.tray_start_mr_clean()  # Создание иконки в системном трее
            self.is_forced_exit = False  # Флаг для проверки принудительного выхода

        except KeyError as e:
            self.logger.error(f"Критическая ошибка: Отсутствует ключ {e} в конфигурационном файле.")
            raise
        except Exception as e:
            self.logger.critical(f"Произошла критическая ошибка: {e}")
            raise


    def load_config(self, config_file):
        """
        Загрузка конфигурации из файла.
        """
        self.logger.debug(f"Загрузка конфигурации из файла: {config_file}")
        config = configparser.ConfigParser()

        # Проверяем, существует ли файл
        if not Path(config_file).exists():
            self.logger.error(f"Файл {config_file} не найден.")
            raise FileNotFoundError(f"Файл {config_file} не найден.")

        # Читаем файл
        config.read(config_file, encoding="utf-8")
        return config


    def setup_logging(self):
        """
        Настройка логирования.
        """
        if self.logging_enabled:
            # Очистка существующих обработчиков логгера
            logging.getLogger().handlers.clear()

            # Использование resource_path для определения базовой директории для логов
            base_path = Path(resource_path(".", is_output_dir=True))
            log_folder = base_path / "LOGS"
            
            if not log_folder.exists():
                self.logger.warning(f"Папка LOGS не найдена. Создание папки {log_folder}.")
                log_folder.mkdir(exist_ok=True)

            log_file = log_folder / f"Mr. Clean {datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.log"

            # Настройка формата логов
            logging.basicConfig(
                level=self.log_level,
                format="%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                handlers=[
                    logging.FileHandler(log_file, encoding="utf-8"),  # Логи в файл
                    logging.StreamHandler()  # Логи в консоль
                ]
            )

            # Добавляем обработчик для вывода логов в GUI
            if hasattr(self, "main_window") and self.main_window:
                gui_handler = CustomLogHandler(self.main_window.log_text)
                gui_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
                logging.getLogger().addHandler(gui_handler)

            self.logger = logging.getLogger(__name__)
            self.logger.debug(f"Настройка логирования выполнена. Логи будут записаны в: {log_file}")


    def tray_start_mr_clean(self):
        """
        Создание иконки в системном трее.
        """
        self.logger.debug("Создание иконки в системном трее.")
        # Получаем путь к иконке через resource_path
        icon_path = resource_path("out" + os.sep + "Mr_Clean.ico")
        self.logger.debug(f"Иконка загружается из: {icon_path}")

        image = Image.open(icon_path)

        # Создание подменю "О программе"
        # about_menu = Menu(
        #     MenuItem("AlexBor", None),
        #     MenuItem(f"{self.PROGRAM_NAME} v{self.PROGRAM_VERSION}", None)
        # )

        icon = Icon(
            "Mr. Clean",
            image,
            menu=Menu(
                MenuItem("Показать", lambda icon, item: self.show_gui(), default=True),  # Пункт "Показать"
                # MenuItem("О программе", about_menu),  # Выпадающее меню "О программе"
                MenuItem("О программе", lambda icon, item: os.system(f'start "" "https://github.com/AlexBor-89/Mr_Clean"')),
                Menu.SEPARATOR,  # Добавление разделителя
                MenuItem("Выход", lambda icon, item: self.tray_stop_mr_clean(icon, exit_source="manual")),  # Пункт "Выход"
            ),
        )
        return icon


    def show_gui(self):
        """
        Отображает GUI окно.
        """
        if not self.main_window.IsShown():
            wx.CallAfter(self.main_window.Show, True)  # Показываем окно
            wx.CallAfter(self.main_window.Raise)       # Поднимаем окно наверх

            # Если обработчик ещё не добавлен, добавляем его
            if not any(isinstance(h, CustomLogHandler) for h in logging.getLogger().handlers):
                gui_handler = CustomLogHandler(self.main_window.log_text)
                gui_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
                logging.getLogger().addHandler(gui_handler)


    def tray_stop_mr_clean(self, icon, exit_source="auto"):
        """
        Завершение программы через иконку в трее или после завершения всех процедур.
        
        :param icon: Иконка в системном трее.
        :param exit_source: Источник вызова ("manual" - через кнопку, "auto" - автоматически).
        """
        self.is_forced_exit = exit_source == "manual"  # Устанавливаем флаг принудительного выхода при ручном вызове

        self.logger.info("(\\_/)")
        self.logger.info("(•.•)")
        self.logger.info("/> @>-")

        if exit_source == "manual":
            self.logger.warning("Принудительное завершение очистки.")
        else:
            self.logger.info("Очистка завершена.")
        time.sleep(5)

        try:  # Закрываем главное окно, если оно существует
            if self.main_window:
                # Удаляем обработчик логов для GUI
                for handler in logging.getLogger().handlers:
                    if isinstance(handler, CustomLogHandler):
                        logging.getLogger().removeHandler(handler)
                self.main_window.Destroy()
        except Exception as e:
            self.logger.debug(f"Ошибка при закрытии главного окна: {e}")

        try:  # Останавливаем иконку в трее
            if icon:
                icon.stop()
                # self.logger.debug("Иконка остановлена.")
        except Exception as e:
            self.logger.debug(f"Ошибка при остановке иконки в трее: {e}")

        try:  # Корректно завершаем MainLoop
            if self.app and self.app.IsMainLoopRunning():
                wx.CallAfter(self.app.ExitMainLoop)
        except Exception as e:
            self.logger.debug("Ошибка при завершении MainLoop: {e}")

        # Безопасное завершение программы
        #if threading.current_thread() is threading.main_thread():
        if exit_source == "auto":
            sys.exit()
        #else:
        #    os._exit(0)  # Принудительное завершение, если мы не в основном потоке


    def get_creation_time(self, file_path):  # Функция для получения времени создания файла (кроссплатформенная)
        """
        Получает время создания файла, используя st_birthtime на macOS/Linux и st_ctime на Windows.
        """
        if platform.system() == "Windows":
            # На Windows st_ctime возвращает время создания файла
            return os.path.getctime(file_path)
        else:
            # На macOS/Linux используем st_birthtime, если доступно
            try:
                stats = os.stat(file_path)
                if hasattr(stats, 'st_birthtime'):
                    return stats.st_birthtime
                else:
                    # Если st_birthtime недоступно, используем st_mtime (время последней модификации)
                    return stats.st_mtime
            except Exception as e:
                raise ValueError(f"Не удалось получить время создания файла: {e}")


    def safe_remove(self, path, is_dir=False):
        """
        Безопасное удаление файла или папки.
        """
        try:
            if is_dir:
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.logger.info(f"Удалён {'каталог' if is_dir else 'файл'}: {path}")
            print(f"Удалён {'каталог' if is_dir else 'файл'}: {path}")  # Вывод в консоль
        except PermissionError as e:
            self.logger.error(f"Ошибка доступа: {path}. {e}")
        except FileNotFoundError:
            self.logger.warning(f"Файл или каталог не найден: {path}")
        except Exception as e:
            self.logger.error(f"Неизвестная ошибка при удалении {path}: {e}")


    def clean_logs_folder(self):
        """
        Очистка старых логов.
        """
        self.logger.debug(f"Очистка старых логов.")

        # Определение директории LOGS
        base_path = Path(resource_path(".", is_output_dir=True))
        log_folder = base_path / "LOGS"

        if not log_folder.exists():
            self.logger.warning(f"Папка LOGS не найдена. Создание папки {log_folder}.")
            log_folder.mkdir(exist_ok=True)
        else:
            self.logger.info("~ ~ ~ ~ ~ ~ ~ ~ ~ ~")
            self.logger.info(f"Сканируется папка: {log_folder}. Период хранения: {self.log_days_limit} {get_days_ending(self.log_days_limit)}.")

            date = datetime.datetime.now() - datetime.timedelta(days=self.log_days_limit)
            for log_file in log_folder.glob("*.log"):
                creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(log_file))
                if creation_date < date:
                    self.safe_remove(log_file)


    def delete_files_and_folders(self, path, date):  # Метод 0
        """
        Удаляет файлы и папки с вложенными файлами, если они старше указанного количества дней.
        """
        time_checker = TimeChecker(self.cycle_time_limit_sec)
        time_checker.start()

        try:
            creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(path))
            if creation_date < date:
                self.safe_remove(path, is_dir=True)
        except Exception as e:
            self.logger.error(f"Ошибка при обработке папки {path}: {e}")
        finally:
            time_checker.stop_event.set()
            time_checker.join()

    def delete_only_folders(self, path, date):  # Метод 1
        """
        Удаляет только папки с вложенными файлами, если они старше указанного количества дней.
        """
        time_checker = TimeChecker(self.cycle_time_limit_sec)
        time_checker.start()

        for root, dirs, _ in os.walk(path):
            if self.is_forced_exit:
                return
    
            for dir_name in dirs:
                if self.is_forced_exit:
                    return

                if time_checker.is_time_up():
                    self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. - пропускаем.")
                    time_checker.stop_event.set()
                    return

                dir_path = os.path.join(root, dir_name)
                try:
                    creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(dir_path))
                    if creation_date < date:
                        self.safe_remove(dir_path, is_dir=True)
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке папки {dir_path}: {e}")

        time_checker.stop_event.set()
        time_checker.join()

    def delete_only_files(self, path, date, mask_patterns):  # Метод 2
        """
        Удаляет только файлы по указанному пути, если они старше указанного количества дней.
        """
        time_checker = TimeChecker(self.cycle_time_limit_sec)
        time_checker.start()

        for root, _, files in os.walk(path):
            if self.is_forced_exit:
                return
    
            for file_name in files:
                if self.is_forced_exit:
                    return

                if time_checker.is_time_up():
                    self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. - пропускаем.")
                    time_checker.stop_event.set()
                    return

                file_path = os.path.join(root, file_name)

                # Проверяем, соответствует ли файл шаблонам Mask
                if not any(fnmatch.fnmatch(file_name.lower(), pattern.lower()) for pattern in mask_patterns):
                    continue
                try:
                    creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(file_path))
                    if creation_date < date:
                        self.safe_remove(file_path)
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке файла {file_path}: {e}")

        time_checker.stop_event.set()
        time_checker.join()

    def delete_files_in_subfolders(self, path, date, mask_patterns):  # Метод 3
        """
        Рекурсивное удаление файлов в подпапках.
        """
        self.logger.debug(f"Начинается рекурсивное удаление файлов в подпапке: {path}.")
        time_checker = TimeChecker(self.cycle_time_limit_sec)
        time_checker.start()

        for item in os.listdir(path):
            if self.is_forced_exit:
                return
            
            if time_checker.is_time_up():
                self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. - пропускаем.")
                break

            item_path = os.path.join(path, item)

            if os.path.isdir(item_path):
                # Сброс таймера перед обработкой нового каталога
                time_checker.reset_timer()
                self.logger.info("~ ~ ~ ~ ~ ~ ~ ~ ~ ~")
                self.logger.info(f"Сканируется подпапка: {item_path}.")
                self.delete_files_in_subfolders(item_path, date, mask_patterns)
            elif os.path.isfile(item_path):
                try:
                    if time_checker.is_time_up():
                        self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. - пропускаем.")
                        break

                    creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(item_path))

                    # Проверяем, соответствует ли файл шаблонам Mask
                    if mask_patterns == ["*.*"]:
                        # Если маска равна "*.*", удаляем все файлы без проверки
                        if os.path.isfile(item_path):
                            if creation_date < date:
                                self.safe_remove(item_path)
                    else:
                        # Иначе проверяем соответствие маске
                        if os.path.isfile(item_path) and mask_patterns and any(fnmatch.fnmatch(os.path.basename(item_path), pattern) for pattern in mask_patterns):
                            if creation_date < date:
                                self.safe_remove(item_path)
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке файла: {item_path}: {e}")

        time_checker.stop_event.set()
        time_checker.join()

    def delete_only_files_in_folder(self, path, date, mask_patterns):  # Метод 4
        """
        Удаление только файлов в указанной папке, без удаления каталогов.
        """
        self.logger.debug(f"Начинается удаление файлов в папке {path}, сохраняя структуру каталогов.")
        time_checker = TimeChecker(self.cycle_time_limit_sec)
        time_checker.start()

        for root, _, files in os.walk(path):
            if self.is_forced_exit:
                return

            for file_name in files:
                if self.is_forced_exit:
                    return
        
                if time_checker.is_time_up():
                    self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. - пропускаем.")
                    time_checker.stop_event.set()
                    return  # Прерываем выполнение, если время истекло

                file_path = os.path.join(root, file_name)

                # Проверяем, соответствует ли файл шаблонам Mask
                if not any(fnmatch.fnmatch(file_name.lower(), pattern.lower()) for pattern in mask_patterns):
                    continue

                try:
                    creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(file_path))
                    if creation_date < date:
                        self.safe_remove(file_path)
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке файла {file_path}: {e}")

            # Сброс таймера после обработки каждой папки (опционально)
            time_checker.reset_timer()

        # Останавливаем time_checker после завершения
        time_checker.stop_event.set()
        time_checker.join()
    

    def get_mask_patterns(self, path):
        """
        Возвращает список шаблонов Mask для заданного пути.
        """
        section = None
        for sec in self.values_config.sections():
            if os.path.normcase(os.path.expandvars(self.values_config.get(sec, "Path").strip('"'))) == os.path.normcase(path):
                section = sec
                break

        if section and "Mask" in self.values_config[section]:
            mask_str = self.values_config[section]["Mask"]
            return [pattern.strip() for pattern in mask_str.split(",") if pattern.strip()]
        return ["*.*"]  # Если нет Mask, удаляем все файлы


    def start_mr_clean(self):
        """
        Основной метод для запуска очистки.
        """
        self.logger.debug(f"Основной метод для запуска очистки.")

        methods = ["Методы:",
            "0 - удаляет файлы и папки с вложенными файлами.",
            "1 - удаляет только папки с вложенными файлами.",
            "2 - удаляет только файлы по указанному пути.",
            "3 - удаляет только файлы в подпапках, но не сами подпапки.",
            "4 - удаляет все файлы в папке и в подпапках, с сохранением структуры папок.",
            "Начало очистки"]
        for method in methods:
            self.logger.info(method)

        self.clean_logs_folder()

        for section in self.values_config.sections():
            if self.is_forced_exit:  # Проверяем флаг остановки
                return

            path = os.path.expandvars(self.values_config.get(section, "Path").strip('"'))
            method = self.values_config.get(section, "Method")
            days = int(self.values_config.get(section, "Days"))
            date = datetime.datetime.now() - datetime.timedelta(days=days)
            mask_patterns = self.get_mask_patterns(path)  # Получаем значение Mask для текущего пути

            self.logger.info("~ ~ ~ ~ ~ ~ ~ ~ ~ ~")
            if not os.path.exists(path):
                self.logger.warning(f"Папка {path} не найдена.")
                continue

            self.logger.info(
                f"Сканируется папка: {path}." +
                f" Метод: {method}." +
                f" Период хранения: {days} {get_days_ending(days)}." +
                f" Маска: {", ".join(mask_patterns)}."
            )
            if method == "0":
                self.delete_files_and_folders(path, date)
            elif method == "1":
                self.delete_only_folders(path, date)
            elif method == "2":
                self.delete_only_files(path, date, mask_patterns)
            elif method == "3":
                self.delete_files_in_subfolders(path, date, mask_patterns)
            elif method == "4":
                self.delete_only_files_in_folder(path, date, mask_patterns)
        
        # Автоматическое завершение программы после завершения очистки
        self.tray_stop_mr_clean(None, exit_source="auto")


    def create_default_configs(self):
        """
        Создание файлов config.cfg и values.ini с параметрами по умолчанию, если они не существуют в рабочей директории.
        """
        # Определение базовой директории
        if hasattr(sys, "_MEIPASS"):
            # Если программа запущена как .exe (PyInstaller)
            base_path = Path(sys._MEIPASS)  # Путь к временной директории
            output_dir = Path(os.path.dirname(sys.executable))  # Директория, где находится .exe
        else:
            # Если программа запущена как скрипт
            base_path = Path(os.path.abspath("."))
            output_dir = base_path

        # Путь к config.cfg
        config_file_path = output_dir / "config.cfg"
        if not config_file_path.exists():
            self.logger.info(f"Файл config.cfg не найден. Создание файла с параметрами по умолчанию.")
            default_config_content = """\
[SETTINGS]
# Максимальное время (в секундах), которое программа может тратить на обработку одного каталога или подкаталога.
cycle-time-limit-sec = 180

[LOG]
# Включение (True) или отключение (False) логирования.
logging = True
# Уровень детализации логов. Доступные значения: DEBUG, INFO, WARNING, ERROR, CRITICAL
log-level = INFO
# Все логи старше указанного количества дней будут автоматически удалены.
log-days-limit = 7
"""
            with open(config_file_path, "w", encoding="utf-8") as config_file:
                config_file.write(default_config_content)

        # Путь к values.ini
        values_file_path = output_dir / "values.ini"
        if not values_file_path.exists():
            self.logger.info(f"Файл values.ini не найден. Создание файла с параметрами по умолчанию.")
            default_values_content = """\
# Методы:
# 0 - удаляет файлы и папки с вложенными файлами.
# 1 - удаляет только папки с вложенными файлами.
# 2 - удаляет только файлы по указанному пути.
# 3 - удаляет только файлы в подпапках, но не сами подпапки.
# 4 - удаляет все файлы в папке и в подпапках, с сохранением структуры папок.

# Произвольное имя секции
[Folder Logs]
# Путь к очищаемой папке
Path = "C:\\Logs"
# Метод удаления
Method = 2
# Количество дней, за которые нужно оставить папки и файлы и не удалять их
Days = 7
# Удаление файлов на основе масок имён и расширений
Mask = *.log

[Folder_Temp]
Path = %%TEMP%%
Method = 4
Days = 30
Mask = *.tmp, *.log
"""
            with open(values_file_path, "w", encoding="utf-8") as values_file:
                values_file.write(default_values_content)

        # Добавляем задержку для завершения записи файлов
        time.sleep(1)  # Задержка в 1 секунду



class TimeChecker(threading.Thread):
    def __init__(self, time_limit):
        super().__init__()
        self.time_limit = time_limit
        self.stop_event = threading.Event()
        self.start_time = time.monotonic()
        self.lock = threading.Lock()


    def run(self):
        while not self.stop_event.is_set():
            with self.lock:
                current_time = time.monotonic()
                if current_time - self.start_time >= self.time_limit:
                    self.stop_event.set()
                    break
            time.sleep(0.1)  # Интервал проверки


    def reset_timer(self):
        with self.lock:
            self.start_time = time.monotonic()


    def is_time_up(self):
        with self.lock:
            return self.stop_event.is_set()


    
class MainWindow(wx.Frame):
    def __init__(self, parent, title, log_level):
        super(MainWindow, self).__init__(parent, title=title, size=(800, 600), 
                                         style=wx.DEFAULT_FRAME_STYLE & ~wx.RESIZE_BORDER & ~wx.MAXIMIZE_BOX)
        
        # Создаем панель
        panel = wx.Panel(self)

        # Статический текст для заголовка
        text = wx.StaticText(panel, label="Mr. Clean — это автоматизированная программа для очистки файлов и папок на компьютере.", pos=(15, 10))
        text = wx.StaticText(panel, label=f"Журнал действий (уровень журналирования: {log_level}):", pos=(15, 30))

        # Кнопка закрытия
        button_close = wx.Button(panel, label="Закрыть", pos=(700, 530))
        button_close.Bind(wx.EVT_BUTTON, self.on_close)

        # Текстовое поле для вывода логов
        self.log_text = wx.TextCtrl(
            panel,
            pos=(10, 50),
            size=(760, 470),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )

        # Устанавливаем иконку для окна
        self.set_icon()

        # Привязка обработчика события EVT_CLOSE
        self.Bind(wx.EVT_CLOSE, self.on_close_event)


    def set_icon(self):
        """
        Устанавливает иконку для окна.
        """
        icon_path = resource_path("out" + os.sep + "Mr_Clean.ico")
        icon = wx.Icon(icon_path, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)


    def on_close(self, event):
        """
        Скрываем окно.
        """
        self.Show(False)


    def on_close_event(self, event):
        """
        Обработчик события закрытия окна через крестик.
        """
        self.Show(False)  # Просто скрываем окно вместо его уничтожения
        event.Skip(False)  # Останавливаем стандартное поведение (уничтожение окна)



class CustomLogHandler(logging.Handler):
    def __init__(self, text_ctrl):
        super().__init__()
        self.text_ctrl = text_ctrl


    def emit(self, record):
        msg = self.format(record)
        # Обновляем текстовое поле через wx.CallAfter для безопасности
        wx.CallAfter(self.text_ctrl.AppendText, msg + "\n")



if __name__ == "__main__":
    # Временный базовый логгер
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
    
    try:
        logging.debug("Запуск программы.")
        logging.debug(f"Текущая директория .exe-файла: {Path(resource_path(".", is_output_dir=True))}")
        logging.debug(f"Текущая временная директория: {Path(resource_path("."))}")

        scraper = Mr_Clean()

        # Создаём потоки
        thread1 = threading.Thread(target=scraper.icon.run)
        thread2 = threading.Thread(target=scraper.start_mr_clean)

        # Запускаем потоки
        thread1.start()
        thread2.start()

        # Запускаем цикл событий wxPython
        scraper.app.MainLoop()

        # Ожидаём завершения второго потока (основной очистки)
        thread2.join()
        if not scraper.is_forced_exit:
            try:  # Останавливаем иконку в трее
                scraper.icon.stop()  # Останавливаем иконку в трее, если выход не принудительный
            except Exception as e:
                logging.debug(f"Ошибка при остановке иконки в трее: {e}")
        thread1.join()
        scraper.logger.debug(f"Завершение программы.")
        os._exit(0)

    except Exception as e:
        logging.critical(f"Произошла критическая ошибка: {e}")
        sys.exit(1)  # Корректное завершение программы с кодом ошибки