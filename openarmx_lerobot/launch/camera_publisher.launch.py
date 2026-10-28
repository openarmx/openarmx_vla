#!/usr/bin/env python3
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

"""
RealSense 相机 ROS2 发布节点启动文件。

在工控机上运行此 launch 文件，将三个 RealSense 相机的 RGB 图像和深度图通过 ROS2 话题发布。
其他设备（如 Jetson）可以通过订阅这些话题获取相机数据。

支持的相机类型:
    - D405: RGB 集成在深度模块
    - D435: 独立 RGB 模块

话题统一映射 (接收端使用统一格式，无需关心相机类型):
    - /cam_left/color/image   (RGB 图像)
    - /cam_left/depth/image   (深度图)
    - /cam_right/color/image
    - /cam_right/depth/image
    - /cam_head/color/image
    - /cam_head/depth/image

命令行参数:
    - width: 图像宽度 (默认: 424)
    - height: 图像高度 (默认: 240)
    - fps: 帧率 (默认: 15)
    - cam_left_serial: 左手相机序列号 (默认: 218622270388)
    - cam_left_type: 左手相机类型 D405/D435/D435I (默认: D405)
    - cam_right_serial: 右手相机序列号 (默认: 218622274446)
    - cam_right_type: 右手相机类型 D405/D435/D435I (默认: D405)
    - cam_head_serial: 头部相机序列号 (默认: 335522070220)
    - cam_head_type: 头部相机类型 D405/D435/D435I (默认: D435)
    - cam_*_color_auto_exposure: 颜色自动曝光，支持 true/false/unset
    - cam_*_color_exposure: 颜色手动曝光，范围 1..10000
    - cam_*_color_gain: 颜色手动增益，范围 0..128
    - cam_*_color_auto_white_balance: 颜色自动白平衡，支持 true/false/unset
    - cam_*_color_white_balance: 颜色手动白平衡，范围 2800..6500
    - cam_*_color_brightness: 亮度，范围 -64..64
    - cam_*_color_contrast: 对比度，范围 0..100
    - cam_*_color_saturation: 饱和度，范围 0..100
    - cam_*_color_sharpness: 锐度，范围 0..100

使用方法:
    # 默认配置启动
    ros2 launch openarmx_lerobot camera_publisher.launch.py

    # 自定义分辨率和帧率
    ros2 launch openarmx_lerobot camera_publisher.launch.py width:=640 height:=480 fps:=30

    # 自定义相机配置
    ros2 launch openarmx_lerobot camera_publisher.launch.py \\
        cam_left_serial:=123456789012 cam_left_type:=D435 \\
        cam_head_serial:=987654321098 cam_head_type:=D405

    # 单独调左手相机颜色曝光/增益
    ros2 launch openarmx_lerobot camera_publisher.launch.py \\
        cam_left_color_auto_exposure:=false \\
        cam_left_color_exposure:=400 \\
        cam_left_color_gain:=32

    # 关闭头部相机自动白平衡并设置手动白平衡
    ros2 launch openarmx_lerobot camera_publisher.launch.py \\
        cam_head_color_auto_white_balance:=false \\
        cam_head_color_white_balance:=4600

    # 确保所有设备使用相同的 ROS_DOMAIN_ID
    export ROS_DOMAIN_ID=42
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


# ============================================================================
# 支持的分辨率和帧率配置
# ============================================================================

# D405 支持的配置 (RGB 和深度共用深度模块)
D405_SUPPORTED_PROFILES = {
    # (width, height): [supported fps list]
    (1280, 720): [5, 15, 30],
    (848, 480): [5, 15, 30, 60, 90],
    (640, 480): [5, 15, 30, 60, 90],
    (640, 360): [5, 15, 30, 60, 90],
    (480, 270): [5, 15, 30, 60, 90],
    (424, 240): [5, 15, 30, 60, 90],
}

# D435 支持的配置
# 注意: D435 的 RGB 和深度模块分辨率可以不同，这里列出常用的共同支持配置
D435_SUPPORTED_PROFILES = {
    # (width, height): [supported fps list]
    (1920, 1080): [6, 15, 30],
    (1280, 720): [6, 15, 30],
    (848, 480): [6, 15, 30, 60, 90],
    (640, 480): [6, 15, 30, 60, 90],
    (640, 360): [6, 15, 30, 60, 90],
    (480, 270): [6, 15, 30, 60, 90],
    (424, 240): [6, 15, 30, 60, 90],
}


# ============================================================================
# 颜色控制参数
# ============================================================================

UNSET = "unset"
SUPPORTED_CAMERA_TYPES = {"D405", "D435", "D435I"}
TRUTHY_VALUES = {"1", "true", "yes", "on"}
FALSY_VALUES = {"0", "false", "no", "off"}
CAMERA_CONTROL_ARGUMENTS = {
    "color_auto_exposure": {
        "type": "bool",
        "param": "rgb_camera.enable_auto_exposure",
        "description": "颜色自动曝光，true/false/unset",
    },
    "color_exposure": {
        "type": "int",
        "param": "rgb_camera.exposure",
        "min": 1,
        "max": 10000,
        "description": "颜色手动曝光，范围 1..10000，unset 表示不设置",
    },
    "color_gain": {
        "type": "int",
        "param": "rgb_camera.gain",
        "min": 0,
        "max": 128,
        "description": "颜色手动增益，范围 0..128，unset 表示不设置",
    },
    "color_auto_white_balance": {
        "type": "bool",
        "param": "rgb_camera.enable_auto_white_balance",
        "description": "颜色自动白平衡，true/false/unset",
    },
    "color_white_balance": {
        "type": "int",
        "param": "rgb_camera.white_balance",
        "min": 2800,
        "max": 6500,
        "description": "颜色手动白平衡，范围 2800..6500，unset 表示不设置",
    },
    "color_brightness": {
        "type": "int",
        "param": "rgb_camera.brightness",
        "min": -64,
        "max": 64,
        "description": "颜色亮度，范围 -64..64，unset 表示不设置",
    },
    "color_contrast": {
        "type": "int",
        "param": "rgb_camera.contrast",
        "min": 0,
        "max": 100,
        "description": "颜色对比度，范围 0..100，unset 表示不设置",
    },
    "color_saturation": {
        "type": "int",
        "param": "rgb_camera.saturation",
        "min": 0,
        "max": 100,
        "description": "颜色饱和度，范围 0..100，unset 表示不设置",
    },
    "color_sharpness": {
        "type": "int",
        "param": "rgb_camera.sharpness",
        "min": 0,
        "max": 100,
        "description": "颜色锐度，范围 0..100，unset 表示不设置",
    },
}


def normalize_camera_type(cam_type: str) -> str:
    return cam_type.strip().upper()


def parse_optional_bool(raw_value: str, arg_name: str) -> bool | None:
    value = raw_value.strip().lower()
    if value in ("", UNSET):
        return None
    if value in TRUTHY_VALUES:
        return True
    if value in FALSY_VALUES:
        return False
    raise RuntimeError(
        f"参数 {arg_name} 必须是 true/false/{UNSET}，当前值: {raw_value}"
    )


def parse_optional_int(raw_value: str, arg_name: str) -> int | None:
    value = raw_value.strip().lower()
    if value in ("", UNSET):
        return None
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"参数 {arg_name} 必须是整数或 {UNSET}，当前值: {raw_value}") from exc


def validate_integer_range(arg_name: str, value: int | None, min_value: int, max_value: int) -> None:
    if value is None:
        return
    if not (min_value <= value <= max_value):
        raise RuntimeError(
            f"参数 {arg_name} 超出范围: {value}，允许范围: {min_value}..{max_value}"
        )


def parse_camera_controls(context, camera_name: str, cam_type: str) -> tuple[dict[str, object], list[str]]:
    """解析并校验每路相机的颜色控制参数。

    说明:
        - 这里按照 realsense2_camera 的公开参数命名
        - D405: 颜色流来自深度传感器，参数需映射到 depth_module.* (如 depth_module.exposure)
        - D435/D435I: 独立 RGB 传感器，参数映射到 rgb_camera.*
    """
    cam_type_upper = normalize_camera_type(cam_type)
    if cam_type_upper not in SUPPORTED_CAMERA_TYPES:
        raise RuntimeError(f"{camera_name} 不支持的相机类型: {cam_type}")

    # 根据相机类型确定参数前缀
    # D405 没有独立的 rgb_camera，其颜色控制实际上是控制 depth_module
    if cam_type_upper == "D405":
        param_prefix = "depth_module"
        src_prefix = "rgb_camera"
    else:
        param_prefix = "rgb_camera"
        src_prefix = "rgb_camera"

    controls: dict[str, object] = {}
    applied_logs: list[str] = []

    for option_name, spec in CAMERA_CONTROL_ARGUMENTS.items():
        arg_name = f"{camera_name}_{option_name}"
        raw_value = LaunchConfiguration(arg_name).perform(context)

        if spec["type"] == "bool":
            parsed_value = parse_optional_bool(raw_value, arg_name)
        else:
            parsed_value = parse_optional_int(raw_value, arg_name)
            validate_integer_range(arg_name, parsed_value, spec["min"], spec["max"])

        if parsed_value is not None:
            # 替换参数前缀
            param_name = spec["param"].replace(src_prefix, param_prefix)
            controls[param_name] = parsed_value
            applied_logs.append(f"{option_name}={parsed_value}")

    # 校验逻辑也需要使用正确的前缀
    color_auto_exposure = controls.get(f"{param_prefix}.enable_auto_exposure")
    color_exposure = controls.get(f"{param_prefix}.exposure")
    color_gain = controls.get(f"{param_prefix}.gain")
    color_auto_white_balance = controls.get(f"{param_prefix}.enable_auto_white_balance")
    color_white_balance = controls.get(f"{param_prefix}.white_balance")

    if color_auto_exposure is True:
        if color_exposure is not None:
            controls.pop(f"{param_prefix}.exposure", None)
            applied_logs.append("color_exposure=ignored(auto)")
        if color_gain is not None:
            controls.pop(f"{param_prefix}.gain", None)
            applied_logs.append("color_gain=ignored(auto)")
    if color_auto_white_balance is True and color_white_balance is not None:
        raise RuntimeError(
            f"{camera_name} 同时设置了颜色自动白平衡=true 与手动白平衡，请改为 false 或移除手动值。"
        )

    if color_auto_exposure is None and (color_exposure is not None or color_gain is not None):
        controls[f"{param_prefix}.enable_auto_exposure"] = False
        applied_logs.append("color_auto_exposure=False(auto)")

    if color_auto_white_balance is None and color_white_balance is not None:
        controls[f"{param_prefix}.enable_auto_white_balance"] = False
        applied_logs.append("color_auto_white_balance=False(auto)")

    return controls, applied_logs


def create_camera_control_arguments() -> list[DeclareLaunchArgument]:
    arguments: list[DeclareLaunchArgument] = []
    for camera_name in ("cam_left", "cam_right", "cam_head"):
        for option_name, spec in CAMERA_CONTROL_ARGUMENTS.items():
            arguments.append(
                DeclareLaunchArgument(
                    f"{camera_name}_{option_name}",
                    default_value=UNSET,
                    description=f"{camera_name} {spec['description']}",
                )
            )
    return arguments


def validate_profile(cam_type: str, width: int, height: int, fps: int) -> tuple[bool, str]:
    """
    验证相机配置是否支持。

    Args:
        cam_type: 相机类型 (D405 或 D435)
        width: 图像宽度
        height: 图像高度
        fps: 帧率

    Returns:
        (is_valid, message): 是否有效及提示信息
    """
    cam_type_upper = cam_type.upper()

    if cam_type_upper == "D405":
        profiles = D405_SUPPORTED_PROFILES
    elif cam_type_upper in ("D435", "D435I"):
        profiles = D435_SUPPORTED_PROFILES
    else:
        return False, f"不支持的相机类型: {cam_type}，仅支持 D405、D435 和 D435I"

    resolution = (width, height)

    if resolution not in profiles:
        supported_res = ", ".join([f"{w}x{h}" for w, h in profiles.keys()])
        return False, (
            f"{cam_type_upper} 不支持分辨率 {width}x{height}\n"
            f"支持的分辨率: {supported_res}"
        )

    supported_fps = profiles[resolution]
    if fps not in supported_fps:
        return False, (
            f"{cam_type_upper} 在分辨率 {width}x{height} 下不支持帧率 {fps}\n"
            f"支持的帧率: {supported_fps}"
        )

    return True, f"{cam_type_upper} 配置有效: {width}x{height}@{fps}fps"


def create_camera_node(
    context,
    name: str,
    serial: str,
    cam_type: str,
    profile: str,
    extra_camera_params: dict[str, object] | None = None,
):
    """
    创建 RealSense 相机节点，并统一话题名称。

    Args:
        context: Launch context
        name: 相机名称 (如 cam_left, cam_right, cam_head)
        serial: 相机序列号
        cam_type: 相机类型 (D405 或 D435)
        profile: 分辨率和帧率配置字符串 (如 "424x240x15")

    Returns:
        配置好的 Node 对象
    """
    # 获取实际参数值
    serial_value = serial.perform(context) if hasattr(serial, 'perform') else serial
    cam_type_value = cam_type.perform(context) if hasattr(cam_type, 'perform') else cam_type
    profile_value = profile.perform(context) if hasattr(profile, 'perform') else profile

    # 序列号需要添加下划线前缀
    serial_str = f"_{serial_value}"

    # 根据相机类型确定原始话题名称和参数配置
    if normalize_camera_type(cam_type_value) == "D405":
        # D405: RGB 集成在深度模块。当前 realsense2_camera 发布 color/image_raw。
        # D405 的 RGB 和 深度是物理同轴的，不需要软件对齐，原始深度图即已对齐
        camera_params = {
            "serial_no": serial_str,
            "depth_module.color_profile": profile_value,
            "depth_module.depth_profile": profile_value,
            "enable_color": True,
            "enable_depth": True,
            "align_depth.enable": False, # D405 不需要软件对齐
            "enable_infra1": False,
            "enable_infra2": False,
            "enable_gyro": False,
            "enable_accel": False,
            "pointcloud.enable": False,
        }
        original_color_topic = f"/{name}/{name}/color/image_raw"
        # D405 直接使用原始深度图（已物理对齐）
        original_depth_topic = f"/{name}/{name}/depth/image_raw"
    else:
        # D435/D435i: 独立 RGB 模块，原始话题是 image_raw
        camera_params = {
            "serial_no": serial_str,
            "rgb_camera.color_profile": profile_value,
            "depth_module.depth_profile": profile_value,
            "enable_color": True,
            "enable_depth": True,
            "align_depth.enable": True,
            "enable_infra1": False,
            "enable_infra2": False,
            "enable_gyro": False,
            "enable_accel": False,
            "pointcloud.enable": False,
        }
        # D435 的原始 RGB 话题是 color/image_raw
        original_color_topic = f"/{name}/{name}/color/image_raw"
        # D435 需要使用对齐后的深度图
        original_depth_topic = f"/{name}/{name}/aligned_depth_to_color/image_raw"

    if extra_camera_params:
        camera_params.update(extra_camera_params)

    # 统一后的话题名称

    # 统一后的话题名称
    unified_color_topic = f"/{name}/color/image"
    unified_depth_topic = f"/{name}/depth/image"

    # 设置话题重映射
    remappings = [
        (original_color_topic, unified_color_topic),
        (original_depth_topic, unified_depth_topic),
    ]

    return Node(
        package="realsense2_camera",
        executable="realsense2_camera_node",
        name=name,
        namespace=name,
        parameters=[camera_params],
        remappings=remappings,
        output="screen",
    )


def launch_setup(context, *args, **kwargs):
    """动态创建相机节点"""
    # 获取配置参数
    width = int(LaunchConfiguration('width').perform(context))
    height = int(LaunchConfiguration('height').perform(context))
    fps = int(LaunchConfiguration('fps').perform(context))

    # 构建 profile 字符串
    profile = f"{width}x{height}x{fps}"

    # 获取各相机配置
    cam_left_serial = LaunchConfiguration('cam_left_serial')
    cam_left_type = LaunchConfiguration('cam_left_type')
    cam_right_serial = LaunchConfiguration('cam_right_serial')
    cam_right_type = LaunchConfiguration('cam_right_type')
    cam_head_serial = LaunchConfiguration('cam_head_serial')
    cam_head_type = LaunchConfiguration('cam_head_type')

    # 获取相机类型字符串用于校验
    cam_left_type_str = normalize_camera_type(cam_left_type.perform(context))
    cam_right_type_str = normalize_camera_type(cam_right_type.perform(context))
    cam_head_type_str = normalize_camera_type(cam_head_type.perform(context))

    # 校验所有相机配置
    cameras_to_validate = [
        ("cam_left", cam_left_type_str),
        ("cam_right", cam_right_type_str),
        ("cam_head", cam_head_type_str),
    ]

    log_actions = []
    has_error = False

    for cam_name, cam_type_str in cameras_to_validate:
        is_valid, message = validate_profile(cam_type_str, width, height, fps)
        if not is_valid:
            has_error = True
            log_actions.append(
                LogInfo(msg=f"\n[ERROR] {cam_name} ({cam_type_str}) 配置无效:\n{message}\n")
            )
        else:
            log_actions.append(
                LogInfo(msg=f"[INFO] {cam_name}: {message}")
            )

    # 解析每路相机的颜色控制参数
    cam_left_controls, cam_left_control_logs = parse_camera_controls(context, "cam_left", cam_left_type_str)
    cam_right_controls, cam_right_control_logs = parse_camera_controls(context, "cam_right", cam_right_type_str)
    cam_head_controls, cam_head_control_logs = parse_camera_controls(context, "cam_head", cam_head_type_str)

    for cam_name, applied_logs in (
        ("cam_left", cam_left_control_logs),
        ("cam_right", cam_right_control_logs),
        ("cam_head", cam_head_control_logs),
    ):
        if applied_logs:
            log_actions.append(LogInfo(msg=f"[INFO] {cam_name} 颜色参数: {', '.join(applied_logs)}"))

    if has_error:
        # 打印支持的配置帮助信息
        log_actions.append(LogInfo(msg="\n" + "=" * 60))
        log_actions.append(LogInfo(msg="请参考 README 文档选择支持的分辨率和帧率组合"))
        log_actions.append(LogInfo(msg="或使用命令 rs-enumerate-devices -c 查看相机支持的配置"))
        log_actions.append(LogInfo(msg="=" * 60 + "\n"))

        # 返回错误信息但不创建节点
        raise RuntimeError(
            f"\n配置校验失败！\n"
            f"当前配置: {width}x{height}@{fps}fps\n"
            f"请检查相机类型和分辨率/帧率是否匹配。\n"
            f"运行 'rs-enumerate-devices -c' 查看相机支持的配置。"
        )

    # 创建相机节点
    cam_left_node = create_camera_node(
        context, "cam_left", cam_left_serial, cam_left_type, profile, cam_left_controls
    )
    cam_right_node = create_camera_node(
        context, "cam_right", cam_right_serial, cam_right_type, profile, cam_right_controls
    )
    cam_head_node = create_camera_node(
        context, "cam_head", cam_head_serial, cam_head_type, profile, cam_head_controls
    )

    return log_actions + [cam_left_node, cam_right_node, cam_head_node]


def generate_launch_description():
    return LaunchDescription([
        # 分辨率和帧率参数
        DeclareLaunchArgument(
            'width',
            default_value='424',
            description='图像宽度 (像素)'
        ),
        DeclareLaunchArgument(
            'height',
            default_value='240',
            description='图像高度 (像素)'
        ),
        DeclareLaunchArgument(
            'fps',
            default_value='15',
            description='帧率 (Hz)'
        ),

        # 左手相机参数
        DeclareLaunchArgument(
            'cam_left_serial',
            default_value='218622270388',
            description='左手相机序列号'
        ),
        DeclareLaunchArgument(
            'cam_left_type',
            default_value='D405',
            description='左手相机类型 (D405、D435 或 D435I)'
        ),

        # 右手相机参数
        DeclareLaunchArgument(
            'cam_right_serial',
            default_value='218622274446',
            description='右手相机序列号'
        ),
        DeclareLaunchArgument(
            'cam_right_type',
            default_value='D405',
            description='右手相机类型 (D405、D435 或 D435I)'
        ),

        # 头部相机参数
        DeclareLaunchArgument(
            'cam_head_serial',
            default_value='335522070220',
            description='头部相机序列号'
        ),
        DeclareLaunchArgument(
            'cam_head_type',
            default_value='D435',
            description='头部相机类型 (D405、D435 或 D435I)'
        ),

    ] + create_camera_control_arguments() + [
        # 使用 OpaqueFunction 动态创建节点
        OpaqueFunction(function=launch_setup),
    ])
