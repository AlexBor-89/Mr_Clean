# encoding = utf-8

# Стандартные библиотеки Python
import os  # Используется для работы с операционной системой, файловой системой и путями.
import wx  # Библиотека для создания графического интерфейса пользователя (GUI).
import sys  # Предоставляет доступ к некоторым переменным и функциям, взаимодействующим с интерпретатором Python.
import time  # Модуль для работы со временем, включая задержки и измерение времени.
# import ctypes  # Модуль, который позволяет вызывать функции из динамически загружаемых библиотек (DLL на Windows, .so на Linux).
import shutil  # Предназначен для высокого уровня операций с файлами и каталогами, таких как копирование, удаление и перемещение.
import fnmatch  # Модуль для сравнения строк с шаблонами UNIX-стиля (*, ?, [seq], [!seq]).
import logging  # Стандартный модуль для логирования событий программы.
import datetime  # Модуль для работы с датой и временем.
import platform  # Модуль для определения информации об операционной системе.
import threading  # Модуль для работы с потоками выполнения.
import configparser  # Модуль для чтения и записи конфигурационных файлов.
from pathlib import Path  # Объектно-ориентированный подход к работе с путями файловой системы.

# Внешние библиотеки
from pystray import Icon, Menu, MenuItem  # Библиотека для создания иконок в системном трее.
from PIL import Image  # Библиотека для обработки изображений.



def resource_path(relative_path, is_output_dir=False):
    """
    Возвращает абсолютный путь к ресурсам, работающий как для скрипта, так и для .exe.
    
    :param relative_path: Относительный путь к ресурсу.
    :param is_output_dir: Если True, возвращает путь к директории, где находится .exe-файл.
                          Если False, возвращает путь к временной директории _MEIPASS.
    """
    try:
        if hasattr(sys, "_MEIPASS"):  # Если программа запущена как .exe (PyInstaller)
            if is_output_dir:
                base_path = Path(os.path.dirname(sys.executable))  # Директория .exe
            else:
                base_path = Path(sys._MEIPASS)  # Временная директория
        else:  # Если программа запущена как скрипт
            base_path = Path(os.path.abspath(__file__)).parent  # Директория скрипта

        return os.path.join(base_path, relative_path)
    except Exception as e:
        logging.error(f"Ошибка при определении пути к ресурсу: {e}")
        raise


