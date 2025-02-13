# encoding = utf-8

import os
import sys
import time
import shutil
import logging
import datetime
import platform
import threading
import configparser
from pathlib import Path
from pystray import Icon, Menu, MenuItem
from PIL import Image

class Mr_Clean:
    def __init__(self):
        """
        Инициализация программы.
        """
        self.PROGRAM_NAME = "Mr. Clean"
        self.PROGRAM_VERSION = "1.1"

        # Временный базовый логгер
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)  # Используется до setup_logging()

        try:
            self.create_default_configs()  # Создание файлов конфигурации, если они отсутствуют

            # Загрузка конфигураций
            self.config = self.load_config("config.cfg")
            self.values_config = self.load_config("values.ini")

            # Инициализация параметров
            self.cycle_time_limit = int(self.config["SETTINGS"]["cycle-time-limit-sec"])
            self.logging_enabled = self.config["LOG"]["logging"].lower() == "true"
            self.log_level = self.config["LOG"]["log-level"].upper()
            self.log_days_limit = int(self.config["LOG"]["log-days-limit"])

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

            # Определение базовой директории для логов
            if hasattr(sys, "_MEIPASS"):
                # Если программа запущена как .exe (PyInstaller)
                output_dir = Path(os.path.dirname(sys.executable))  # Директория, где находится .exe
            else:
                # Если программа запущена как скрипт
                output_dir = Path(os.path.abspath("."))

            log_folder = output_dir / "LOGS"
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
            self.logger = logging.getLogger(__name__)
            self.logger.debug(f"Настройка логирования выполнена. Логи будут записаны в: {log_file}")


    def tray_start_mr_clean(self):
        """
        Создание иконки в системном трее.
        """
        self.logger.debug(f"Создание иконки в системном трее.")
        # Получаем путь к иконке через resource_path
        icon_path = self.resource_path("out" + os.sep + "Mr_Clean.ico")
        self.logger.debug(f"Иконка загружается из: {icon_path}")

        image = Image.open(icon_path)

        # Создание подменю "О программе"
        about_menu = Menu(
            MenuItem("AlexBor", None),
            MenuItem(f"{self.PROGRAM_NAME} v{self.PROGRAM_VERSION}", None)
        )

        icon = Icon(
            "Mr. Clean",
            image,
            menu=Menu(
                MenuItem("О программе", about_menu),  # Выпадающее меню "О программе"
                Menu.SEPARATOR,  # Добавление разделителя
                MenuItem("Выход", self.tray_stop_mr_clean), # Пункт "Выход"
            ),
        )
        return icon


    def resource_path(self, relative_path):
        """
        Возвращает абсолютный путь к ресурсам, работающий как для скрипта, так и для .exe, созданного PyInstaller.
        """
        try:
            # PyInstaller создает временную директорию BASE_PATH и помещает туда ресурсы
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath("." + os.sep)

        return os.path.join(base_path, relative_path)


    def tray_stop_mr_clean(self, icon):
        """
        Завершение программы через иконку в трее.
        """
        self.is_forced_exit = True  # Устанавливаем флаг принудительного выхода
        self.logger.warning("Принудительное завершение программы")
        icon.stop()
        os._exit(0)


    # Функция для получения времени создания файла (кроссплатформенная)
    def get_creation_time(self, file_path):
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
        if hasattr(sys, "_MEIPASS"):
            output_dir = Path(os.path.dirname(sys.executable))
        else:
            output_dir = Path(os.path.abspath("."))

        log_folder = output_dir / "LOGS"
        if not log_folder.exists():
            self.logger.warning(f"Папка LOGS не найдена. Создание папки.")
            log_folder.mkdir(exist_ok=True)

        date = datetime.datetime.now() - datetime.timedelta(days=self.log_days_limit)
        for log_file in log_folder.glob("*.log"):
            creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(log_file))
            if creation_date < date:
                self.safe_remove(log_file)


    def delete_files_in_subfolders(self, folder, start_time):
        """
        Рекурсивное удаление файлов в подпапках.
        """
        date = datetime.datetime.now() - datetime.timedelta(days=self.log_days_limit)
        
        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            
            # Проверка времени выполнения
            if time.monotonic() - start_time >= self.cycle_time_limit:
                self.logger.warning(f"Цикл {folder} работает дольше {self.cycle_time_limit} сек. - пропускаем.")
                break
            if os.path.isdir(item_path):
                self.delete_files_in_subfolders(item_path, start_time)
            elif os.path.isfile(item_path):
                try:
                    creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(item_path))
                    if creation_date < date:
                        self.safe_remove(item_path)
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке файла {item_path}: {e}")


    def start_mr_clean(self):
        """
        Основной метод для запуска очистки.
        """
        self.logger.debug(f"Основной метод для запуска очистки.")
        self.clean_logs_folder()

        self.logger.info("Методы:")
        self.logger.info("0 - удаляет файлы и папки с вложенными файлами.")
        self.logger.info("1 - удаляет только папки с вложенными файлами.")
        self.logger.info("2 - удаляет только файлы по указанному пути.")
        self.logger.info("3 - удаляет только файлы в подпапках, но не сами подпапки.")
        self.logger.info("Начало очистки")

        for section in self.values_config.sections():
            path = os.path.expandvars(self.values_config.get(section, "Path").strip('"'))
            method = self.values_config.get(section, "Method")
            days = int(self.values_config.get(section, "Days"))
            date = datetime.datetime.now() - datetime.timedelta(days=days)

            self.logger.info("~ ~ ~ ~ ~ ~ ~ ~ ~ ~")
            if not os.path.exists(path):
                self.logger.warning(f"Папка {path} не найдена.")
                continue

            self.logger.info(f"Сканируется папка {path}. Метод {method}, Дней {days}.")
            if method == "0":
                try:
                    creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(path))
                    if creation_date < date:
                        self.safe_remove(path, is_dir=True)
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке папки {path}: {e}")
            elif method == "1":
                for root, dirs, _ in os.walk(path):
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(dir_path))
                            if creation_date < date:
                                self.safe_remove(dir_path, is_dir=True)
                        except Exception as e:
                            self.logger.error(f"Ошибка при обработке папки {dir_path}: {e}")
            elif method == "2":
                for root, _, files in os.walk(path):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        try:
                            creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(file_path))
                            if creation_date < date:
                                self.safe_remove(file_path)
                        except Exception as e:
                            self.logger.error(f"Ошибка при обработке файла {file_path}: {e}")
            elif method == "3":
                start_time = time.monotonic()
                self.delete_files_in_subfolders(path, start_time)

        self.logger.info("(\\_/)")
        self.logger.info("(•.•)")
        self.logger.info("/> @>-")
        self.logger.info("Очистка завершена.")
        self.icon.stop()


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
cycle-time-limit-sec = 180

