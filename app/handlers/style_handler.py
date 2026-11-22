import json

import os
STYLES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "styles.json")

def load_styles():
    # Загрузка стилей из файла styles.json
    try:
        with open(STYLES_PATH, "r") as file:
            styles = json.load(file)
            return styles
    except FileNotFoundError:
        print("Styles file not found, using default styles.")
        return {}

def save_styles(styles):
    # Сохранение стилей в styles.json
    with open(STYLES_PATH, "w") as file:
        json.dump(styles, file, indent=4)
    print("Styles saved:", styles)

def apply_styles(window, styles):
    # Применение стилей к элементам интерфейса
    window.setStyleSheet(f"""
        QPushButton {{
            background-color: {styles.get('button_background_color', 'gray')};
            border-radius: {styles.get('button_corner_radius', '5')}px;
            color: {styles.get('button_text_color', 'black')};
        }}
        QPushButton:pressed {{
            background-color: {styles.get('button_pressed_color', 'darkgray')};
        }}
        #launchButton {{
            background-color: {styles.get('launch_button_background_color', 'darkviolet')};
            border: 2px solid {styles.get('launch_button_border_color', 'pink')};
            color: {styles.get('launch_button_text_color', 'white')};
        }}
        QLabel {{
            color: {styles.get('label_text_color', 'black')};
        }}
        QComboBox {{
            background-color: {styles.get('combobox_background_color', 'white')};
        }}
        #profileComboBox {{
            background-color: {styles.get('profile_combobox_background_color', 'white')};
        }}
        #versionComboBox {{
            background-color: {styles.get('version_combobox_background_color', 'white')};
        }}
    """)
