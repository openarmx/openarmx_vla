# OpenArmX VLA 使用指南（LeRobot）

本文档介绍如何使用 OpenArmX 机器人在 LeRobot 框架下完成 VLA 数据采集、ACT 训练与推理。

<span style="background:#E8F5E9;padding:2px 8px;border-radius:6px;"><b>✅ 成功提示</b></span>
<span style="background:#FFF8E1;padding:2px 8px;border-radius:6px;"><b>⚠️ 注意事项</b></span>
<span style="background:#FFEBEE;padding:2px 8px;border-radius:6px;"><b>🚨 高风险项</b></span>
<span style="background:#E3F2FD;padding:2px 8px;border-radius:6px;"><b>💡 实用建议</b></span>

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 本文档最重要的三件事：</b></span>  
> <b>1)</b> 启动顺序必须严格按步骤执行。  
> <b>2)</b> `W/H/FPS` 在相机发布、采集、推理三处必须完全一致。  
> <b>3)</b> 采集前先改 `config/vla_collect.env` 的数据集参数。

## 目录

1. 设备分工
2. 通用前置条件
3. VLA 数据采集流程（工控机）
   - 3.1 手动启动顺序（必须按顺序）
   - 3.2 GUI 一键启动（推荐）
   - 3.3 话题快速检查（可选）
   - 3.4 录制界面按键说明
   - 3.5 数据采集命令参数说明
4. ACT 训练流程（用户高性能电脑/服务器）
   - 4.1 训练前说明
   - 4.2 ACT 依赖模型下载
   - 4.3 ACT 训练命令
5. VLA 推理流程（工控机 + 推理机）
   - 5.1 推理前置条件
   - 5.2 启动顺序
   - 5.3 推理命令参数说明
6. 两机协同时的 ROS_DOMAIN_ID 配置
   - 6.1 检查当前配置
   - 6.2 统一配置为同一值（如 77，若不一致）
   - 6.3 再次验证
7. 相机参数配置参考
   - 7.1 命令中哪些参数需要改
   - 7.2 可用分辨率/帧率组合（D405 / D435）
   - 7.3 三相机带宽上限与推荐配置

---

## 🧩 1. 设备分工

- **工控机（我们提供）**：机器人 CAN 控制、Pico VR 遥操作、3 台相机发布、LeRobot 数据采集。
- **用户机器（您自行配置）**：模型训练与推理（可与工控机联动）。

## ✅ 2. 通用前置条件

- 工控机已编译工作空间，并可正常执行 `source ~/openarmx_ws/install/setup.bash`。
- 机器人可以正常启动，并可通过 VR 遥操作。
- 双机通信在第 5 节推理场景需要；请根据第6节设置DOMAIN ID。

> <span style="background:#FFF8E1;color:#8A6D3B;padding:2px 6px;border-radius:4px;"><b>⚠️ 若第 2 节不满足，后续步骤大概率失败。</b></span>

---

## 📦 3. VLA 数据采集流程（工控机）

### 🚦 3.1 手动启动顺序（必须按顺序）

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 严禁跳步或并行乱序启动。</b></span>

#### Step 1：启动机器人真机

```bash
cd ~/openarmx_ws
source install/setup.bash
ros2 launch openarmx_bringup openarmx.bimanual.launch.py \
  control_mode:=mit \
  robot_controller:=forward_position_controller \
  use_fake_hardware:=false
```

#### Step 2：启动 Pico Bridge

```bash
cd ~/openarmx_ws
source install/setup.bash
ros2 run openarmx_teleop_bridge_vr_pico openarmx_teleop_bridge_vr_pico_node
```

#### Step 3：启动 VR 遥操作

```bash
cd ~/openarmx_ws
source install/setup.bash
ros2 launch openarmx_teleop_vr_pico teleop_vr_pico.launch.py
```

#### Step 4：启动三相机发布

请先将命令中的相机型号与序列号替换为你自己的设备参数：