def get_days_ending(number):
    """
    Определение правильного склонения слова "день" в зависимости от переданного числа.
    """
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
        self.PROGRAM_VERSION = "1.3"

        # Временный базовый логгер
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        logging.getLogger("PIL").setLevel(logging.INFO)
        self.logger = logging.getLogger(__name__)  # Используется до setup_logging()

        try:
            self.create_default_configs()  # Создание файлов конфигурации, если они отсутствуют

            # Загрузка конфигураций
            config_file = resource_path("config.cfg", is_output_dir=True)
            values_file = resource_path("values.ini", is_output_dir=True)

            self.config = self.load_config(config_file)
            self.values_config = self.load_config(values_file)

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
                log_level=self.log_level,  # Передаем уровень логирования
                mr_clean_instance=self  # Передаем ссылку на себя
            )

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

        if not Path(config_file).exists():  # Проверяем, существует ли файл
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
            # Использование resource_path для определения базовой директории для логов
            base_path = Path(resource_path(".", is_output_dir=True))
            log_folder = base_path / "LOGS"
            
            if not log_folder.exists():
                logging.warning(f"Каталог LOGS не найден. Создание каталога: {log_folder}.")
                log_folder.mkdir(exist_ok=True)

            log_file = log_folder / f"Mr. Clean {datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.log"

            # Очистка существующих обработчиков логгера
            logging.getLogger().handlers.clear()

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

        self.icon = Icon(
            "Mr. Clean",
            image,
            menu=Menu(
                MenuItem("Показать", lambda icon, item: self.show_gui(), default=True),
                MenuItem("О программе", lambda icon, item: os.system(f'start "" "https://github.com/AlexBor-89/Mr_Clean"')),
                Menu.SEPARATOR,
                MenuItem("Выход", lambda icon, item: self.tray_stop_mr_clean(self.icon, exit_source="manual")),
            ),
        )
        return self.icon


    def show_gui(self):
        """
        Отображает GUI окно.
        """
        if not self.main_window.IsShown():
            wx.CallAfter(self.main_window.Show, True)  # Показываем окно
            wx.CallAfter(self.main_window.Raise)  # Поднимаем окно наверх

            # Если обработчик ещё не добавлен, добавляем его
            if not any(isinstance(h, CustomLogHandler) for h in logging.getLogger().handlers):
                gui_handler = CustomLogHandler(self.main_window.log_text)
                gui_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
                logging.getLogger().addHandler(gui_handler)


    def tray_stop_mr_clean(self, icon=None, exit_source="auto"):
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

        def delayed_shutdown():
            try:  # Закрываем главное окно, если оно существует
                if self.main_window:
                    # Удаляем обработчик логов для GUI
                    for handler in logging.getLogger().handlers:
                        if hasattr(handler, "flush"):
                            handler.flush()
                        if isinstance(handler, CustomLogHandler):
                            logging.getLogger().removeHandler(handler)
                    self.main_window.Destroy()
            except Exception as e:
                self.logger.debug(f"Ошибка при закрытии главного окна: {e}")

            try:  # Останавливаем иконку в трее
                if icon and icon.visible:
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
            if exit_source == "auto":
                sys.exit()

        # Выполняем shutdown через главный поток с задержкой в 3 секунды
        if threading.current_thread() is threading.main_thread():  # Через окно (Завершить работу)
            wx.CallLater(3000, delayed_shutdown)
        else:  # Через трей (Выход)
            time.sleep(3)
            delayed_shutdown()


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
        Метод предназначен для безопасного удаления файлов или каталогов.
        """
        try:
            if is_dir:
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.logger.info(f"Удалён {'каталог' if is_dir else 'файл'}: {path}")
            print(f"Удалён {'каталог' if is_dir else 'файл'}: {path}")  # Вывод в консоль
        except PermissionError as e:
            self.logger.error(f"Ошибка доступа при обработке {path}: {e}")
        except FileNotFoundError:
            self.logger.warning(f"Файл или каталог не найден: {path}")
        except Exception as e:
            self.logger.error(f"Ошибка при обработке {path}: {e}")


    def clean_logs_folder(self):
        """
        Метод отвечает за очистку старых логов в директории LOGS.
        """
        self.logger.debug(f"Очистка старых логов.")

        # Определение директории LOGS
        base_path = Path(resource_path(".", is_output_dir=True))
        log_folder = base_path / "LOGS"

        if not log_folder.exists():
            self.logger.warning(f"Каталог LOGS не найден. Создание каталога: {log_folder}.")
            log_folder.mkdir(exist_ok=True)
        else:
            # Проверяем права доступа к каталогу LOGS
            if not os.access(log_folder, os.R_OK | os.W_OK):
                self.logger.error(f"Недостаточно прав для чтения/записи в каталоге LOGS: {log_folder} — пропускаем очистку.")
                return

            self.logger.info("~ ~ ~ ~ ~ ~ ~ ~ ~ ~")
            self.logger.info(f"Сканируется каталог: {log_folder}. Период хранения: {self.log_days_limit} {get_days_ending(self.log_days_limit)}.")

            date = datetime.datetime.now() - datetime.timedelta(days=self.log_days_limit)

            for log_file in log_folder.glob("*.log"):  # Проходим по всем файлам в каталоге LOGS
                try:
                    # Проверяем права доступа к каждому файлу
                    if not os.access(log_file, os.R_OK | os.W_OK):
                        self.logger.warning(f"Файл {log_file} недоступен — пропускаем.")
                        continue

                    creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(log_file))
                    if creation_date < date:
                        self.safe_remove(log_file)
                except PermissionError as e:
                    self.logger.error(f"Ошибка доступа при обработке файла {log_file}: {e}")
                except FileNotFoundError:
                    self.logger.warning(f"Файл не найден: {log_file}")
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке файла {log_file}: {e}")


    def delete_files_and_folders(self, path, date):  # Метод 0
        """
        Удаляет файлы и каталоги с вложенными файлами, если они старше указанного количества дней.
        """
        time_checker = TimeChecker(self.cycle_time_limit_sec)
        time_checker.start()

        try:
            for root, dirs, files in os.walk(path, topdown=False):
                if self.is_forced_exit:
                    return

                if time_checker.is_time_up():
                    self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. — пропускаем.")
                    break

                if not os.access(root, os.R_OK | os.W_OK):  # Проверяем доступ к текущей директории
                    self.logger.error(f"Недостаточно прав для чтения/записи в директории: {root} — пропускаем.")
                    continue

                for file_name in files:  # Обработка файлов
                    if self.is_forced_exit:
                        return
                    
                    file_path = os.path.join(root, file_name)

                    # Проверяем существование файла и права доступа
                    if not os.path.exists(file_path) or not os.access(file_path, os.R_OK | os.W_OK):
                        self.logger.warning(f"Файл {file_path} не существует или недоступен — пропускаем.")
                        continue

                    try:
                        creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(file_path))
                        if creation_date < date:
                            self.safe_remove(file_path)
                    except PermissionError as e:
                        self.logger.error(f"Ошибка доступа при обработке: {file_path}. {e}")
                    except FileNotFoundError:
                        self.logger.warning(f"Файл не найден: {file_path}")
                    except Exception as e:
                        self.logger.error(f"Ошибка при обработке файла {file_path}: {e}")

                for dir_name in dirs:  # Обработка каталогов
                    if self.is_forced_exit:
                        return
                    
                    dir_path = os.path.join(root, dir_name)

                    # Проверяем существование каталога и права доступа
                    if not os.path.exists(dir_path) or not os.access(dir_path, os.R_OK | os.W_OK):
                        self.logger.warning(f"Каталог {dir_path} не существует или недоступен — пропускаем.")
                        continue

                    try:
                        creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(dir_path))
                        if creation_date < date:
                            self.safe_remove(dir_path, is_dir=True)
                    except PermissionError as e:
                        self.logger.error(f"Ошибка доступа при обработке: {dir_path}. {e}")
                    except Exception as e:
                        self.logger.error(f"Ошибка при обработке каталога {dir_path}: {e}")

            # Проверяем сам корневой каталог после обработки его содержимого
            if os.path.exists(path) and os.access(path, os.R_OK | os.W_OK):
                creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(path))
                if creation_date < date:
                    self.safe_remove(path, is_dir=True)

        except Exception as e:
            self.logger.error(f"Ошибка при обработке пути {path}: {e}")
        finally:
            time_checker.stop_event.set()
            time_checker.join()


    def delete_only_folders(self, path, date):  # Метод 1
        """
        Удаляет только каталоги с вложенными файлами, если они старше указанного количества дней.
        """
        time_checker = TimeChecker(self.cycle_time_limit_sec)
        time_checker.start()

        try:
            for root, dirs, _ in os.walk(path):
                if self.is_forced_exit:
                    return
                
                if not os.access(root, os.R_OK | os.W_OK):  # Проверяем доступ к текущей директории
                    self.logger.error(f"Недостаточно прав для чтения/записи в директории: {root} — пропускаем.")
                    continue

                for dir_name in dirs:
                    if self.is_forced_exit:
                        return

                    if time_checker.is_time_up():
                        self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. — пропускаем.")
                        time_checker.stop_event.set()
                        return

                    dir_path = os.path.join(root, dir_name)

                    # Проверяем существование каталога и права доступа
                    if not os.path.exists(dir_path) or not os.access(dir_path, os.R_OK | os.W_OK):
                        self.logger.warning(f"Каталог {dir_path} не существует или недоступен — пропускаем.")
                        continue

                    try:
                        creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(dir_path))
                        if creation_date < date:
                            self.safe_remove(dir_path, is_dir=True)
                    except Exception as e:
                        self.logger.error(f"Ошибка при обработке каталога {dir_path}: {e}")

                # Сброс таймера после обработки каждого каталога (опционально)
                time_checker.reset_timer()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке пути {path}: {e}")
        finally:
            time_checker.stop_event.set()
            time_checker.join()


    def delete_only_files(self, path, date, mask_patterns):  # Метод 2
        """
        Удаляет только файлы по указанному пути, если они старше указанного количества дней.
        """
        time_checker = TimeChecker(self.cycle_time_limit_sec)
        time_checker.start()

        try:
            for root, _, files in os.walk(path):
                if self.is_forced_exit:
                    return

                if not os.access(root, os.R_OK | os.W_OK):  # Проверяем доступ к текущей директории
                    self.logger.error(f"Недостаточно прав для чтения/записи в директории: {root} — пропускаем.")
                    continue

                for file_name in files:
                    if self.is_forced_exit:
                        return

                    if time_checker.is_time_up():
                        self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. — пропускаем.")
                        time_checker.stop_event.set()
                        return

                    file_path = os.path.join(root, file_name)

                    # Проверяем существование файла и права доступа
                    if not os.path.exists(file_path) or not os.access(file_path, os.R_OK | os.W_OK):
                        self.logger.warning(f"Файл {file_path} не существует или недоступен — пропускаем.")
                        continue

                    # Проверяем, соответствует ли файл шаблонам Mask
                    if not any(fnmatch.fnmatch(file_name.lower(), pattern.lower()) for pattern in mask_patterns):
                        continue

                    try:
                        creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(file_path))
                        if creation_date < date:
                            self.safe_remove(file_path)
                    except PermissionError as e:
                        self.logger.error(f"Ошибка доступа при обработке файла {file_path}: {e}")
                    except FileNotFoundError:
                        self.logger.warning(f"Файл не найден: {file_path}")
                    except Exception as e:
                        self.logger.error(f"Ошибка при обработке файла {file_path}: {e}")

                # Сброс таймера после обработки каждого каталога (опционально)
                time_checker.reset_timer()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке пути {path}: {e}")
        finally:
            time_checker.stop_event.set()
            time_checker.join()


    def delete_files_in_subfolders(self, path, date, mask_patterns):  # Метод 3
        """
        Рекурсивное удаление файлов в подкаталогах.
        """
        self.logger.debug(f"Начинается рекурсивное удаление файлов в подкаталоге: {path}")
        time_checker = TimeChecker(self.cycle_time_limit_sec)
        time_checker.start()

        try:
            for item in os.listdir(path):
                if self.is_forced_exit:
                    return
                
                if time_checker.is_time_up():
                    self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. — пропускаем.")
                    break

                item_path = os.path.join(path, item)

                if not os.access(item_path, os.R_OK | os.W_OK):  # Проверяем права доступа к текущему элементу
                    self.logger.error(f"Недостаточно прав для чтения/записи в элементе: {item_path} — пропускаем.")
                    continue

                if os.path.isdir(item_path):
                    # Сброс таймера перед обработкой нового каталога
                    time_checker.reset_timer()
                    self.logger.info("~ ~ ~ ~ ~ ~ ~ ~ ~ ~")
                    self.logger.info(f"Сканируется подкаталог: {item_path}")
                    self.delete_files_in_subfolders(item_path, date, mask_patterns)
                elif os.path.isfile(item_path):
                    try:
                        if time_checker.is_time_up():
                            self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. — пропускаем.")
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
                    except PermissionError as e:
                        self.logger.error(f"Ошибка доступа при обработке файла {item_path}: {e}")
                    except FileNotFoundError:
                        self.logger.warning(f"Файл не найден: {item_path}")
                    except Exception as e:
                        self.logger.error(f"Ошибка при обработке файла {item_path}: {e}")

        except Exception as e:
            self.logger.error(f"Ошибка при обработке пути {path}: {e}")
        finally:
            time_checker.stop_event.set()
            time_checker.join()


    def delete_only_files_in_folder(self, path, date, mask_patterns):  # Метод 4
        """
        Удаление только файлов в указанном каталоге, без удаления каталогов.
        """
        self.logger.debug(f"Начинается удаление файлов в каталоге {path}, сохраняя структуру каталогов.")
        time_checker = TimeChecker(self.cycle_time_limit_sec)
        time_checker.start()

        try:
            for root, _, files in os.walk(path):
                if self.is_forced_exit:
                    return
                
                if not os.access(root, os.R_OK | os.W_OK):  # Проверяем доступ к текущей директории
                    self.logger.error(f"Недостаточно прав для чтения/записи в директории: {root} — пропускаем.")
                    continue

                for file_name in files:
                    if self.is_forced_exit:
                        return
            
                    if time_checker.is_time_up():
                        self.logger.warning(f"Цикл {path} работает дольше {self.cycle_time_limit_sec} сек. — пропускаем.")
                        time_checker.stop_event.set()
                        return  # Прерываем выполнение, если время истекло

                    file_path = os.path.join(root, file_name)

                    # Проверяем существование файла и права доступа
                    if not os.path.exists(file_path) or not os.access(file_path, os.R_OK | os.W_OK):
                        self.logger.warning(f"Файл {file_path} не существует или недоступен — пропускаем.")
                        continue

                    # Проверяем, соответствует ли файл шаблонам Mask
                    if not any(fnmatch.fnmatch(file_name.lower(), pattern.lower()) for pattern in mask_patterns):
                        continue

                    try:
                        creation_date = datetime.datetime.fromtimestamp(self.get_creation_time(file_path))
                        if creation_date < date:
                            self.safe_remove(file_path)
                    except PermissionError as e:
                        self.logger.error(f"Ошибка доступа при обработке файла {file_path}: {e}")
                    except FileNotFoundError:
                        self.logger.warning(f"Файл не найден: {file_path}")
                    except Exception as e:
                        self.logger.error(f"Ошибка при обработке файла {file_path}: {e}")

                # Сброс таймера после обработки каждого каталога (опционально)
                time_checker.reset_timer()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке пути {path}: {e}")
        finally:
            # Останавливаем time_checker после завершения
            time_checker.stop_event.set()
            time_checker.join()
    

    def get_mask_patterns(self, path):
        """
        Метод возвращает список шаблонов (Mask) для заданного пути из файла конфигурации values.ini.
        Если шаблоны не указаны, используется значение *.*, что означает удаление всех файлов.
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
        Метод является основной точкой входа для запуска процесса очистки.
        Он перебирает все секции файла values.ini, применяет соответствующие методы очистки и логирует результаты.
        """
        self.logger.info(f"{self.PROGRAM_NAME} v{self.PROGRAM_VERSION}")
        self.logger.debug(f"Основной метод для запуска очистки.")

        methods = ["Методы:",
            "0 - удаляет файлы и каталоги с вложенными файлами.",
            "1 - удаляет только каталоги с вложенными файлами.",
            "2 - удаляет только файлы по указанному пути.",
            "3 - удаляет только файлы в подкаталогах, но не сами подкаталоги.",
            "4 - удаляет все файлы в каталоге и в подкаталогах, с сохранением структуры каталогов.",
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
                self.logger.warning(f"Каталог {path} не найден.")
                continue

            self.logger.info(
                f"Сканируется каталог: {path}." +
                f" Метод: {method}." +
                f" Период хранения: {days} {get_days_ending(days)}." +
                f" Маска: {", ".join(mask_patterns)}."
            )

            try:
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
            except Exception as e:
                self.logger.error(f"Ошибка при обработке секции {section}: {e}")
        
        # Автоматическое завершение программы после завершения очистки
        self.tray_stop_mr_clean(self.icon, exit_source="auto")


    def create_default_configs(self):
        """
        Метод создаёт файлы конфигурации config.cfg и values.ini с параметрами по умолчанию, если они отсутствуют в рабочей директории.
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
# 0 - удаляет файлы и каталоги с вложенными файлами.
# 1 - удаляет только каталоги с вложенными файлами.
# 2 - удаляет только файлы по указанному пути.
# 3 - удаляет только файлы в подкаталогах, но не сами подкаталоги.
# 4 - удаляет все файлы в каталоге и в подкаталогах, с сохранением структуры каталогов.

