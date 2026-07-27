# OpenArmX VLA User Guide (LeRobot)

This document explains how to use the OpenArmX robot with the LeRobot framework for VLA data collection, ACT training, and inference.

<span style="background:#E8F5E9;padding:2px 8px;border-radius:6px;"><b>✅ Success Tips</b></span>
<span style="background:#FFF8E1;padding:2px 8px;border-radius:6px;"><b>⚠️ Notes</b></span>
<span style="background:#FFEBEE;padding:2px 8px;border-radius:6px;"><b>🚨 High-Risk Items</b></span>
<span style="background:#E3F2FD;padding:2px 8px;border-radius:6px;"><b>💡 Practical Advice</b></span>

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 The 3 most important things in this document:</b></span>  
> <b>1)</b> The startup order must be followed strictly step by step.  
> <b>2)</b> `W/H/FPS` must be exactly the same across camera publishing, collection, and inference.  
> <b>3)</b> Before collection, update dataset parameters in `config/vla_collect.env`.

## Table of Contents

1. Device Roles
2. General Prerequisites
3. VLA Data Collection Workflow (IPC)
   - 3.1 Manual Startup Order (must follow order)
   - 3.2 GUI One-Click Startup (recommended)
   - 3.3 Quick Topic Check (optional)
   - 3.4 Recording UI Key Guide
   - 3.5 Data Collection Command Parameters
4. ACT Training Workflow (User High-Performance PC/Server)
   - 4.1 Notes Before Training
   - 4.2 Download ACT Dependency Models
   - 4.3 ACT Training Commands
5. VLA Inference Workflow (IPC + Inference Machine)
   - 5.1 Inference Prerequisites
   - 5.2 Startup Order
   - 5.3 Inference Command Parameters
6. ROS_DOMAIN_ID Configuration for Two-Machine Collaboration
   - 6.1 Check Current Configuration
   - 6.2 Set Both Machines to the Same Value (e.g., 77, if inconsistent)
   - 6.3 Verify Again
7. Camera Parameter Configuration Reference
   - 7.1 Which Parameters Need to Be Modified in Commands
   - 7.2 Available Resolution/FPS Combinations (D405 / D435)
   - 7.3 Three-Camera Bandwidth Limit and Recommended Settings

---

## 🧩 1. Device Roles

- **IPC (provided by us)**: Robot CAN control, Pico VR teleoperation, 3-camera publishing, LeRobot data collection.
- **User machine (self-configured)**: Model training and inference (can work together with the IPC).

## ✅ 2. General Prerequisites

- The IPC workspace has been built, and `source ~/openarmx_ws/install/setup.bash` works properly.
- The robot can start normally and can be teleoperated through VR.
- Two-machine communication is required for the inference scenario in Section 5; configure DOMAIN ID according to Section 6.

> <span style="background:#FFF8E1;color:#8A6D3B;padding:2px 6px;border-radius:4px;"><b>⚠️ If Section 2 is not satisfied, the following steps will likely fail.</b></span>

---

## 📦 3. VLA Data Collection Workflow (IPC)

### 🚦 3.1 Manual Startup Order (must follow order)

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 Do not skip steps or start modules in parallel out of order.</b></span>

#### Step 1: Start the Real Robot

```bash
cd ~/openarmx_ws
source install/setup.bash
ros2 launch openarmx_bringup openarmx.bimanual.launch.py \
  control_mode:=mit \
  robot_controller:=forward_position_controller \
  use_fake_hardware:=false
```

#### Step 2: Start Pico Bridge

```bash
cd ~/openarmx_ws
source install/setup.bash
ros2 run openarmx_teleop_bridge_vr_pico openarmx_teleop_bridge_vr_pico_node
```

#### Step 3: Start VR Teleoperation

```bash
cd ~/openarmx_ws
source install/setup.bash
ros2 launch openarmx_teleop_vr_pico teleop_vr_pico.launch.py
```

