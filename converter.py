import os
import sys
import time
import datetime
import gc
import shutil
import tkinter as tk
from tkinter import filedialog, simpledialog

# Импорт библиотек
try:
    import xmltodict
    import orjson
    from lxml import etree
    from tqdm import tqdm
except ImportError:
    print("Библиотеки не найдены. Запустите start.bat")
    sys.exit(1)

# --- НАСТРОЙКИ ---
GC_COLLECT_STEP = 50000 

def select_input_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    print("Выберите исходный XML файл...")
    input_path = filedialog.askopenfilename(
        title="Выберите XML файл (30GB+)",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )
    root.destroy()
    return input_path

def ask_save_path(mode):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    if mode == 1:
        # Режим 1: Выбираем куда сохранить ФАЙЛ
        path = filedialog.asksaveasfilename(
            title="Сохранить ЕДИНЫЙ JSON файл как...",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
    else:
        # Режим 2: Выбираем ПАПКУ для кучи файлов
        print("Выберите папку для сохранения датасета...")
        path = filedialog.askdirectory(
            title="Выберите пустую папку для сохранения файлов"
        )
    
    root.destroy()
    return path

def format_time(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))

def process_xml(input_xml, output_path, mode):
    total_bytes = os.path.getsize(input_xml)
    start_time = time.time()
    
    # Визуальные настройки
    custom_ascii = " █"
    tqdm_args = {
        'ascii': custom_ascii,
        'mininterval': 1.0, # Обновление раз в 1 сек
        'maxinterval': 1.0,
        'colour': 'white'
    }
    
    print("-" * 60)
    file_stream = open(input_xml, 'rb')
    
    # Если режим 2, создаем папку, если её нет
    if mode == 2:
        os.makedirs(output_path, exist_ok=True)
    
    # Если режим 1, открываем файл сразу
    f_single = None
    if mode == 1:
        f_single = open(output_path, 'wb')
        f_single.write(b'[\n')

    try:
        # Прогресс-бары
        with tqdm(total=total_bytes, unit='B', unit_scale=True, desc="Объем   ", 
                 bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]", **tqdm_args) as pbar_bytes, \
             tqdm(total=None, unit=' files', desc="Объектов", 
                 bar_format="{desc}: {n_fmt} | {rate_fmt}", position=1, **tqdm_args) as pbar_items:

            context = etree.iterparse(file_stream, events=('start', 'end'))
            _, root = next(context) 
            
            first_item = True
            last_pos = 0
            count = 0
            
            for event, elem in context:
                if event == 'end':
                    if elem == root: continue # Пропуск корня
                    
                    # Берем только прямых потомков корня
                    if elem.getparent() == root:
                        
                        # Прогресс
                        current_pos = file_stream.tell()
                        pbar_bytes.update(current_pos - last_pos)
                        last_pos = current_pos
                        
                        # Парсинг
                        xml_str = etree.tostring(elem, encoding='utf-8')
                        data_dict = xmltodict.parse(xml_str)
                        
                        # --- РАЗВЕТВЛЕНИЕ ЛОГИКИ ---
                        
                        if mode == 1:
                            # ЗАПИСЬ В ОДИН ФАЙЛ
                            if not first_item: f_single.write(b',\n')
                            else: first_item = False
                            f_single.write(orjson.dumps(data_dict))
                        
                        else:
                            # ЗАПИСЬ ПО ФАЙЛАМ (ДАТАСЕТ)
                            # Пытаемся найти красивое имя (например id или title)
                            # Иначе просто номер 00001.json
                            safe_name = f"{count}.json"
                            
                            # Попытка найти ID внутри данных для красивого имени
                            # (Работает для Wiki, StackOverflow и многих других)
                            try:
                                # Ищем первый ключ (напр 'page')
                                top_key = list(data_dict.keys())[0]
                                if 'id' in data_dict[top_key]:
                                    obj_id = data_dict[top_key]['id']
                                    safe_name = f"{obj_id}.json"
                            except:
                                pass # Если не нашли ID, будет просто номер
                            
                            file_full_path = os.path.join(output_path, safe_name)
                            
                            with open(file_full_path, 'wb') as f_small:
                                f_small.write(orjson.dumps(data_dict))

                        # ---------------------------

                        # Очистка
                        elem.clear()
                        while elem.getprevious() is not None:
                            del elem.getparent()[0]
                        
                        count += 1
                        pbar_items.update(1)
                        
                        if count % GC_COLLECT_STEP == 0:
                            gc.collect()

        # Закрываем главный файл если был режим 1
        if mode == 1 and f_single:
            f_single.write(b'\n]')
            f_single.close()

    except Exception as e:
        print(f"\n\n[ОШИБКА]: {e}")
    finally:
        file_stream.close()
        end_time = time.time()
        print("\n" + "="*60)
        print(f" ГОТОВО!")
        print(f" Режим: {'Единый файл' if mode == 1 else 'Папка с файлами'}")
        print(f" Обработано: {count} объектов")
        print(f" Время: {format_time(end_time - start_time)}")
        print("="*60)

def main():
    input_xml = select_input_file()
    if not input_xml: return

    print("\n" + "="*40)
    print(" ВЫБЕРИТЕ РЕЖИМ КОНВЕРТАЦИИ:")
    print("="*40)
    print(" [1] ПОЛНЫЙ (Монолит)")
    print("     - Создаст один огромный .json файл.")
    print("     - Удобно для хранения и переноса.")
    print("")
    print(" [2] ПО СТРАНИЦАМ (Датасет для ИИ)")
    print("     - Создаст папку и тысячи мелких файлов внутри.")
    print("     - Идеально для обучения нейросетей (DataLoader).")
    print("     - Имя файла будет браться из <id>, если он есть.")
    print("="*40)
    
    while True:
        choice = input(" Введите 1 или 2 и нажмите Enter: ").strip()
        if choice in ['1', '2']:
            mode = int(choice)
            break
        print(" Неверный ввод.")

    output_dest = ask_save_path(mode)
    if not output_dest: return

    process_xml(input_xml, output_dest, mode)

if __name__ == "__main__":
    main()
