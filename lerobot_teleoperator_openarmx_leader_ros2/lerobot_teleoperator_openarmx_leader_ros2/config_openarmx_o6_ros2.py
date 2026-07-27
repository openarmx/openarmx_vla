# Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
#
# Copyright (c) 2026 Chengdu Changshu Robot Co., Ltd.
# https://www.openarmx.com

from __future__ import annotations

from dataclasses import dataclass, field

from lerobot.teleoperators.config import TeleoperatorConfig


O6_MESSAGE_JOINT_NAMES = [
    "thumb_cmc_pitch",
    "thumb_cmc_yaw",
    "index_mcp_pitch",
    "middle_mcp_pitch",
    "ring_mcp_pitch",
    "pinky_mcp_pitch",
]


def o6_feature_joint_names(side: str) -> list[str]:
    return [f"openarmx_{side}_o6_{name}" for name in O6_MESSAGE_JOINT_NAMES]


@dataclass
class OpenArmXO6Ros2TeleopInterfaceConfig:
    """ROS 2 inputs used to assemble a 26-dimensional O6 teleoperation action."""

    namespace: str = ""
    joint_states_topic: str = "/joint_states"
    left_grip_topic: str = "/pico_left_controller/grip"
    right_grip_topic: str = "/pico_right_controller/grip"

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


@TeleoperatorConfig.register_subclass("openarmx_leader_o6_ros2")
@dataclass
class OpenArmXO6Ros2TeleopConfig(TeleoperatorConfig):
    """LeRobot teleoperator for Pico arm poses plus HIGVR-controlled O6 hands."""

    ros2: OpenArmXO6Ros2TeleopInterfaceConfig = field(
        default_factory=OpenArmXO6Ros2TeleopInterfaceConfig
    )