#### Step 4: Start Three-Camera Publishing

First replace the camera model and serial number in the command with your own device parameters:

- Supported camera models: `D435`, `D405`
- `cam_left_*` / `cam_right_*` / `cam_head_*` correspond to left hand, right hand, and head camera respectively
- Query serial numbers: `rs-enumerate-devices | grep "Serial Number"`

With the standard IPC + standard docking station, the stable upper limit for three cameras is `640x480 @ 30fps`.
For camera parameter selection and available combinations, see Section 7 "Camera Parameter Configuration Reference".

> <span style="background:#E3F2FD;color:#0D47A1;padding:2px 6px;border-radius:4px;"><b>💡 Recommended default: run through the full pipeline with `424x240 @ 30fps` first, then gradually increase resolution.</b></span>

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

You need to modify these parameters based on your actual devices:

- `W` / `H` / `FPS`: unified resolution and frame rate for all three cameras (example: `424x240@30`).
- `cam_left_serial` / `cam_right_serial` / `cam_head_serial`: replace with your three camera serial numbers.
- `cam_left_type` / `cam_right_type` / `cam_head_type`: set to actual camera model `D405` or `D435`.

If you need to tune exposure parameters for all three cameras at startup, you can use the following example:

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

Common adjustable color parameters:

- `cam_*_color_auto_exposure`: color auto exposure, values `true/false/unset`
- `cam_*_color_exposure`: color manual exposure, range `1..10000`
- `cam_*_color_gain`: color manual gain, range `0..128`
- `cam_*_color_auto_white_balance`: color auto white balance, values `true/false/unset`
- `cam_*_color_white_balance`: color manual white balance, range `2800..6500`
- `cam_*_color_brightness`: brightness, range `-64..64`
- `cam_*_color_contrast`: contrast, range `0..100`
- `cam_*_color_saturation`: saturation, range `0..100`
- `cam_*_color_sharpness`: sharpness, range `0..100`

Notes:

- `cam_left_*` / `cam_right_*` / `cam_head_*` apply to left hand, right hand, and head camera respectively
- `unset` means do not force-set this parameter and keep default driver behavior
- If only `cam_*_color_exposure` or `cam_*_color_gain` is specified, launch will automatically add `cam_*_color_auto_exposure:=false`
- If only `cam_*_color_white_balance` is specified, launch will automatically add `cam_*_color_auto_white_balance:=false`

#### Step 5: Start LeRobot Data Collection

Enter the LeRobot environment first, then run the recording command:

- `W/H/FPS` configures camera resolution and frame rate during data collection (for example: `W=640; H=480; FPS=30`).
- Here, `W/H/FPS` must be exactly the same as `width/height/fps` in `camera_publisher.launch.py`.
- After changing W/H/FPS in camera publisher, update W/H/FPS in the collection command accordingly; otherwise format mismatch will cause errors.

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 Key constraint: `Collection W/H/FPS` = `Camera publish width/height/fps`.</b></span>

```bash
lerobot-env
W=424; H=240; FPS=30
HF_HUB_OFFLINE=1 lerobot-record \
  --robot.type=openarmx_follower_ros2 \
  --robot.cameras="{cam_left: {type: ros2, image_topic: /cam_left/color/image, depth_topic: /cam_left/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_right: {type: ros2, image_topic: /cam_right/color/image, depth_topic: /cam_right/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_head: {type: ros2, image_topic: /cam_head/color/image, depth_topic: /cam_head/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}}" \
  --teleop.type=openarmx_leader_ros2 \
  --dataset.repo_id=local/your_dataset_name \
  --dataset.single_task="task_name_you_perform" \
  --dataset.num_episodes=total_number_of_episodes \
  --dataset.episode_time_s=duration_per_episode_seconds \
  --dataset.reset_time_s=interval_after_each_episode \
  --dataset.push_to_hub=false \
  --display_data=true
```

Example:

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

