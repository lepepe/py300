from setuptools import setup, find_packages

setup(
    name='py300',
    version='0.0.1',
    description='Simple CLI app to interac with Sage300',
    author='Jose Perez (a.k.a Lepepe)',
    author_email='lepepe@hey.com',
    url='https://github.com/lepepe/py300',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'click',
        'pandas',
        'numpy',
        'pyodbc',
        'rich',
        'inventorize3'
    ],
    entry_points={
        'console_scripts': [
            'py300=main:cli'
        ]
    }
)
