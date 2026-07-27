# Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
#
# Copyright (c) 2026 Chengdu Changshu Robot Co., Ltd.
# https://www.openarmx.com

from __future__ import annotations

import logging
import time
from functools import cached_property
from typing import Any

from lerobot.cameras.camera import Camera
from lerobot.robots import Robot
from lerobot.utils.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError

from .config_openarmx_o6_ros2 import OpenArmXO6Ros2Config
from .openarmx_ros2 import make_cameras
from .ros2_interface_openarmx_o6 import OpenArmXO6Ros2Interface

logger = logging.getLogger(__name__)


class OpenArmXO6Ros2(Robot):
    """OpenArmX bimanual robot with two independently controlled O6 hands."""

    config_class = OpenArmXO6Ros2Config
    name = "openarmx_o6_ros2"

    def __init__(self, config: OpenArmXO6Ros2Config):
        super().__init__(config)
        self.config = config
        self.ros2 = OpenArmXO6Ros2Interface(config.ros2)
        self.cameras: dict[str, Camera] = make_cameras(config.cameras)

        ros2 = self.config.ros2
        self._arm_joint_names = ros2.left_arm_joint_names + ros2.right_arm_joint_names
        self._hand_joint_names = ros2.left_hand_joint_names + ros2.right_hand_joint_names
        self._all_joint_names = (
            ros2.left_arm_joint_names
            + ros2.left_hand_joint_names
            + ros2.right_arm_joint_names
            + ros2.right_hand_joint_names
        )
        self._validate_config()

    def _validate_config(self) -> None:
        ros2 = self.config.ros2
        if len(ros2.left_arm_joint_names) != 7 or len(ros2.right_arm_joint_names) != 7:
            raise ValueError("O6 mode requires exactly 7 arm joints per side")
        if len(ros2.left_hand_joint_names) != 6 or len(ros2.right_hand_joint_names) != 6:
            raise ValueError("O6 mode requires exactly 6 hand ranges per side")
        if len(ros2.hand_message_joint_names) != 6:
            raise ValueError("hand_message_joint_names must contain exactly 6 names")
        if len(set(self._all_joint_names)) != 26:
            raise ValueError("O6 LeRobot feature names must be unique")
        if self.config.hand_position_min >= self.config.hand_position_max:
            raise ValueError("hand_position_min must be less than hand_position_max")

    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        motor_state_ft = {f"{name}.pos": float for name in self._all_joint_names}
        camera_ft = {
            name: (self.config.cameras[name].height, self.config.cameras[name].width, 3)
            for name in self.cameras
        }
        return {**motor_state_ft, **camera_ft}

    @cached_property
    def action_features(self) -> dict[str, type]:
        return {f"{name}.pos": float for name in self._all_joint_names}

    @property
    def is_connected(self) -> bool:
        return self.ros2.is_connected and all(camera.is_connected for camera in self.cameras.values())

    def connect(self, calibrate: bool = True) -> None:
        if self.is_connected:
            raise DeviceAlreadyConnectedError(f"{self} already connected")
        for camera in self.cameras.values():
            camera.connect()
        self.ros2.connect()
        self.configure()

        deadline = time.time() + 5.0
        while self._get_robot_positions() is None and time.time() < deadline:
            time.sleep(0.05)

    @property
    def is_calibrated(self) -> bool:
        return True

    def calibrate(self) -> None:
        return

    def configure(self) -> None:
        return

    def _get_robot_positions(self) -> dict[str, float] | None:
        ros2 = self.config.ros2
        arms = self.ros2.get_arm_positions(self._arm_joint_names)
        left_hand = self.ros2.get_hand_positions("left")
        right_hand = self.ros2.get_hand_positions("right")
        if arms is None or left_hand is None or right_hand is None:
            return None
        positions = {**arms, **left_hand, **right_hand}
        if any(name not in positions for name in self._all_joint_names):
            return None
        # Preserve the declared feature ordering.
        return {name: positions[name] for name in self._all_joint_names}

    def get_observation(self) -> dict[str, Any]:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected")
        positions = self._get_robot_positions()
        if positions is None:
            raise ValueError("Arm or O6 hand state is incomplete")

        observation: dict[str, Any] = {
            f"{name}.pos": positions[name] for name in self._all_joint_names
        }
        for camera_name, camera in self.cameras.items():
            try:
                observation[camera_name] = camera.async_read(timeout_ms=300)
            except Exception as exc:
                logger.error("Failed to read camera %s: %s", camera_name, exc)
                observation[camera_name] = None
        return observation

    @staticmethod
    def _relative_caps(
        names: list[str], setting: float | dict[str, float]
    ) -> dict[str, float]:
        if isinstance(setting, (int, float)):
            return {name: float(setting) for name in names}
        normalized: dict[str, float] = {}
        for name in names:
            if name in setting:
                normalized[name] = float(setting[name])
            elif f"{name}.pos" in setting:
                normalized[name] = float(setting[f"{name}.pos"])
            else:
                raise ValueError(f"Missing relative target limit for {name}")
        return normalized

    def _apply_relative_limit(
        self,
        goal: dict[str, float],
        present: dict[str, float],
        names: list[str],
        setting: float | dict[str, float] | None,
    ) -> None:
        if setting is None:
            return
        caps = self._relative_caps(names, setting)
        for name in names:
            delta = goal[name] - present[name]
            cap = abs(caps[name])
            goal[name] = present[name] + max(-cap, min(cap, delta))

    def send_action(self, action: dict[str, float]) -> dict[str, float]:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected")

        goal = {
            key.removesuffix(".pos"): float(value)
            for key, value in action.items()
            if key.endswith(".pos")
        }
        missing = [name for name in self._all_joint_names if name not in goal]
        if missing:
            raise ValueError(f"Missing O6 action features: {missing}")
        goal = {name: goal[name] for name in self._all_joint_names}

        if self.config.skip_send_action:
            return {f"{name}.pos": goal[name] for name in self._all_joint_names}

        present = self._get_robot_positions()
        if present is None and (
            self.config.max_relative_arm_target is not None
            or self.config.max_relative_hand_target is not None
        ):
            raise ValueError("Cannot apply relative action limits because robot state is incomplete")
        if present is not None:
            self._apply_relative_limit(
                goal,
                present,
                self._arm_joint_names,
                self.config.max_relative_arm_target,
            )
            self._apply_relative_limit(
                goal,
                present,
                self._hand_joint_names,
                self.config.max_relative_hand_target,
            )

        for name in self._hand_joint_names:
            goal[name] = max(
                self.config.hand_position_min,
                min(self.config.hand_position_max, goal[name]),
            )

        ros2 = self.config.ros2
        self.ros2.send_arm_positions("left", [goal[name] for name in ros2.left_arm_joint_names])
        self.ros2.send_arm_positions("right", [goal[name] for name in ros2.right_arm_joint_names])
        self.ros2.send_hand_positions("left", [goal[name] for name in ros2.left_hand_joint_names])
        self.ros2.send_hand_positions("right", [goal[name] for name in ros2.right_hand_joint_names])

        return {f"{name}.pos": goal[name] for name in self._all_joint_names}

    def disconnect(self) -> None:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected")
        for camera in self.cameras.values():
            camera.disconnect()
        self.ros2.disconnect()