### 🚀 3.2 GUI One-Click Startup (recommended)

If you want to automatically launch multiple terminal windows in a fixed order, like Section 3.1, you can use the one-click startup script in this repository:

- `scripts/vla_collect_gui.sh`: GUI multi-terminal one-click startup script
- ⚠️ `config/vla_collect.env`: one-click startup config file, centrally storing robot/camera/data-collection parameters. <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>Please prioritize parameter changes here</b></span>
- `scripts/README_GUI_EN.md`: standalone guide for one-click startup

Recommended to enter the repository directory first:

```bash
cd /home/openarmx/openarmx_ws/src/openarmx_vla
```

Run a pre-check before startup:

```bash
bash scripts/vla_collect_gui.sh check
```

The pre-check validates:

- Whether `WORKSPACE_DIR/install/setup.bash` exists
- Whether current session is a graphical desktop (`DISPLAY` / `WAYLAND_DISPLAY`)
- Whether terminal command specified by `GUI_TERMINAL` is available (default `gnome-terminal`)
- Whether `ros2` is available
- In `collect` mode, whether `LEROBOT_ENV_CMD` (default `lerobot-env`) is found in interactive shell

Common startup modes:

```bash
# 1. Start only real robot + Pico Bridge + VR Teleop
bash scripts/vla_collect_gui.sh base

# 2. Start robot base stack + camera publishing
bash scripts/vla_collect_gui.sh base_camera

# 3. Start robot base stack + camera publishing + LeRobot data collection
# ⚠️ Note: before each one-click collection run, update DATASET_REPO_ID in config/vla_collect.env
bash scripts/vla_collect_gui.sh collect

# Close all terminals started by this script
bash scripts/vla_collect_gui.sh stop
```

> <span style="background:#FFF8E1;color:#8A6D3B;padding:2px 6px;border-radius:4px;"><b>⚠️ Always check `DATASET_REPO_ID` before `collect` to avoid writing to the wrong dataset directory.</b></span>

Mode mapping:

- `base`: equivalent to manually running "real robot + Pico Bridge + VR teleop"
- `base_camera`: starts three-camera publishing on top of `base`
- `collect`: starts LeRobot data collection on top of `base_camera`
- `stop`: precisely closes windows launched by this script via state file; no error even if some windows were closed manually

Script startup behavior:

- Pops up multiple terminal windows in sequence and starts each module with configured delays
- Each window remains open after command execution for on-site troubleshooting
- If windows from the previous run are still active, it prompts you to run `bash scripts/vla_collect_gui.sh stop` first
- In `collect` mode, it runs `LEROBOT_ENV_CMD` first in recording terminal, then runs `lerobot-record`
- Default config path is `config/vla_collect.env`; you can also temporarily switch with `VLA_CONFIG_FILE=/your_path.env bash scripts/vla_collect_gui.sh collect`

Usually, you only need to modify these items in `config/vla_collect.env`:

- Base path and GUI parameters: workspace path, terminal command, window state file path
- Robot base parameters: `CONTROL_MODE`, `ROBOT_CONTROLLER`, `USE_FAKE_HARDWARE`
- VR teleoperation parameters: Pico/Teleop control rate, grasp threshold, topic names, etc.
- Camera parameters: `W/H/FPS`, three camera serial numbers, camera model, exposure/gain/white balance, etc.
- Data collection parameters: dataset name, task description, episode count, episode duration, reset time, whether to display data, etc.

Special attention:

- `W/H/FPS` is used by both camera publishing and `lerobot-record`; keep it consistent with actual camera output
- `CAM_LEFT_TYPE` / `CAM_RIGHT_TYPE` / `CAM_HEAD_TYPE` must be set to actual devices `D405` or `D435`
- `CAM_LEFT_SERIAL` / `CAM_RIGHT_SERIAL` / `CAM_HEAD_SERIAL` must be replaced with your camera serial numbers
- If using `collect` mode, make sure dataset parameters like `DATASET_REPO_ID` and `DATASET_SINGLE_TASK` are updated to your task

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 The 4 items above are frequent failure points; check them one by one before each collection run.</b></span>

