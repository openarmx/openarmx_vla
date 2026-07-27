# Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
#
# Copyright (c) 2026 Chengdu Changshu Robot Co., Ltd.
# https://www.openarmx.com
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
# 4.0 International License (CC BY-NC-SA 4.0).

from __future__ import annotations

from dataclasses import dataclass, field

from lerobot.cameras import CameraConfig
from lerobot.cameras.configs import ColorMode, Cv2Rotation
from lerobot.robots import RobotConfig

from .ros2_camera import Ros2CameraConfig


O6_MESSAGE_JOINT_NAMES = [
    "thumb_cmc_pitch",
    "thumb_cmc_yaw",
    "index_mcp_pitch",
    "middle_mcp_pitch",
    "ring_mcp_pitch",
    "pinky_mcp_pitch",
]


def o6_feature_joint_names(side: str) -> list[str]:
    """Return side-qualified LeRobot feature names for the six O6 ranges."""
    return [f"openarmx_{side}_o6_{name}" for name in O6_MESSAGE_JOINT_NAMES]


@dataclass
class OpenArmXO6Ros2InterfaceConfig:
    """ROS 2 topics and fixed joint ordering for the bimanual O6 robot."""

    namespace: str = ""
    joint_states_topic: str = "/joint_states"

    left_arm_command_topic: str = "/left_forward_position_controller/commands"
    right_arm_command_topic: str = "/right_forward_position_controller/commands"
    left_hand_command_topic: str = "/openarmx/o6/left/command"
    right_hand_command_topic: str = "/openarmx/o6/right/command"
    left_hand_state_topic: str = "/openarmx/o6/left/state"
    right_hand_state_topic: str = "/openarmx/o6/right/state"

    left_arm_joint_names: list[str] = field(
        default_factory=lambda: [f"openarmx_left_joint{i}" for i in range(1, 8)]
    )
    right_arm_joint_names: list[str] = field(
        default_factory=lambda: [f"openarmx_right_joint{i}" for i in range(1, 8)]
    )
    left_hand_joint_names: list[str] = field(default_factory=lambda: o6_feature_joint_names("left"))
    right_hand_joint_names: list[str] = field(default_factory=lambda: o6_feature_joint_names("right"))
    hand_message_joint_names: list[str] = field(default_factory=lambda: list(O6_MESSAGE_JOINT_NAMES))


def _default_cameras() -> dict[str, CameraConfig]:
    common = {
        "fps": 15,
        "width": 424,
        "height": 240,
        "color_mode": ColorMode.RGB,
        "use_depth": True,
        "rotation": Cv2Rotation.NO_ROTATION,
        "qos_reliability": "best_effort",
        "queue_size": 1,
    }
    return {
        "cam_right": Ros2CameraConfig(
            image_topic="/cam_right/cam_right/color/image_raw",
            depth_topic="/cam_right/cam_right/depth/camera_info",
            **common,
        ),
        "cam_left": Ros2CameraConfig(
            image_topic="/cam_left/cam_left/color/image_raw",
            depth_topic="/cam_left/cam_left/depth/camera_info",
            **common,
        ),
        "cam_head": Ros2CameraConfig(
            image_topic="/cam_head/color/image",
            depth_topic="/cam_head/depth/image",
            **common,
        ),
    }


@RobotConfig.register_subclass("openarmx_follower_o6_ros2")
@dataclass
class OpenArmXO6Ros2Config(RobotConfig):
    """LeRobot configuration for OpenArmX bimanual arms with two O6 hands."""

    # Arm values are radians; O6 hand values use the driver's native 0..255 range.
    max_relative_arm_target: float | dict[str, float] | None = None
    max_relative_hand_target: float | dict[str, float] | None = None
    hand_position_min: float = 0.0
    hand_position_max: float = 255.0

    # True for VR/HIGVR data collection. Set false only when a policy owns the outputs.
    skip_send_action: bool = True

    cameras: dict[str, CameraConfig] = field(default_factory=_default_cameras)
    ros2: OpenArmXO6Ros2InterfaceConfig = field(default_factory=OpenArmXO6Ros2InterfaceConfig)
