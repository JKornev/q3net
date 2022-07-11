from setuptools import setup, find_packages

setup(
    name= 'q3net',
    version= '1.0.1',
    description= 'Quake 3 connection emulator',
    url= 'https://github.com/JKornev/q3net',
    author= 'JKornev',
    license= 'Free',
    packages=['q3net'],
    package_dir={
        'q3net': '.',
    },
    install_requires=['q3huff2==0.4.2']
)