For a more complete one-click startup guide, refer to: `scripts/README_GUI_EN.md`.

### 🔎 3.3 Quick Topic Check (optional)

```bash
ros2 topic list | grep cam
ros2 topic list | grep joint_states
ros2 topic list | grep forward_position_controller/commands
```

Expected at minimum:

- Camera topics: `/cam_left/color/image`, `/cam_right/color/image`, `/cam_head/color/image`
- Joint state: `/joint_states`
- Teleop outputs: `/left_forward_position_controller/commands`, `/right_forward_position_controller/commands`

If the above conditions are met, data collection can proceed.

### ⌨️ 3.4 Recording UI Key Guide

- `→` (Right Arrow): End and save current episode, then enter reset stage.
- `←` (Left Arrow): Discard current episode and re-record.
- `Esc`: Stop recording and exit, then save dataset.

### 🧾 3.5 Data Collection Command Parameters

Common parameters:

- `HF_HUB_OFFLINE=1`: Enable Hugging Face Hub offline mode.
- `--robot.type=openarmx_follower_ros2`: Specify target robot type being controlled.
- `--teleop.type=openarmx_leader_ros2`: Specify teleoperation device type.
- `--dataset.repo_id=local/xxx`: Dataset storage identifier (path under `~/.cache/huggingface/lerobot/local/`).
- `--dataset.single_task`: Task description.
- `--dataset.num_episodes`: Total number of episodes.
- `--dataset.episode_time_s`: Maximum duration per episode (seconds).
- `--dataset.reset_time_s`: Reset wait time between episodes (seconds).
- `--dataset.push_to_hub`: Whether to upload to Hugging Face Hub.
- `--display_data`: Whether to display real-time data.

Other parameters:

- `--dataset.root`: Custom dataset save path.
- `--dataset.fps`: Limit recording frame rate.
- `--dataset.video`: Whether to encode images as video.
- `--dataset.vcodec`: Video codec (default `libsvtav1`).
- `--dataset.video_encoding_batch_size`: Number of episodes per batch video encoding.
- `--dataset.private`: Set private when uploading to Hub.
- `--dataset.tags`: Hub dataset tags.
- `--dataset.num_image_writer_processes`: Number of image writer processes.
- `--dataset.num_image_writer_threads_per_camera`: Number of writer threads per camera.
- `--dataset.rename_map`: Rename observation keys.

### 🖐️ 3.6 Dual O6 Dexterous-Hand Data Collection

The O6 hands use separate LeRobot types and do not change the existing gripper types:

```text
Gripper: openarmx_follower_ros2 + openarmx_leader_ros2 (16 dimensions)
Dual O6: openarmx_follower_o6_ros2 + openarmx_leader_o6_ros2 (26 dimensions)
```

Install both plugins again in the LeRobot environment after the first checkout or an update:

```bash
pip install -e ./lerobot_robot_openarmx_follower_ros2
pip install -e ./lerobot_teleoperator_openarmx_leader_ros2
```

As with the gripper workflow, start the O6 base, VR, and glove nodes separately. VLA does not add a combined launch.

#### Step 1: Start Both Arms and O6 Hands

```bash
ros2 launch openarmx_hand_bringup openarmx.bimanual.o6.launch.py \
  control_mode:=mit \
  robot_controller:=forward_position_controller \
  use_fake_hardware:=false
```

#### Step 2: Start Pico Bridge

```bash
ros2 run openarmx_teleop_bridge_vr openarmx_teleop_bridge_vr_node
```

#### Step 3: Start Arm VR Control

```bash
ros2 launch openarmx_teleop_vr teleop_vr.launch.py controller_pose_mode:=hand
```

#### Step 4: Start Both HIGVR Gloves