- 支持相机型号：`D435`、`D405`
- `cam_left_*` / `cam_right_*` / `cam_head_*` 分别对应左手、右手、头部相机
- 查询序列号：`rs-enumerate-devices | grep "Serial Number"`

在标配工控机 + 标配拓展坞下，三相机稳定上限为 `640x480 @ 30fps`。
相机参数如何选择与可用组合，请见第 7 节《相机参数配置参考》。

> <span style="background:#E3F2FD;color:#0D47A1;padding:2px 6px;border-radius:4px;"><b>💡 默认建议先用 `424x240 @ 30fps` 跑通流程，再逐步提分辨率。</b></span>

```bash
cd ~/openarmx_ws
source install/setup.bash
W=424; H=240; FPS=30
ros2 launch openarmx_lerobot camera_publisher.launch.py \
  width:=$W height:=$H fps:=$FPS \
  cam_left_serial:=218622270388 cam_left_type:=D405 \
  cam_right_serial:=218622274446 cam_right_type:=D405 \
  cam_head_serial:=335522070220 cam_head_type:=D435
```

你需要按实际设备修改这些参数：

- `W` / `H` / `FPS`：三相机统一分辨率与帧率（示例为 `424x240@30`）。
- `cam_left_serial` / `cam_right_serial` / `cam_head_serial`：替换成你的三台相机序列号。
- `cam_left_type` / `cam_right_type` / `cam_head_type`：按相机实际型号填 `D405` 或 `D435`。

如果需要在启动时同时调三台相机的曝光参数，可以使用下面的示例：

```bash
cd ~/openarmx_ws
source install/setup.bash
W=424; H=240; FPS=30
ros2 launch openarmx_lerobot camera_publisher.launch.py \
  width:=$W height:=$H fps:=$FPS \
  cam_left_serial:=218622270388 cam_left_type:=D405 \
  cam_right_serial:=218622274446 cam_right_type:=D405 \
  cam_head_serial:=335522070220 cam_head_type:=D435 \
  cam_left_color_auto_exposure:=true \
  cam_left_color_exposure:=10000 \
  cam_left_color_gain:=32 \
  cam_right_color_auto_exposure:=true \
  cam_right_color_exposure:=10000 \
  cam_right_color_gain:=32 \
  cam_head_color_auto_exposure:=true \
  cam_head_color_exposure:=10000 \
  cam_head_color_gain:=16
```

常用可调颜色参数如下：

- `cam_*_color_auto_exposure`：颜色自动曝光，取值 `true/false/unset`
- `cam_*_color_exposure`：颜色手动曝光，范围 `1..10000`
- `cam_*_color_gain`：颜色手动增益，范围 `0..128`
- `cam_*_color_auto_white_balance`：颜色自动白平衡，取值 `true/false/unset`
- `cam_*_color_white_balance`：颜色手动白平衡，范围 `2800..6500`
- `cam_*_color_brightness`：亮度，范围 `-64..64`
- `cam_*_color_contrast`：对比度，范围 `0..100`
- `cam_*_color_saturation`：饱和度，范围 `0..100`
- `cam_*_color_sharpness`：锐度，范围 `0..100`

说明：

- `cam_left_*` / `cam_right_*` / `cam_head_*` 分别作用于左手、右手、头部相机
- `unset` 表示不主动设置该参数，保持驱动默认行为
- 若只写 `cam_*_color_exposure` 或 `cam_*_color_gain`，launch 会自动补成 `cam_*_color_auto_exposure:=false`
- 若只写 `cam_*_color_white_balance`，launch 会自动补成 `cam_*_color_auto_white_balance:=false`

#### Step 5：启动 LeRobot 数据采集

先进入 LeRobot 环境，再执行录制命令：

