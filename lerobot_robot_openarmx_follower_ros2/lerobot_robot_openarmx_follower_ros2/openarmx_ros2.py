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

from __future__ import annotations

import logging
import time
from functools import cached_property
from typing import Any

from lerobot.cameras.camera import Camera
from lerobot.robots import Robot
from lerobot.robots.utils import ensure_safe_goal_position
from lerobot.utils.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError

from .config_openarmx_ros2 import OpenArmXRos2Config
from .ros2_camera import Ros2Camera, Ros2CameraConfig
from .ros2_interface_openarmx import OpenArmXRos2Interface

logger = logging.getLogger(__name__)


def make_cameras(camera_configs: dict[str, Any]) -> dict[str, Camera]:
    """创建相机实例，支持 Ros2Camera 和 LeRobot 内置相机类型。"""
    cameras: dict[str, Camera] = {}

    for key, cfg in camera_configs.items():
        if isinstance(cfg, Ros2CameraConfig):
            # 使用我们的 ROS2 相机
            cameras[key] = Ros2Camera(cfg)
        else:
            # 回退到 LeRobot 内置的相机工厂
            from lerobot.cameras.utils import make_cameras_from_configs
            cameras[key] = make_cameras_from_configs({key: cfg})[key]

    return cameras


class OpenArmXRos2(Robot):
    """OpenArmX bimanual robot controlled via ROS 2 topics.

    Observations:
      - per-joint positions from /joint_states
      - optional camera frames (if configured)

    Actions:
      - per-joint target positions published as Float64MultiArray to:
        /left_forward_position_controller/commands
        /right_forward_position_controller/commands

    The command vector ordering is defined by config.ros2.left_joint_names / right_joint_names.
    """

    config_class = OpenArmXRos2Config
    # Keep type name aligned with lerobot CLI choice list
    name = "openarmx_ros2"

    def __init__(self, config: OpenArmXRos2Config):
        super().__init__(config)
        self.config = config
        self.ros2 = OpenArmXRos2Interface(config.ros2)
        self.cameras = make_cameras(config.cameras)

        self._all_joint_names = self.config.ros2.left_joint_names + self.config.ros2.right_joint_names

    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        motor_state_ft = {f"{j}.pos": float for j in self._all_joint_names}
        cams_ft = {
            cam: (self.config.cameras[cam].height, self.config.cameras[cam].width, 3) for cam in self.cameras
        }
        return {**motor_state_ft, **cams_ft}

    @cached_property
    def action_features(self) -> dict[str, type]:
        return {f"{j}.pos": float for j in self._all_joint_names}

    @property
    def is_connected(self) -> bool:
        return self.ros2.is_connected and all(cam.is_connected for cam in self.cameras.values())

    def connect(self, calibrate: bool = True) -> None:
        if self.is_connected:
            raise DeviceAlreadyConnectedError(f"{self} already connected")

        for cam in self.cameras.values():
            cam.connect()
        self.ros2.connect()

        # OpenArmX is calibrated/configured by ROS bringup.
        self.configure()

        # Wait for joint state once to avoid get_observation failing immediately.
        t0 = time.time()
        while self.ros2.get_joint_positions(self._all_joint_names) is None:
            if time.time() - t0 > 5.0:
                break
            time.sleep(0.05)

    @property
    def is_calibrated(self) -> bool:
        return True

    def calibrate(self) -> None:
        return  # handled externally

    def configure(self) -> None:
        return  # handled externally

    def get_observation(self) -> dict[str, Any]:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        obs: dict[str, Any] = {}
        positions = self.ros2.get_joint_positions(self._all_joint_names)
        if positions is None:
            raise ValueError("Joint state is not available yet.")

        # Fill all joints (if some are missing, fail loudly to avoid silent dataset corruption)
        missing = [j for j in self._all_joint_names if j not in positions]
        if missing:
            raise ValueError(f"Missing joints in joint_states: {missing}")

        obs.update({f"{j}.pos": positions[j] for j in self._all_joint_names})

        for cam_key, cam in self.cameras.items():
            try:
                obs[cam_key] = cam.async_read(timeout_ms=300)
            except Exception as e:
                logger.error(f"Failed to read camera {cam_key}: {e}")
                raise RuntimeError(f"Failed to read camera {cam_key}") from e

        return obs

    def send_action(self, action: dict[str, float]) -> dict[str, float]:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        # Build per-joint goals
        goal = {k.removesuffix(".pos"): float(v) for k, v in action.items() if k.endswith(".pos")}

        # Skip sending if configured (direct teleop mode - teleop_node controls robot)
        if self.config.skip_send_action:
            return {f"{j}.pos": goal[j] for j in self._all_joint_names}

        # Optional relative clipping (same helper as other robots)
        if self.config.max_relative_target is not None:
            present = self.ros2.get_joint_positions(self._all_joint_names)
            if present is None:
                raise ValueError("Joint state is not available yet.")
            goal_present = {f"{j}.pos": (goal[j], present[j]) for j in self._all_joint_names}
            clipped = ensure_safe_goal_position(goal_present, self.config.max_relative_target)
            goal = {k.removesuffix(".pos"): v for k, v in clipped.items()}

        left_vec = [goal[j] for j in self.config.ros2.left_joint_names]
        right_vec = [goal[j] for j in self.config.ros2.right_joint_names]

        self.ros2.send_left_positions(left_vec)
        self.ros2.send_right_positions(right_vec)

        return {f"{j}.pos": goal[j] for j in self._all_joint_names}

    def disconnect(self) -> None:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        for cam in self.cameras.values():
            cam.disconnect()
        self.ros2.disconnect()
