# Импортируем модули
import os
import time
import shutil
import datetime
import configparser

print("Mr. Clean", "Ver. 1.0", "AlexBor", sep="\n")
time.sleep(2)

# Создаем объект configparser
config = configparser.ConfigParser()

# Читаем файл конфигурации
config.read("config.ini")

# Получаем список имен групп параметров
names = config.sections()


# Определяем функцию для удаления файлов в подпапках
def delete_files_in_subfolders(folder):
    # Проходим по всем элементам в папке
    for item in os.listdir(folder):
        # Получаем полный путь к элементу
        item_path = os.path.join(folder, item)
        # Если элемент - папка, то рекурсивно вызываем функцию для нее
        if os.path.isdir(item_path):
            delete_files_in_subfolders(item_path)
        # Если элемент - файл, то проверяем его дату создания
        elif os.path.isfile(item_path):
            # Получаем время создания файла в секундах
            creation_date = datetime.datetime.fromtimestamp(os.path.getctime(item_path))
            # Если разница больше или равна заданному количеству дней, то удаляем файл
            if creation_date < date:
                try:
                    os.remove(item_path)
                    print(f"Удалён файл {item_path}")
                except (
                    PermissionError
                ) as e:  # Продолжаем работу, не останавливая программу
                    print(f"Не удалось удалить файл {item_path} из-за ошибки: {e}")


# Для каждого имени в списке
for name in names:
    # Получаем путь к папке, метод удаления и количество дней из файла конфигурации
    path = config.get(name, "Path")
    method = config.get(name, "Method")
    days = config.get(name, "Days")
    # Преобразуем количество дней в дату, от которой будем удалять файлы или папки
    date = datetime.datetime.now() - datetime.timedelta(days=int(days))
    # Заменяем системные переменные на их значения в пути
    path = os.path.expandvars(path)
    # Убираем кавычки из пути, если они есть
    path = path.strip('"')
    # Убираем пробелы или символы перевода строки в конце пути
    path = path.rstrip()
    # Проверяем, существует ли папка по указанному пути
    if os.path.exists(path):
        print("~ ~ ~ ~ ~ ~ ~ ~ ~ ~", f"Сканируется папка {path}", sep="\n")
        print(f"Метод {method}, Количество дней {days}")
        # Если метод удаления равен 0, то удаляем всю папку со всем содержимым, если она старше указанной даты
        if (
            method == "0"
            and datetime.datetime.fromtimestamp(os.path.getctime(path)) < date
        ):
            try:
                shutil.rmtree(path)
                print(f"Удалена папка {path} со всем содержимым")
            except PermissionError as e:  # Продолжаем работу, не останавливая программу
                print(f"Не удалось удалить {path} из-за ошибки: {e}")
        # Если метод удаления равен 1, то удаляем только подпапки со всем содержимым, если они старше указанной даты
        elif method == "1":
            # Получаем список подпапок в папке
            subfolders = [
                os.path.join(path, f)
                for f in os.listdir(path)
                if os.path.isdir(os.path.join(path, f))
            ]
            # Для каждой подпапки в списке
            for subfolder in subfolders:
                # Получаем дату создания подпапки и преобразуем значение в дату и время
                creation_date = datetime.datetime.fromtimestamp(
                    os.path.getctime(subfolder)
                )  # abs(os.path.getctime(subfolder))
                # Если подпапка старше указанной даты, то удаляем её со всем содержимым
                if creation_date < date:
                    try:
                        shutil.rmtree(subfolder)
                        print(f"Удалена подпапка {subfolder} со всем содержимым")
                    except (
                        PermissionError
                    ) as e:  # Продолжаем работу, не останавливая программу
                        print(f"Не удалось удалить папку {subfolder} из-за ошибки: {e}")
        # Если метод удаления равен 2, то удаляем только файлы в папке, если они старше указанной даты
        elif method == "2":
            # Получаем список файлов в папке
            files = [
                os.path.join(path, f)
                for f in os.listdir(path)
                if os.path.isfile(os.path.join(path, f))
            ]
            # Для каждого файла в списке
            for file in files:
                # Получаем дату создания файла
                creation_date = datetime.datetime.fromtimestamp(os.path.getctime(file))
                # Если файл старше указанной даты, то удаляем его
                if creation_date < date:
                    try:
                        os.remove(file)
                        print(f"Удалён файл {file}")
                    except (
                        PermissionError
                    ) as e:  # Продолжаем работу, не останавливая программу
                        print(f"Не удалось удалить файл {file} из-за ошибки: {e}")
        elif method == "3":
            # Удаляем только файлы в подпапках, но не сами подпапки
            # Для этого вызываем функцию delete_files_in_subfolders для папки path
            delete_files_in_subfolders(path)
    else:
        # Если папка по указанному пути не существует, то выводим сообщение об ошибке
        print(f"Папка {path} не найдена")

print("Через 1 минуту это окно закроется")
time.sleep(60)