- `W/H/FPS` 用于配置采集时的相机分辨率与帧率（例如 `W=640; H=480; FPS=30`）。
- 这里的 `W/H/FPS` 必须与相机发布节点 `camera_publisher.launch.py` 的 `width/height/fps` 完全一致。
- 修改相机发布节点的 W/H/FPS 后，请同步将数据采集命令中的 W/H/FPS 改为一致；否则相机格式不匹配会导致报错。

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 关键约束：`采集 W/H/FPS` = `相机发布 width/height/fps`。</b></span>

```bash
lerobot-env
W=424; H=240; FPS=30
HF_HUB_OFFLINE=1 lerobot-record \
  --robot.type=openarmx_follower_ros2 \
  --robot.cameras="{cam_left: {type: ros2, image_topic: /cam_left/color/image, depth_topic: /cam_left/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_right: {type: ros2, image_topic: /cam_right/color/image, depth_topic: /cam_right/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_head: {type: ros2, image_topic: /cam_head/color/image, depth_topic: /cam_head/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}}" \
  --teleop.type=openarmx_leader_ros2 \
  --dataset.repo_id=local/你的数据名称 \
  --dataset.single_task="你执行的任务名称" \
  --dataset.num_episodes=采集的总组数 \
  --dataset.episode_time_s=每一组的时间(秒) \
  --dataset.reset_time_s=采完一组后的间隔时间 \
  --dataset.push_to_hub=false \
  --display_data=true
```

示例：

```bash
lerobot-env
W=424; H=240; FPS=30
HF_HUB_OFFLINE=1 lerobot-record \
  --robot.type=openarmx_follower_ros2 \
  --robot.cameras="{cam_left: {type: ros2, image_topic: /cam_left/color/image, depth_topic: /cam_left/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_right: {type: ros2, image_topic: /cam_right/color/image, depth_topic: /cam_right/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_head: {type: ros2, image_topic: /cam_head/color/image, depth_topic: /cam_head/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}}" \
  --teleop.type=openarmx_leader_ros2 \
  --dataset.repo_id=local/take_box \
  --dataset.single_task="take box" \
  --dataset.num_episodes=70 \
  --dataset.episode_time_s=180 \
  --dataset.reset_time_s=5 \
  --dataset.push_to_hub=false \
  --display_data=true
```

### 🚀 3.2 GUI 一键启动（推荐）

如果你希望像本节 3.1 一样，按固定顺序自动拉起多个终端窗口，可以使用仓库内的一键启动脚本：

- `scripts/vla_collect_gui.sh`：GUI 多终端一键启动脚本
- ⚠️ `config/vla_collect.env`：一键启动配置文件，集中保存机器人、相机、数采参数。<span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>请优先在这里修改参数</b></span>
- `scripts/README_GUI_CN.md`：一键启动的独立说明文档

建议先进入仓库目录：

```bash
cd /home/openarmx/openarmx_ws/src/openarmx_vla
```

启动前可先做一次自检：

```bash
bash scripts/vla_collect_gui.sh check
```

自检会检查以下项目：

- `WORKSPACE_DIR/install/setup.bash` 是否存在
- 当前是否处于图形桌面会话（`DISPLAY` / `WAYLAND_DISPLAY`）
- `GUI_TERMINAL` 指定的终端命令是否可用（默认 `gnome-terminal`）
- `ros2` 是否可用
- 在 `collect` 场景下，交互式 shell 中是否能找到 `LEROBOT_ENV_CMD`（默认 `lerobot-env`）

常用启动方式：

```bash
# 1. 只启动机器人真机 + Pico Bridge + VR Teleop
bash scripts/vla_collect_gui.sh base

# 2. 启动机器人底层 + 相机发布
bash scripts/vla_collect_gui.sh base_camera

# 3. 启动机器人底层 + 相机发布 + LeRobot 数采
# ⚠️ 注意：每次一键启动数采前，先修改 config/vla_collect.env 中 DATASET_REPO_ID
bash scripts/vla_collect_gui.sh collect

# 关闭本脚本拉起的所有终端
bash scripts/vla_collect_gui.sh stop
```

