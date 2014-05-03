from setuptools import setup, find_packages

setup(
    name='import_sample',
    author='Andrew Svetlov',
    version='0.0.1',
    description='Sample for illustrating import hooks',
    packages=find_packages('src'),
    include_package_data = True,
    package_dir = {'': 'src'},
    tests_require = ['nose>=0.11'],
    )
