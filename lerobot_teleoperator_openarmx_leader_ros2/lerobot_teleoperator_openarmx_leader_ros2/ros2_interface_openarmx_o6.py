# Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
#
# Copyright (c) 2026 Chengdu Changshu Robot Co., Ltd.
# https://www.openarmx.com

from __future__ import annotations

import logging
import threading
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float32, Float64MultiArray

from .config_openarmx_o6_ros2 import OpenArmXO6Ros2TeleopInterfaceConfig

logger = logging.getLogger(__name__)


class OpenArmXO6Ros2TeleopInterface:
    """Collect the latest arm and O6 command vectors, with state fallbacks."""

    def __init__(self, config: OpenArmXO6Ros2TeleopInterfaceConfig):
        self.config = config
        self._node: Node | None = None
        self._executor: SingleThreadedExecutor | None = None
        self._spin_thread: threading.Thread | None = None
        self._entities: list = []

        self._lock = threading.Lock()
        self._arm_commands: dict[str, list[float] | None] = {"left": None, "right": None}
        self._hand_commands: dict[str, list[float] | None] = {"left": None, "right": None}
        self._arm_states: dict[str, float] = {}
        self._hand_states: dict[str, list[float] | None] = {"left": None, "right": None}
        self._grip_values = {"left": 0.0, "right": 0.0}
        self._warned_lengths: set[str] = set()
        self.is_connected = False

    def connect(self) -> None:
        if self.is_connected:
            return
        if not rclpy.ok():
            rclpy.init()

        self._node = Node("openarmx_lerobot_o6_teleop_interface", namespace=self.config.namespace)
        self._entities = [
            self._node.create_subscription(
                Float64MultiArray,
                self.config.left_arm_command_topic,
                lambda msg: self._arm_command_cb("left", msg),
                5,
            ),
            self._node.create_subscription(
                Float64MultiArray,
                self.config.right_arm_command_topic,
                lambda msg: self._arm_command_cb("right", msg),
                5,
            ),
            self._node.create_subscription(
                JointState,
                self.config.left_hand_command_topic,
                lambda msg: self._hand_command_cb("left", msg),
                5,
            ),
            self._node.create_subscription(
                JointState,
                self.config.right_hand_command_topic,
                lambda msg: self._hand_command_cb("right", msg),
                5,
            ),
            self._node.create_subscription(
                JointState, self.config.joint_states_topic, self._arm_state_cb, 10
            ),
            self._node.create_subscription(
                JointState,
                self.config.left_hand_state_topic,
                lambda msg: self._hand_state_cb("left", msg),
                10,
            ),
            self._node.create_subscription(
                JointState,
                self.config.right_hand_state_topic,
                lambda msg: self._hand_state_cb("right", msg),
                10,
            ),
            self._node.create_subscription(
                Float32,
                self.config.left_grip_topic,
                lambda msg: self._grip_cb("left", msg),
                5,
            ),
            self._node.create_subscription(
                Float32,
                self.config.right_grip_topic,
                lambda msg: self._grip_cb("right", msg),
                5,
            ),
        ]

        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)
        self._spin_thread = threading.Thread(target=self._executor.spin, daemon=True)
        self._spin_thread.start()
        time.sleep(0.2)
        self.is_connected = True

    def disconnect(self) -> None:
        if not self.is_connected:
            return
        for entity in self._entities:
            entity.destroy()
        self._entities.clear()
        if self._executor is not None:
            self._executor.shutdown()
            self._executor = None
        if self._spin_thread is not None:
            self._spin_thread.join(timeout=2.0)
            self._spin_thread = None
        if self._node is not None:
            self._node.destroy_node()
            self._node = None
        self.is_connected = False

    def _arm_names(self, side: str) -> list[str]:
        return self.config.left_arm_joint_names if side == "left" else self.config.right_arm_joint_names

    def _arm_command_cb(self, side: str, msg: Float64MultiArray) -> None:
        values = [float(value) for value in msg.data]
        expected = len(self._arm_names(side))
        if len(values) != expected:
            self._warn_once(f"{side}_arm", len(values), expected)
            return
        with self._lock:
            self._arm_commands[side] = values

    def _ordered_hand_values(self, msg: JointState) -> list[float] | None:
        expected_names = self.config.hand_message_joint_names
        if msg.name:
            by_name = {name: float(value) for name, value in zip(msg.name, msg.position)}
            if all(name in by_name for name in expected_names):
                return [by_name[name] for name in expected_names]
            return None
        if len(msg.position) == len(expected_names):
            return [float(value) for value in msg.position]
        return None

    def _hand_command_cb(self, side: str, msg: JointState) -> None:
        values = self._ordered_hand_values(msg)
        if values is None:
            self._warn_once(f"{side}_hand_command", len(msg.position), 6)
            return
        with self._lock:
            self._hand_commands[side] = values

    def _arm_state_cb(self, msg: JointState) -> None:
        with self._lock:
            for name, position in zip(msg.name, msg.position):
                self._arm_states[name] = float(position)

    def _hand_state_cb(self, side: str, msg: JointState) -> None:
        values = self._ordered_hand_values(msg)
        if values is None:
            self._warn_once(f"{side}_hand_state", len(msg.position), 6)
            return
        with self._lock:
            self._hand_states[side] = values

    def _grip_cb(self, side: str, msg: Float32) -> None:
        with self._lock:
            self._grip_values[side] = float(msg.data)

    def _warn_once(self, key: str, actual: int, expected: int) -> None:
        if key in self._warned_lengths:
            return
        self._warned_lengths.add(key)
        logger.warning("%s length %s does not match expected %s; ignoring message", key, actual, expected)

    def get_grip_value(self, side: str) -> float:
        if side not in self._grip_values:
            raise ValueError(f"Unknown side: {side}")
        with self._lock:
            return self._grip_values[side]

    def _arm_state_fallback(self, side: str) -> list[float] | None:
        names = self._arm_names(side)
        with self._lock:
            if any(name not in self._arm_states for name in names):
                return None
            return [self._arm_states[name] for name in names]

    def get_latest_positions(self) -> dict[str, list[float]] | None:
        """Return four ordered vectors, preferring commands over measured states."""
        with self._lock:
            left_arm = None if self._arm_commands["left"] is None else list(self._arm_commands["left"])
            right_arm = None if self._arm_commands["right"] is None else list(self._arm_commands["right"])
            left_hand = None if self._hand_commands["left"] is None else list(self._hand_commands["left"])
            right_hand = None if self._hand_commands["right"] is None else list(self._hand_commands["right"])
            left_hand_state = None if self._hand_states["left"] is None else list(self._hand_states["left"])
            right_hand_state = (
                None
                if self._hand_states["right"] is None
                else list(self._hand_states["right"])
            )

        left_arm = left_arm if left_arm is not None else self._arm_state_fallback("left")
        right_arm = right_arm if right_arm is not None else self._arm_state_fallback("right")
        left_hand = left_hand if left_hand is not None else left_hand_state
        right_hand = right_hand if right_hand is not None else right_hand_state

        if any(value is None for value in (left_arm, right_arm, left_hand, right_hand)):
            return None
        return {
            "left_arm": left_arm,
            "left_hand": left_hand,
            "right_arm": right_arm,
            "right_hand": right_hand,
        }