> <span style="background:#FFF8E1;color:#8A6D3B;padding:2px 6px;border-radius:4px;"><b>⚠️ `collect` 前务必检查 `DATASET_REPO_ID`，避免写到错误数据集目录。</b></span>

各模式对应关系如下：

- `base`：等价于手动执行“机器人真机 + Pico Bridge + VR 遥操作”三步
- `base_camera`：在 `base` 基础上继续启动三相机发布
- `collect`：在 `base_camera` 基础上继续启动 LeRobot 数据采集
- `stop`：按状态文件精准关闭本脚本拉起的窗口；即使你手动关过部分窗口，也不会报错

脚本启动特性说明：

- 会按顺序弹出多个终端窗口，并按配置的延时依次启动各模块
- 每个窗口执行结束后会保留在终端中，方便现场排查报错
- 若检测到上一次启动的窗口仍在运行，会提示你先执行 `bash scripts/vla_collect_gui.sh stop`
- `collect` 模式会在录制终端中先执行 `LEROBOT_ENV_CMD`，再执行 `lerobot-record`
- 默认配置文件路径为 `config/vla_collect.env`，也可通过 `VLA_CONFIG_FILE=/你的路径.env bash scripts/vla_collect_gui.sh collect` 临时切换配置

你通常只需要修改 `config/vla_collect.env` 中这些内容：

- 基础路径与 GUI 参数：工作空间路径、终端命令、窗口状态文件路径
- 机器人底层参数：`CONTROL_MODE`、`ROBOT_CONTROLLER`、`USE_FAKE_HARDWARE`
- VR 遥操作参数：Pico / Teleop 的控制速率、抓取阈值、话题名等
- 相机参数：`W/H/FPS`、三台相机序列号、相机型号、曝光/增益/白平衡等
- 数采参数：数据集名称、任务描述、episode 数、单轮时长、重置时间、是否显示数据等

其中需要特别注意：

- `W/H/FPS` 会同时用于相机发布和 `lerobot-record`，请保持与相机实际输出一致
- `CAM_LEFT_TYPE` / `CAM_RIGHT_TYPE` / `CAM_HEAD_TYPE` 需按真实设备填写 `D405` 或 `D435`
- `CAM_LEFT_SERIAL` / `CAM_RIGHT_SERIAL` / `CAM_HEAD_SERIAL` 需替换为你自己的相机序列号
- 若使用 `collect` 模式，请确认 `DATASET_REPO_ID`、`DATASET_SINGLE_TASK` 等数据集参数已改成你的任务

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 上述 4 项属于高频出错点，建议每次采集前逐条核对。</b></span>

更完整的一键启动单独说明，请参考：`scripts/README_GUI_CN.md`。

### 🔎 3.3 话题快速检查（可选）

```bash
ros2 topic list | grep cam
ros2 topic list | grep joint_states
ros2 topic list | grep forward_position_controller/commands
```

预期至少看到：

- 相机话题：`/cam_left/color/image`、`/cam_right/color/image`、`/cam_head/color/image`
- 关节状态：`/joint_states`
- 遥操作输出：`/left_forward_position_controller/commands`、`/right_forward_position_controller/commands`

若满足以上条件，说明可以进行数据采集。

### ⌨️ 3.4 录制界面按键说明

- `→`（右箭头）：结束当前 episode 并保存，然后进入重置阶段。
- `←`（左箭头）：丢弃当前 episode，重新录制。
- `Esc`：停止录制并退出，保存数据集。

### 🧾 3.5 数据采集命令参数说明

常用参数：

