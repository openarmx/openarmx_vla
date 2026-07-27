# Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
#
# Copyright (c) 2026 Chengdu Changshu Robot Co., Ltd.
# https://www.openarmx.com

from __future__ import annotations

import time
from typing import Any

from lerobot.teleoperators.teleoperator import Teleoperator
from lerobot.teleoperators.utils import TeleopEvents
from lerobot.utils.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError

from .config_openarmx_o6_ros2 import OpenArmXO6Ros2TeleopConfig
from .ros2_interface_openarmx_o6 import OpenArmXO6Ros2TeleopInterface


class OpenArmXO6Ros2Teleop(Teleoperator):
    """LeRobot teleoperator for bimanual VR motion and two HIGVR/O6 hands."""

    config_class = OpenArmXO6Ros2TeleopConfig
    name = "openarmx_o6_ros2"

    def __init__(self, config: OpenArmXO6Ros2TeleopConfig):
        super().__init__(config)
        self.config = config
        self.ros2 = OpenArmXO6Ros2TeleopInterface(config.ros2)
        ros2 = self.config.ros2
        self._all_joint_names = (
            ros2.left_arm_joint_names
            + ros2.left_hand_joint_names
            + ros2.right_arm_joint_names
            + ros2.right_hand_joint_names
        )
        self._validate_config()

    def _validate_config(self) -> None:
        ros2 = self.config.ros2
        lengths = (
            len(ros2.left_arm_joint_names),
            len(ros2.left_hand_joint_names),
            len(ros2.right_arm_joint_names),
            len(ros2.right_hand_joint_names),
        )
        if lengths != (7, 6, 7, 6):
            raise ValueError(f"O6 teleoperator requires 7+6 joints per side, got {lengths}")
        if len(ros2.hand_message_joint_names) != 6:
            raise ValueError("hand_message_joint_names must contain exactly 6 names")
        if len(set(self._all_joint_names)) != 26:
            raise ValueError("O6 LeRobot action feature names must be unique")

    @property
    def action_features(self) -> dict[str, type]:
        return {f"{name}.pos": float for name in self._all_joint_names}

    @property
    def feedback_features(self) -> dict[str, type]:
        return {}

    @property
    def is_connected(self) -> bool:
        return self.ros2.is_connected

    def connect(self, calibrate: bool = True) -> None:
        if self.is_connected:
            raise DeviceAlreadyConnectedError(f"{self} already connected")
        self.ros2.connect()
        self.configure()
        deadline = time.time() + 3.0
        while self.ros2.get_latest_positions() is None and time.time() < deadline:
            time.sleep(0.05)

    def calibrate(self) -> None:
        return

    @property
    def is_calibrated(self) -> bool:
        return True

    def configure(self) -> None:
        return

    def get_action(self) -> dict[str, Any]:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected")
        latest = self.ros2.get_latest_positions()
        if latest is None:
            raise ValueError(
                "O6 action is incomplete. Check the 7-value arm command topics "
                "and both O6 command/state topics."
            )

        ros2 = self.config.ros2
        groups = (
            (ros2.left_arm_joint_names, latest["left_arm"]),
            (ros2.left_hand_joint_names, latest["left_hand"]),
            (ros2.right_arm_joint_names, latest["right_arm"]),
            (ros2.right_hand_joint_names, latest["right_hand"]),
        )
        action: dict[str, float] = {}
        for names, values in groups:
            if len(names) != len(values):
                raise ValueError(f"O6 action length mismatch: {len(values)}/{len(names)}")
            action.update({f"{name}.pos": float(value) for name, value in zip(names, values)})
        return action

    def send_feedback(self, feedback: dict[str, Any]) -> None:
        return

    def disconnect(self) -> None:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected")
        self.ros2.disconnect()

    def get_teleop_events(self) -> dict[str, Any]:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected")
        is_intervention = (
            self.ros2.get_grip_value("left") > 0.5
            or self.ros2.get_grip_value("right") > 0.5
        )
        return {
            TeleopEvents.IS_INTERVENTION: is_intervention,
            TeleopEvents.TERMINATE_EPISODE: False,
            TeleopEvents.SUCCESS: False,
            TeleopEvents.RERECORD_EPISODE: False,
        }
