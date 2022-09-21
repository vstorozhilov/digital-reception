from cx_Freeze import setup, Executable

executables = (
    [
        Executable(
            "main.py",
            copyright="Copyright (C) 2022 ФГАУ ВИТ ЭРА. 14 Лаборатория искусственного ителлекта",
            icon="./logo.ico",
            shortcutName="Электронная приемная",
            shortcutDir="Приемная",
            base="Win32GUI",
            targetName="Электронная приемная.exe"
        )
    ]
)

buildOptions = {
    "build_exe": "Электронная приемная",
    "include_files": [r'.\logo.ico',
                      r".\credentials.json",
                      r'.\mute.ico',
                      r'.\mute_1.ico',
                      r'.\sound1.wav']
}


setup(
    name="Электронная приемная",
    version="1.1",
    description="Приложения для ведения событий, встреч и посетителей.",
    options={
        "build_exe": buildOptions,
    },
    executables=executables
)
