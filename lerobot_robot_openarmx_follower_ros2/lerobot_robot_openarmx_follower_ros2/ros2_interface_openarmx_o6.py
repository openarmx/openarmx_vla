# Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
#
# Copyright (c) 2026 Chengdu Changshu Robot Co., Ltd.
# https://www.openarmx.com

from __future__ import annotations

import threading
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

from lerobot.utils.errors import DeviceNotConnectedError

from .config_openarmx_o6_ros2 import OpenArmXO6Ros2InterfaceConfig


class OpenArmXO6Ros2Interface:
    """ROS 2 transport for 7+7 arm joints and two six-range O6 hands."""

    def __init__(self, config: OpenArmXO6Ros2InterfaceConfig):
        self.config = config
        self._node: Node | None = None
        self._executor: SingleThreadedExecutor | None = None
        self._spin_thread: threading.Thread | None = None

        self._left_arm_pub = None
        self._right_arm_pub = None
        self._left_hand_pub = None
        self._right_hand_pub = None
        self._joint_state_sub = None
        self._left_hand_state_sub = None
        self._right_hand_state_sub = None
        self._left_hand_command_sub = None
        self._right_hand_command_sub = None

        self._lock = threading.Lock()
        self._arm_positions: dict[str, float] = {}
        self._hand_positions: dict[str, dict[str, float]] = {"left": {}, "right": {}}
        self._hand_command_positions: dict[str, dict[str, float]] = {
            "left": {},
            "right": {},
        }
        self.is_connected = False

    def connect(self) -> None:
        if self.is_connected:
            return
        if not rclpy.ok():
            rclpy.init()

        self._node = Node("openarmx_lerobot_o6_interface", namespace=self.config.namespace)
        self._left_arm_pub = self._node.create_publisher(
            Float64MultiArray, self.config.left_arm_command_topic, 10
        )
        self._right_arm_pub = self._node.create_publisher(
            Float64MultiArray, self.config.right_arm_command_topic, 10
        )
        self._left_hand_pub = self._node.create_publisher(
            JointState, self.config.left_hand_command_topic, 10
        )
        self._right_hand_pub = self._node.create_publisher(
            JointState, self.config.right_hand_command_topic, 10
        )

        self._joint_state_sub = self._node.create_subscription(
            JointState, self.config.joint_states_topic, self._arm_state_cb, 50
        )
        self._left_hand_state_sub = self._node.create_subscription(
            JointState,
            self.config.left_hand_state_topic,
            lambda msg: self._hand_state_cb("left", msg),
            20,
        )
        self._right_hand_state_sub = self._node.create_subscription(
            JointState,
            self.config.right_hand_state_topic,
            lambda msg: self._hand_state_cb("right", msg),
            20,
        )
        self._left_hand_command_sub = self._node.create_subscription(
            JointState,
            self.config.left_hand_command_topic,
            lambda msg: self._hand_command_cb("left", msg),
            20,
        )
        self._right_hand_command_sub = self._node.create_subscription(
            JointState,
            self.config.right_hand_command_topic,
            lambda msg: self._hand_command_cb("right", msg),
            20,
        )

        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)
        self._spin_thread = threading.Thread(target=self._executor.spin, daemon=True)
        self._spin_thread.start()
        time.sleep(0.2)
        self.is_connected = True

    def disconnect(self) -> None:
        if not self.is_connected:
            return

        for entity_name in (
            "_joint_state_sub",
            "_left_hand_state_sub",
            "_right_hand_state_sub",
            "_left_hand_command_sub",
            "_right_hand_command_sub",
            "_left_arm_pub",
            "_right_arm_pub",
            "_left_hand_pub",
            "_right_hand_pub",
        ):
            entity = getattr(self, entity_name)
            if entity is not None:
                entity.destroy()
                setattr(self, entity_name, None)

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

    def _arm_state_cb(self, msg: JointState) -> None:
        with self._lock:
            for name, position in zip(msg.name, msg.position):
                self._arm_positions[name] = float(position)

    def _ordered_hand_positions(self, side: str, msg: JointState) -> dict[str, float] | None:
        expected_message_names = self.config.hand_message_joint_names
        feature_names = (
            self.config.left_hand_joint_names if side == "left" else self.config.right_hand_joint_names
        )
        if len(feature_names) != len(expected_message_names):
            return None

        if msg.name:
            by_name = {name: float(value) for name, value in zip(msg.name, msg.position)}
            values = (
                [by_name[name] for name in expected_message_names]
                if all(name in by_name for name in expected_message_names)
                else None
            )
        elif len(msg.position) == len(feature_names):
            values = [float(value) for value in msg.position]
        else:
            return None
        if values is None:
            return None
        return dict(zip(feature_names, values))

    def _hand_state_cb(self, side: str, msg: JointState) -> None:
        positions = self._ordered_hand_positions(side, msg)
        if positions is None:
            return
        with self._lock:
            self._hand_positions[side] = positions

    def _hand_command_cb(self, side: str, msg: JointState) -> None:
        positions = self._ordered_hand_positions(side, msg)
        if positions is None:
            return
        with self._lock:
            self._hand_command_positions[side] = positions

    def get_arm_positions(self, joint_names: list[str]) -> dict[str, float] | None:
        with self._lock:
            if not self._arm_positions:
                return None
            return {name: self._arm_positions[name] for name in joint_names if name in self._arm_positions}

    def get_hand_positions(self, side: str) -> dict[str, float] | None:
        with self._lock:
            positions = self._hand_positions[side]
            if positions:
                return dict(positions)
            command_positions = self._hand_command_positions[side]
            return dict(command_positions) if command_positions else None

    def _require_connected(self) -> None:
        if not self.is_connected or self._node is None:
            raise DeviceNotConnectedError("OpenArmXO6Ros2Interface not connected")

    def send_arm_positions(self, side: str, positions: list[float]) -> None:
        self._require_connected()
        publisher = self._left_arm_pub if side == "left" else self._right_arm_pub
        if publisher is None:
            raise DeviceNotConnectedError(f"{side} arm publisher is unavailable")
        msg = Float64MultiArray()
        msg.data = [float(value) for value in positions]
        publisher.publish(msg)

    def send_hand_positions(self, side: str, positions: list[float]) -> None:
        self._require_connected()
        publisher = self._left_hand_pub if side == "left" else self._right_hand_pub
        if publisher is None:
            raise DeviceNotConnectedError(f"{side} hand publisher is unavailable")
        msg = JointState()
        msg.header.stamp = self._node.get_clock().now().to_msg()
        msg.name = list(self.config.hand_message_joint_names)
        msg.position = [float(value) for value in positions]
        publisher.publish(msg)