- `HF_HUB_OFFLINE=1`：启用 Hugging Face Hub 离线模式。
- `--robot.type=openarmx_follower_ros2`：指定被控制机器人类型。
- `--teleop.type=openarmx_leader_ros2`：指定遥操作设备类型。
- `--dataset.repo_id=local/xxx`：数据集存储标识（路径在 `~/.cache/huggingface/lerobot/local/`）。
- `--dataset.single_task`：任务描述。
- `--dataset.num_episodes`：总 episode 数量。
- `--dataset.episode_time_s`：单组最长时长（秒）。
- `--dataset.reset_time_s`：组间重置等待时间（秒）。
- `--dataset.push_to_hub`：是否上传到 Hugging Face Hub。
- `--display_data`：是否显示实时数据。

其他参数：

- `--dataset.root`：自定义数据集保存路径。
- `--dataset.fps`：限制采集帧率。
- `--dataset.video`：是否将图像编码为视频。
- `--dataset.vcodec`：视频编码器（默认 `libsvtav1`）。
- `--dataset.video_encoding_batch_size`：批量视频编码的 episode 数。
- `--dataset.private`：上传到 Hub 时设置为私有。
- `--dataset.tags`：Hub 数据集标签。
- `--dataset.num_image_writer_processes`：图像写入进程数。
- `--dataset.num_image_writer_threads_per_camera`：每个相机的写入线程数。
- `--dataset.rename_map`：重命名观测键名。

### 🖐️ 3.6 双 O6 灵巧手数据采集

O6 灵巧手使用独立的 LeRobot 类型，不会改变原夹爪类型：

```text
普通夹爪：openarmx_follower_ros2 + openarmx_leader_ros2（16维）
双O6手： openarmx_follower_o6_ros2 + openarmx_leader_o6_ros2（26维）
```

首次使用或代码更新后，在 LeRobot 环境中重新安装两个插件：

```bash
pip install -e ./lerobot_robot_openarmx_follower_ros2
pip install -e ./lerobot_teleoperator_openarmx_leader_ros2
```

与夹爪流程相同，O6 的底层、VR 和手套节点分别启动。VLA 不额外提供组合 launch。

#### Step 1：启动双臂和双 O6

```bash
ros2 launch openarmx_hand_bringup openarmx.bimanual.o6.launch.py \
  control_mode:=mit \
  robot_controller:=forward_position_controller \
  use_fake_hardware:=false
```

#### Step 2：启动 Pico Bridge

```bash
ros2 run openarmx_teleop_bridge_vr openarmx_teleop_bridge_vr_node
```

#### Step 3：启动双臂 VR 控制

```bash
ros2 launch openarmx_teleop_vr teleop_vr.launch.py controller_pose_mode:=hand
```

#### Step 4：启动 HIGVR 双手套

```bash
ros2 launch openarmx_hands_hig higvr_both.launch.py
```

#### Step 5：启动 HIGVR 到 O6 转换

```bash
ros2 launch openarmx_hands_bridge higvr_to_o6.launch.py hand:=both
```

相机仍按本章 Step 4 单独启动。随后使用 O6 插件录制：

```bash
HF_HUB_OFFLINE=1 lerobot-record \
  --robot.type=openarmx_follower_o6_ros2 \
  --teleop.type=openarmx_leader_o6_ros2 \
  --dataset.repo_id=local/o6_task \
  --dataset.single_task="你的任务名称" \
  --dataset.num_episodes=70 \
  --dataset.push_to_hub=false \
  --display_data=true
```

推理时只启动双臂/O6 底层和相机，不启动 VR、HIGVR 及转换节点，避免多个节点同时发布控制命令。然后使用 `--robot.type=openarmx_follower_o6_ros2`、
`--robot.skip_send_action=false` 和对应的 26 维 O6 模型执行推理。普通夹爪的16维模型不能直接用于 O6。

---

## 🧠 4. ACT 训练流程（用户高性能电脑/服务器）

### 📌 4.1 训练前说明

ACT 训练建议在用户自备的高性能电脑或服务器上进行（推荐使用独立 GPU）。
在开始训练前，请先在本机完成 LeRobot 环境安装，并下载对应模型。本文以 ACT 为例，更多环境配置与各类模型训练教程请参考官网文档：<http://docs.openarmx.com/>。