```bash
ros2 launch openarmx_hands_hig higvr_both.launch.py
```

#### Step 5: Start HIGVR-to-O6 Conversion

```bash
ros2 launch openarmx_hands_bridge higvr_to_o6.launch.py hand:=both
```

Start the cameras separately as described in Step 4 of this chapter, then record with the O6 plugins:

```bash
HF_HUB_OFFLINE=1 lerobot-record \
  --robot.type=openarmx_follower_o6_ros2 \
  --teleop.type=openarmx_leader_o6_ros2 \
  --dataset.repo_id=local/o6_task \
  --dataset.single_task="your task" \
  --dataset.num_episodes=70 \
  --dataset.push_to_hub=false \
  --display_data=true
```

For policy inference, start only the arm/O6 base and cameras. Do not start VR, HIGVR, or the conversion node, so no other process publishes competing commands. Then run inference with `--robot.type=openarmx_follower_o6_ros2`,
`--robot.skip_send_action=false`, and a matching 26-dimensional O6 policy. Existing
16-dimensional gripper policies are not compatible with O6.

---

## 🧠 4. ACT Training Workflow (User High-Performance PC/Server)

### 📌 4.1 Notes Before Training

ACT training is recommended on a user-provided high-performance PC or server (dedicated GPU recommended).
Before training, complete LeRobot environment installation on this machine and download required model files. This document uses ACT as an example. For more environment setup and model training tutorials, see the official docs: <http://docs.openarmx.com/>.

### 📥 4.2 Download ACT Dependency Models

Run in a LeRobot environment terminal:

```bash
mkdir -p ~/.cache/torch/hub/checkpoints
# Enter LeRobot environment and install dependencies
lerobot-env
wget https://mirrors.tuna.tsinghua.edu.cn/pytorch/models/resnet18-f37072fd.pth \
  -O ~/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth
```

### 🏋️ 4.3 ACT Training Commands

#### 4.3.1 Single-GPU Training (optional)

```bash
lerobot-env
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
lerobot-train \
  --dataset.repo_id=local/your_dataset_name \
  --dataset.root=absolute_path_to_your_dataset \
  --policy.type=act \
  --policy.push_to_hub=false \
  --output_dir=outputs/your_trained_model_name \
  --batch_size=batch_size_per_training_step \
  --steps=total_training_steps \
  --log_freq=log_every_n_steps \
  --save_freq=save_every_n_steps
```

#### 4.3.2 Multi-GPU Training (optional)

```bash
lerobot-env
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
torchrun --nproc_per_node=number_of_your_gpus \
  "$(which lerobot-train)" \
  --dataset.repo_id=local/your_dataset_name \
  --dataset.root=absolute_path_to_your_dataset \
  --policy.type=act \
  --policy.push_to_hub=false \
  --output_dir=outputs/your_trained_model_name \
  --batch_size=batch_size_per_training_step \
  --steps=total_training_steps \
  --log_freq=log_every_n_steps \
  --save_freq=save_every_n_steps
```

After training, record the exported `pretrained_model` path in `output_dir` for inference in Section 5.

---

## 🤖 5. VLA Inference Workflow (IPC + Inference Machine)

Using ACT as an example, this section explains how to load a trained model for online inference.
In the current workflow, **two-machine communication between IPC and user machine is required**. Complete `ROS_DOMAIN_ID` configuration in Section 6 before inference.

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 If two-machine communication is not configured before inference, linkage will almost certainly fail.</b></span>

### ✅ 5.1 Inference Prerequisites

- Training is completed and model path is available (usually the `pretrained_model` directory).
- IPC can start robot and cameras normally.
- Inference is usually run on another user machine, so two-machine communication is required; complete `ROS_DOMAIN_ID` configuration in Section 6 first.

### 🚦 5.2 Startup Order

#### Step 1: Start Real Robot (IPC)

