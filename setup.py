from setuptools import setup
import os

with open(os.path.abspath('./README.md'), 'rb') as f:
    readme = f.read().decode('utf-8')

setup(
    name='flowlight',
    version='0.1.5',
    packages=[
        'flowlight',
        'flowlight.core',
        'flowlight.model',
        'flowlight.tasks',
        'flowlight.utils'
    ],
    description='a tool make remote operations easier',
    long_description=readme,
    license='MIT',
    author='Wentao Liang',
    author_email='tonnie17@gmail.com',
    url='http://github.com/tonnie17/flowlight/',
    install_requires=['paramiko', 'cloudpickle'],
    entry_points='''
    [console_scripts]
    flowlight=flowlight:enter
    '''
)