### 📥 4.2 ACT 依赖模型下载

在 LeRobot 环境终端执行：

```bash
mkdir -p ~/.cache/torch/hub/checkpoints
# 进入 LeRobot 环境安装依赖
lerobot-env
wget https://mirrors.tuna.tsinghua.edu.cn/pytorch/models/resnet18-f37072fd.pth \
  -O ~/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth
```

### 🏋️ 4.3 ACT 训练命令

#### 4.3.1 单卡训练（可选）

```bash
lerobot-env
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
lerobot-train \
  --dataset.repo_id=local/你的数据名称 \
  --dataset.root=你的数据绝对路径 \
  --policy.type=act \
  --policy.push_to_hub=false \
  --output_dir=outputs/训练好的模型名字 \
  --batch_size=每个训练步的批次大小 \
  --steps=总训练步数 \
  --log_freq=每隔多少步输出一次日志 \
  --save_freq=每隔多少步保存一次
```

#### 4.3.2 多卡训练（可选）

```bash
lerobot-env
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
torchrun --nproc_per_node=你的显卡数量 \
  "$(which lerobot-train)" \
  --dataset.repo_id=local/你的数据名称 \
  --dataset.root=你的数据绝对路径 \
  --policy.type=act \
  --policy.push_to_hub=false \
  --output_dir=outputs/训练好的模型名字 \
  --batch_size=每个训练步的批次大小 \
  --steps=总训练步数 \
  --log_freq=每隔多少步输出一次日志 \
  --save_freq=每隔多少步保存一次
```

训练完成后，请记录 `output_dir` 中导出的 `pretrained_model` 路径，供第 5 节推理使用。

---

## 🤖 5. VLA 推理流程（工控机 + 推理机）

本节以 ACT 为例，介绍如何加载已训练模型进行在线推理。
当前流程中，**需要工控机与用户机器进行双机通信**，请在推理前先完成第 6 节 `ROS_DOMAIN_ID` 配置。

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 推理前未完成双机通信配置，基本无法正常联动。</b></span>

### ✅ 5.1 推理前置条件

- 已完成训练，并拿到模型路径（通常指向 `pretrained_model` 目录）。
- 工控机可正常启动机器人与相机。
- 推理一般在另一台用户的电脑执行，因此需要双机通信；请先完成第 6 节 `ROS_DOMAIN_ID` 配置。

### 🚦 5.2 启动顺序

#### Step 1：启动机器人真机（工控机）

```bash
cd ~/openarmx_ws
source install/setup.bash
ros2 launch openarmx_bringup openarmx.bimanual.launch.py \
  control_mode:=mit \
  robot_controller:=forward_position_controller \
  use_fake_hardware:=false
```

#### Step 2：启动三相机发布（工控机）

请按第 7 节《相机参数配置参考》修改 `W/H/FPS` 与三台相机的 `serial/type`。

```bash
cd ~/openarmx_ws
source install/setup.bash
W=424; H=240; FPS=30
ros2 launch openarmx_lerobot camera_publisher.launch.py \
  width:=$W height:=$H fps:=$FPS \
  cam_left_serial:=218622270388 cam_left_type:=D405 \
  cam_right_serial:=218622274446 cam_right_type:=D405 \
  cam_head_serial:=335522070220 cam_head_type:=D435
```

若需要在推理前固定三台相机曝光，也可以直接使用与第 3 节相同的三相机曝光示例，在上述命令后追加：

- 左手：`cam_left_color_auto_exposure:=false cam_left_color_exposure:=400 cam_left_color_gain:=32`
- 右手：`cam_right_color_auto_exposure:=false cam_right_color_exposure:=400 cam_right_color_gain:=32`
- 头部：`cam_head_color_auto_exposure:=false cam_head_color_exposure:=300 cam_head_color_gain:=16`

