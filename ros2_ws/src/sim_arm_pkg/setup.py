import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'sim_arm_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # damit launch ordner gefunden wird
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        # damit config ordner gefunden wird
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ros',
    maintainer_email='ros@todo.todo',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'tcp_pose = sim_arm_pkg.tcp_pose:main',
            'status_client = sim_arm_pkg.status_client:main',
            'command_client = sim_arm_pkg.command_client:main',
            'action_client = sim_arm_pkg.action_client:main',
            'action_client_moveitpy = sim_arm_pkg.action_client_moveitpy:main'
        ],
    },
)