[LOG]
logging = True
log-level = INFO
log-days-limit = 7
"""
            with open(config_file_path, "w", encoding="utf-8") as config_file:
                config_file.write(default_config_content)

        # Путь к values.ini
        values_file_path = output_dir / "values.ini"
        if not values_file_path.exists():
            self.logger.info(f"Файл values.ini не найден. Создание файла с параметрами по умолчанию.")
            default_values_content = """\
[Folder Logs]
Path = "C:\\Logs"
Method = 2
Days = 7

[Folder_Temp]
Path = %%TEMP%%
Method = 0
Days = 30
"""
            with open(values_file_path, "w", encoding="utf-8") as values_file:
                values_file.write(default_values_content)

        # Добавляем задержку для завершения записи файлов
        time.sleep(1)  # Задержка в 1 секунду


if __name__ == "__main__":
    try:
        # Временный базовый логгер
        #logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        #logging.debug("Запуск программы.")

        scraper = Mr_Clean()

        # Создаём потоки
        thread1 = threading.Thread(target=scraper.icon.run)
        thread2 = threading.Thread(target=scraper.start_mr_clean)

        # Запускаем потоки
        thread1.start()
        thread2.start()

        # Ожидаем завершения второго потока (основной очистки)
        thread2.join()
        if not scraper.is_forced_exit:
            scraper.icon.stop()  # Останавливаем иконку в трее, если выход не принудительный
        scraper.logger.debug(f"Завершение программы.")

    except Exception as e:
        #logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        #logging.critical(f"Произошла критическая ошибка: {e}")
        sys.exit(1)  # Корректное завершение программы с кодом ошибки