# Произвольное имя секции
[Folder Logs]
# Путь к очищаемому каталогу
Path = "C:\\Logs"
# Метод удаления
Method = 2
# Количество дней, за которые нужно оставить каталоги и файлы и не удалять их
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
        """
        Метод является основным методом потока, который постоянно проверяет, не превышено ли заданное время (time_limit).
        Если время истекло, устанавливается флаг завершения (stop_event).
        """
        while not self.stop_event.is_set():
            with self.lock:
                current_time = time.monotonic()
                if current_time - self.start_time >= self.time_limit:
                    self.stop_event.set()
                    break
            time.sleep(0.2)  # Интервал проверки


    def reset_timer(self):
        """
        Метод сбрасывает таймер, обновляя начальное время (start_time) на текущее значение.
        Это позволяет повторно запустить отсчет времени без необходимости создавать новый экземпляр класса.
        """
        with self.lock:
            self.start_time = time.monotonic()


    def is_time_up(self):
        """
        Метод проверяет, истекло ли заданное время (time_limit).
        """
        with self.lock:
            return self.stop_event.is_set()


    
class MainWindow(wx.Frame):
    def __init__(self, parent, title, log_level, mr_clean_instance):
        super(MainWindow, self).__init__(parent, title=title, size=(800, 600), 
                                         style=wx.DEFAULT_FRAME_STYLE & ~wx.RESIZE_BORDER & ~wx.MAXIMIZE_BOX)
        
        # Сохраняем ссылку на экземпляр Mr_Clean
        self.mr_clean = mr_clean_instance

        # Создаем панель
        panel = wx.Panel(self)

        # Статический текст для заголовка
        text = wx.StaticText(panel, label="Mr. Clean — это автоматизированная программа для очистки файлов и каталогов на компьютере.", pos=(15, 10))
        text = wx.StaticText(panel, label=f"Журнал действий (уровень журналирования: {log_level}):", pos=(15, 30))

        # Кнопка закрытия
        button_close = wx.Button(panel, label="Закрыть", pos=(700, 530))
        button_close.Bind(wx.EVT_BUTTON, self.on_close)

        # Кнопка завершения работы программы
        button_close = wx.Button(panel, label="Завершить работу", pos=(10, 530))
        button_close.Bind(wx.EVT_BUTTON, self.on_shutdown)

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
        Метод скрывает главное окно программы при нажатии кнопки "Закрыть".
        Это позволяет свернуть программу в системный трей вместо полного закрытия.
        """
        self.Show(False)


    def on_close_event(self, event):
        """
        Метод обрабатывает событие закрытия окна через крестик в верхнем углу.
        Вместо закрытия окно просто скрывается, а программа продолжает работать в фоне.
        """
        self.Show(False)  # Просто скрываем окно вместо его уничтожения
        event.Skip(False)  # Останавливаем стандартное поведение (уничтожение окна)

    def on_shutdown(self, event):
        """
        Метод вызывается при нажатии кнопки "Завершить работу".
        Он инициирует принудительное завершение работы программы через вызов соответствующего метода из класса Mr_Clean.
        """
        if self.mr_clean:
            self.mr_clean.tray_stop_mr_clean(self.mr_clean.icon, exit_source="manual")  # Вызываем метод



class CustomLogHandler(logging.Handler):
    def __init__(self, text_ctrl):
        super().__init__()
        self.text_ctrl = text_ctrl


    def emit(self, record):
        """
        Метод используется для вывода логов в текстовое поле графического интерфейса.
        """
        msg = self.format(record)
        # Обновляем текстовое поле через wx.CallAfter
        wx.CallAfter(self.text_ctrl.AppendText, msg + "\n")



if __name__ == "__main__":
    # if not ctypes.windll.shell32.IsUserAnAdmin():
    #     logging.warning("Программа должна быть запущена с правами администратора для полной функциональности.")

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
        if scraper.icon and scraper.icon.visible:
            try:  # Останавливаем иконку в трее
                scraper.icon.stop()  # Останавливаем иконку в трее, если выход не принудительный
            except Exception as e:
                logging.debug(f"Ошибка при остановке иконки в трее: {e}")     
        
        if not threading.current_thread() is threading.main_thread():
            thread1.join()
        
        scraper.logger.debug(f"Завершение программы.")
        os._exit(0)

    except Exception as e:
        logging.critical(f"Произошла критическая ошибка: {e}")
        sys.exit(1)  # Корректное завершение программы с кодом ошибки