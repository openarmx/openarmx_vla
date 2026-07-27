# Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
#
# Copyright (c) 2026 Chengdu Changshu Robot Co., Ltd.
# https://www.openarmx.com

from pathlib import Path

from setuptools import find_packages, setup


setup(
    name="lerobot_teleoperator_openarmx_leader_ros2",
    version="0.0.1",
    description=(
        "LeRobot teleoperator plugin for OpenArmX VR control with gripper or O6 hands."
    ),
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=["lerobot", "rclpy"],
    entry_points={
        "lerobot.teleoperators": [
            "openarmx_leader_ros2 = "
            "lerobot_teleoperator_openarmx_leader_ros2.config_openarmx_ros2:"
            "OpenArmXRos2TeleopConfig",
            "openarmx_leader_o6_ros2 = "
            "lerobot_teleoperator_openarmx_leader_ros2.config_openarmx_o6_ros2:"
            "OpenArmXO6Ros2TeleopConfig",
        ],
    },
)