#### Step 3：执行推理（推理机）

- 推理命令中的 `W/H/FPS` 必须与当前相机发布节点的 `width/height/fps` 完全一致。
- 推理时相机格式（分辨率/帧率）应与数据采集时保持一致（建议与训练该模型所用数据格式一致）。

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 关键约束：`推理 W/H/FPS` = `采集 W/H/FPS` = `相机发布 width/height/fps`。</b></span>

```bash
lerobot-env
W=424; H=240; FPS=30
HF_HUB_OFFLINE=1 lerobot-record \
  --robot.type=openarmx_follower_ros2 \
  --robot.cameras="{cam_left: {type: ros2, image_topic: /cam_left/color/image, depth_topic: /cam_left/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_right: {type: ros2, image_topic: /cam_right/color/image, depth_topic: /cam_right/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_head: {type: ros2, image_topic: /cam_head/color/image, depth_topic: /cam_head/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}}" \
  --robot.skip_send_action=false \
  --dataset.repo_id="local/推理完成模型名称" \
  --dataset.single_task="你的任务名称" \
  --dataset.num_episodes=推理次数 \
  --dataset.push_to_hub=false \
  --display_data=true \
  --policy.path="你训练好的模型路径"
```

示例：

```bash
lerobot-env
W=424; H=240; FPS=30
HF_HUB_OFFLINE=1 lerobot-record \
  --robot.type=openarmx_follower_ros2 \
  --robot.cameras="{cam_left: {type: ros2, image_topic: /cam_left/color/image, depth_topic: /cam_left/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_right: {type: ros2, image_topic: /cam_right/color/image, depth_topic: /cam_right/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_head: {type: ros2, image_topic: /cam_head/color/image, depth_topic: /cam_head/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}}" \
  --robot.skip_send_action=false \
  --dataset.repo_id=local/eval_take_box \
  --dataset.single_task="take the box" \
  --dataset.num_episodes=10 \
  --dataset.push_to_hub=false \
  --display_data=true \
  --policy.path="/home/i4090/openarmx_vla/src/VLA/OUTPUTS/045000/pretrained_model"
```

### 🧾 5.3 推理命令参数说明

- `HF_HUB_OFFLINE=1`：离线模式，不联网拉取资源。
- `--robot.type=openarmx_follower_ros2`：推理动作下发目标机器人类型。
- `--robot.skip_send_action=false`：`false` 表示真实下发动作；`true` 表示仅验证流程不动机器人。
- `--dataset.repo_id="local/推理完成模型名称"`：推理结果保存标识。
- `--dataset.single_task="你的任务名称"`：推理任务名（元信息）。
- `--dataset.num_episodes=推理次数`：推理回合数。
- `--dataset.push_to_hub=false`：不上传到 Hugging Face Hub。
- `--display_data=true`：显示推理过程数据。
- `--policy.path="你训练好的模型路径"`：本地模型路径。

---

## 🌐 6. 两机协同时的 ROS_DOMAIN_ID 配置

当工控机与用户机器需要跨机通信时，两台机器的 `ROS_DOMAIN_ID` 必须一致（建议统一为同一值，如 `77`）。

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 两台机器 `ROS_DOMAIN_ID` 不一致时，跨机话题发现会失败。</b></span>

### 6.1 检查当前配置

在两台机器分别执行：

```bash
echo $ROS_DOMAIN_ID
```

### 6.2 统一配置为同一值（如 77，若不一致）

在两台机器都执行（先将 `DOMAIN_ID` 设置为双方统一值，示例为 `77`）：

```bash
DOMAIN_ID=77
grep -q '^export ROS_DOMAIN_ID=' ~/.bashrc \
  && sed -i "s/^export ROS_DOMAIN_ID=.*/export ROS_DOMAIN_ID=${DOMAIN_ID}/" ~/.bashrc \
  || echo "export ROS_DOMAIN_ID=${DOMAIN_ID}" >> ~/.bashrc
source ~/.bashrc
```