```bash
cd ~/openarmx_ws
source install/setup.bash
ros2 launch openarmx_bringup openarmx.bimanual.launch.py \
  control_mode:=mit \
  robot_controller:=forward_position_controller \
  use_fake_hardware:=false
```

#### Step 2: Start Three-Camera Publishing (IPC)

Modify `W/H/FPS` and the three camera `serial/type` according to Section 7 "Camera Parameter Configuration Reference".

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

If you need fixed exposure for all three cameras before inference, you can append the same three-camera exposure settings used in Section 3:

- Left hand: `cam_left_color_auto_exposure:=false cam_left_color_exposure:=400 cam_left_color_gain:=32`
- Right hand: `cam_right_color_auto_exposure:=false cam_right_color_exposure:=400 cam_right_color_gain:=32`
- Head: `cam_head_color_auto_exposure:=false cam_head_color_exposure:=300 cam_head_color_gain:=16`

#### Step 3: Run Inference (Inference Machine)

- `W/H/FPS` in the inference command must be exactly the same as `width/height/fps` of the current camera publishing node.
- During inference, camera format (resolution/frame rate) should match data collection format (recommended: same format as training data for this model).

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 Key constraint: `Inference W/H/FPS` = `Collection W/H/FPS` = `Camera publish width/height/fps`.</b></span>

```bash
lerobot-env
W=424; H=240; FPS=30
HF_HUB_OFFLINE=1 lerobot-record \
  --robot.type=openarmx_follower_ros2 \
  --robot.cameras="{cam_left: {type: ros2, image_topic: /cam_left/color/image, depth_topic: /cam_left/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_right: {type: ros2, image_topic: /cam_right/color/image, depth_topic: /cam_right/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}, cam_head: {type: ros2, image_topic: /cam_head/color/image, depth_topic: /cam_head/depth/image, use_depth: true, width: $W, height: $H, fps: $FPS}}" \
  --robot.skip_send_action=false \
  --dataset.repo_id="local/inference_result_model_name" \
  --dataset.single_task="your_task_name" \
  --dataset.num_episodes=number_of_inference_runs \
  --dataset.push_to_hub=false \
  --display_data=true \
  --policy.path="path_to_your_trained_model"
```

Example:

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

### 🧾 5.3 Inference Command Parameters

- `HF_HUB_OFFLINE=1`: Offline mode, do not fetch online resources.
- `--robot.type=openarmx_follower_ros2`: Target robot type for inference action publishing.
- `--robot.skip_send_action=false`: `false` means send real actions; `true` means validate pipeline only without moving robot.
- `--dataset.repo_id="local/inference_result_model_name"`: Identifier for inference result storage.
- `--dataset.single_task="your_task_name"`: Inference task name (metadata).
- `--dataset.num_episodes=number_of_inference_runs`: Number of inference episodes.
- `--dataset.push_to_hub=false`: Do not upload to Hugging Face Hub.
- `--display_data=true`: Display inference process data.
- `--policy.path="path_to_your_trained_model"`: Local model path.

---

## 🌐 6. ROS_DOMAIN_ID Configuration for Two-Machine Collaboration

When IPC and user machine need cross-machine communication, `ROS_DOMAIN_ID` must be identical on both machines (recommended: same value, e.g. `77`).

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 If `ROS_DOMAIN_ID` is inconsistent between the two machines, cross-machine topic discovery will fail.</b></span>

### 6.1 Check Current Configuration

Run on both machines separately:

```bash
echo $ROS_DOMAIN_ID
```

### 6.2 Set Both Machines to the Same Value (e.g., 77, if inconsistent)

Run on both machines (set `DOMAIN_ID` to a shared value first, here `77`):

```bash
DOMAIN_ID=77
grep -q '^export ROS_DOMAIN_ID=' ~/.bashrc \
  && sed -i "s/^export ROS_DOMAIN_ID=.*/export ROS_DOMAIN_ID=${DOMAIN_ID}/" ~/.bashrc \
  || echo "export ROS_DOMAIN_ID=${DOMAIN_ID}" >> ~/.bashrc
source ~/.bashrc
```

