# Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
#
# Copyright (c) 2026 Chengdu Changshu Robot Co., Ltd.
# https://www.openarmx.com
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
# 4.0 International License (CC BY-NC-SA 4.0).
#
# To view a copy of this license, visit:
# http://creativecommons.org/licenses/by-nc-sa/4.0/
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="lerobot_robot_openarmx_follower_ros2",
    version="0.0.1",
    author="OpenARM-X Team",
    description="A package for controlling OpenARM-X robot with VR controller in ROS2 environment.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=[
        'lerobot',
        'torch',
        'transformers',
        'datasets',
        'accelerate',
        'deepspeed',
        'opencv-python',
        'pygame',
        'rclpy',
        'numpy>=1.21,<2.0'
    ],
    entry_points={
        'lerobot.robots': [
            'openarmx_follower_ros2 = '
            'lerobot_robot_openarmx_follower_ros2.config_openarmx_ros2:OpenArmXRos2Config',
            'openarmx_follower_o6_ros2 = '
            'lerobot_robot_openarmx_follower_ros2.config_openarmx_o6_ros2:'
            'OpenArmXO6Ros2Config',
        ],
    },
)