### 6.3 再次验证

```bash
echo $ROS_DOMAIN_ID
```

两台机器输出一致即可。

---

## 📷 7. 相机参数配置参考

### 🛠️ 7.1 命令中哪些参数需要改

使用 `camera_publisher.launch.py` 时，通常只需要修改以下参数：

- `W` / `H` / `FPS`：分辨率与帧率。
- `cam_left_serial` / `cam_right_serial` / `cam_head_serial`：三台相机序列号。
- `cam_left_type` / `cam_right_type` / `cam_head_type`：三台相机型号（`D405` 或 `D435`）。
- 下面参数名中的 `*` 不是字面量，而是占位符，需要替换成具体相机前缀：
  - 左手相机用 `cam_left`
  - 右手相机用 `cam_right`
  - 头部相机用 `cam_head`
- 例如：`cam_*_color_exposure` 实际要写成 `cam_left_color_exposure`、`cam_right_color_exposure` 或 `cam_head_color_exposure`。
- `cam_*_color_auto_exposure`：颜色自动曝光，取值 `true/false/unset`。
- `cam_*_color_exposure`：颜色手动曝光，范围 `1..10000`。
- `cam_*_color_gain`：颜色手动增益，范围 `0..128`。
- `cam_*_color_auto_white_balance`：颜色自动白平衡，取值 `true/false/unset`。
- `cam_*_color_white_balance`：颜色手动白平衡，范围 `2800..6500`。
- `cam_*_color_brightness`：亮度，范围 `-64..64`。
- `cam_*_color_contrast`：对比度，范围 `0..100`。
- `cam_*_color_saturation`：饱和度，范围 `0..100`。
- `cam_*_color_sharpness`：锐度，范围 `0..100`。

在 `lerobot-record`（采集与推理）命令中也需要设置同一组 `W/H/FPS`，并保持一致性：

- `lerobot-record` 的 `W/H/FPS` = `camera_publisher.launch.py` 的 `width/height/fps`。
- 推理 `W/H/FPS` = 数据采集 `W/H/FPS`（建议与训练该模型使用的数据一致）。

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 这里的一致性是全流程稳定的核心约束。</b></span>

序列号查询命令：

```bash
rs-enumerate-devices | grep "Serial Number"
```

### 📐 7.2 可用分辨率/帧率组合（D405 / D435）

`camera_publisher.launch.py` 已内置校验，必须使用以下有效组合：

### Intel RealSense D405

| 分辨率 | 支持的帧率 |
|--------|-----------|
| 1280 x 720 | 5, 15, 30 |
| 848 x 480 | 5, 15, 30, 60, 90 |
| 640 x 480 | 5, 15, 30, 60, 90 |
| 640 x 360 | 5, 15, 30, 60, 90 |
| 480 x 270 | 5, 15, 30, 60, 90 |
| 424 x 240 | 5, 15, 30, 60, 90 |

### Intel RealSense D435 / D435i

| 分辨率 | 支持的帧率 |
|--------|-----------|
| 1920 x 1080 | 6, 15, 30 |
| 1280 x 720 | 6, 15, 30 |
| 848 x 480 | 6, 15, 30, 60, 90 |
| 640 x 480 | 6, 15, 30, 60, 90 |
| 640 x 360 | 6, 15, 30, 60, 90 |
| 480 x 270 | 6, 15, 30, 60, 90 |
| 424 x 240 | 6, 15, 30, 60, 90 |

### 💡 7.3 三相机带宽上限与推荐配置

- 标配工控机 + 标配拓展坞下，三相机稳定上限：`640x480 @ 30fps`。
- 默认推荐配置：`424x240 @ 30fps`（带宽占用更低，更稳）。
- 若追求更高画质，请优先降低帧率或减少并发相机数量。