### 6.3 Verify Again

```bash
echo $ROS_DOMAIN_ID
```

Both machines should print the same value.

---

## 📷 7. Camera Parameter Configuration Reference

### 🛠️ 7.1 Which Parameters Need to Be Modified in Commands

When using `camera_publisher.launch.py`, usually you only need to modify these parameters:

- `W` / `H` / `FPS`: resolution and frame rate.
- `cam_left_serial` / `cam_right_serial` / `cam_head_serial`: serial numbers of the three cameras.
- `cam_left_type` / `cam_right_type` / `cam_head_type`: camera model (`D405` or `D435`) for each camera.
- In the parameter names below, `*` is not a literal character but a placeholder and must be replaced with a specific camera prefix:
  - Use `cam_left` for left hand camera
  - Use `cam_right` for right hand camera
  - Use `cam_head` for head camera
- For example, `cam_*_color_exposure` should actually be `cam_left_color_exposure`, `cam_right_color_exposure`, or `cam_head_color_exposure`.
- `cam_*_color_auto_exposure`: color auto exposure, values `true/false/unset`.
- `cam_*_color_exposure`: color manual exposure, range `1..10000`.
- `cam_*_color_gain`: color manual gain, range `0..128`.
- `cam_*_color_auto_white_balance`: color auto white balance, values `true/false/unset`.
- `cam_*_color_white_balance`: color manual white balance, range `2800..6500`.
- `cam_*_color_brightness`: brightness, range `-64..64`.
- `cam_*_color_contrast`: contrast, range `0..100`.
- `cam_*_color_saturation`: saturation, range `0..100`.
- `cam_*_color_sharpness`: sharpness, range `0..100`.

The same `W/H/FPS` must also be set in `lerobot-record` commands (collection and inference), and must stay consistent:

- `W/H/FPS` in `lerobot-record` = `width/height/fps` in `camera_publisher.launch.py`.
- Inference `W/H/FPS` = Data collection `W/H/FPS` (recommended to match the training data format used by the model).

> <span style="background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;"><b>🚨 Consistency here is the core stability constraint of the entire pipeline.</b></span>

Serial number query command:

```bash
rs-enumerate-devices | grep "Serial Number"
```

### 📐 7.2 Available Resolution/FPS Combinations (D405 / D435)

`camera_publisher.launch.py` has built-in validation; only the following valid combinations can be used:

### Intel RealSense D405

| Resolution | Supported FPS |
|--------|-----------|
| 1280 x 720 | 5, 15, 30 |
| 848 x 480 | 5, 15, 30, 60, 90 |
| 640 x 480 | 5, 15, 30, 60, 90 |
| 640 x 360 | 5, 15, 30, 60, 90 |
| 480 x 270 | 5, 15, 30, 60, 90 |
| 424 x 240 | 5, 15, 30, 60, 90 |

### Intel RealSense D435 / D435i

| Resolution | Supported FPS |
|--------|-----------|
| 1920 x 1080 | 6, 15, 30 |
| 1280 x 720 | 6, 15, 30 |
| 848 x 480 | 6, 15, 30, 60, 90 |
| 640 x 480 | 6, 15, 30, 60, 90 |
| 640 x 360 | 6, 15, 30, 60, 90 |
| 480 x 270 | 6, 15, 30, 60, 90 |
| 424 x 240 | 6, 15, 30, 60, 90 |

### 💡 7.3 Three-Camera Bandwidth Limit and Recommended Settings

- With standard IPC + standard docking station, stable upper limit for three cameras: `640x480 @ 30fps`.
- Default recommended setting: `424x240 @ 30fps` (lower bandwidth usage, more stable).
- If you need higher image quality, prioritize reducing frame rate or reducing the number of concurrent cameras.
