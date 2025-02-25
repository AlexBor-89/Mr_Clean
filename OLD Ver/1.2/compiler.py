import os
import shutil
import subprocess
import sys

def compile_to_exe():
    print("Проверка наличия PyInstaller...")
    try:
        # Установка зависимостей
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller", "pystray", "Pillow"],
            check=True
        )
    except Exception as e:
        print(f"Ошибка при установке зависимостей: {e}")
        return
    
    # Удаление предыдущих файлов main.exe и Mr_Clean.exe из папки out, если они существуют
    out_folder = "out"
    old_main_exe = os.path.join(out_folder, "main.exe")
    old_mr_clean_exe = os.path.join(out_folder, "Mr_Clean.exe")
    
    if os.path.exists(old_main_exe):
        print("Удаление старого main.exe из папки out...")
        os.remove(old_main_exe)
    
    if os.path.exists(old_mr_clean_exe):
        print("Удаление старого Mr_Clean.exe из папки out...")
        os.remove(old_mr_clean_exe)

    print("Компиляция main.py...")
    try:
        # Список ненужных плагинов PIL
        excluded_pillow_plugins = [
            "BlpImagePlugin", "BmpImagePlugin", "CurImagePlugin", "DcxImagePlugin", "DdsImagePlugin",
            "EpsImagePlugin", "FitsImagePlugin", "FliImagePlugin", "FpxImagePlugin", "GbrImagePlugin",
            "GifImagePlugin", "GribStubImagePlugin", "Hdf5StubImagePlugin", "IcnsImagePlugin", "ImImagePlugin",
            "ImtImagePlugin", "IptcImagePlugin", "Jpeg2KImagePlugin", "McIdasImagePlugin", "MicImagePlugin",
            "MpegImagePlugin", "MspImagePlugin", "PalmImagePlugin", "PcdImagePlugin", "PcxImagePlugin",
            "PdfImagePlugin", "PixarImagePlugin", "PsdImagePlugin", "SgiImagePlugin", "SpiderImagePlugin",
            "SunImagePlugin", "TgaImagePlugin", "TiffImagePlugin", "WebPImagePlugin", "WmfImagePlugin",
            "XbmImagePlugin", "XpmImagePlugin"
        ]
        
        # Команда для PyInstaller
        pyinstaller_command = [
            "pyinstaller",
            "--onefile",  # Создание одного исполняемого файла
            "--windowed",  # Без консольного окна
            f"--icon=out/Mr_Clean.ico",  # Иконка для exe-файла
            "--add-data", "out/Mr_Clean.ico;out",  # Добавление ресурсов
            "--hidden-import=pystray._win32",  # Скрытые импорты
            "--hidden-import=PIL.Image",
            "--clean",  # Очистка кэша перед сборкой
            "main.py"
        ]
        
        # Добавление параметров исключения для ненужных плагинов PIL
        for plugin in excluded_pillow_plugins:
            pyinstaller_command.extend(["--exclude-module", f"Pillow.{plugin}"])
        
        # Запуск PyInstaller
        subprocess.run(pyinstaller_command, check=True)
    except Exception as e:
        print(f"Ошибка при компиляции: {e}")
        return

    print("Перемещение и переименование EXE-файла в папке out...")
    try:
        # Путь к выходному файлу в папке dist
        dist_folder = "dist"
        exe_file = os.path.join(dist_folder, "main.exe")  # Предполагается, что имя файла - main.exe
        
        # Проверяем, существует ли папка dist и файл внутри нее
        if os.path.exists(exe_file):
            out_folder = "out"
            if not os.path.exists(out_folder):
                os.makedirs(out_folder)  # Создаем папку out, если она не существует
            
            # Перемещаем файл в папку out с заменой
            temp_path = os.path.join(out_folder, "main.exe")
            shutil.move(exe_file, temp_path)
            
            # Переименовываем файл в Mr_Clean.exe
            final_path = os.path.join(out_folder, "Mr_Clean.exe")
            os.rename(temp_path, final_path)
            print(f"Файл успешно перемещён и переименован в {final_path}")
        else:
            print("EXE-файл не найден в папке dist.")
    except Exception as e:
        print(f"Ошибка при перемещении или переименовании файла: {e}")

    print("Очистка временных файлов...")
    # Удаление временных файлов
    folders_to_remove = ["build", "dist", "__pycache__"]
    for folder in folders_to_remove:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    files_to_remove = ["main.spec"]
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)

    print("Компиляция завершена! Mr_Clean.exe находится в папке out.")

if __name__ == "__main__":
    compile_to_exe()