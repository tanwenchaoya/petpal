# PetPal Technical Roadmap

## 目标

这份文档用于指导 PetPal 后续开发，避免在 LLM、视觉、运动控制、报告生成之间反复返工。

当前核心原则：

```text
LLM 是任务大脑，不是电机控制器。
YOLO / VLM 是感知层。
确定性策略负责安全动作闭环。
```

## 当前基础能力

已完成并实测过的能力：

- 头部摄像头默认使用 `camera 2`
- YOLO 找猫基础版，支持分块放大检测
- YOLO 将猫误识别为 `dog` 时，返回 `cat_candidate`
- 视觉靠近基础闭环，支持最多 10 步小动作
- 当前演示参数：`center_tolerance=0.25`、`forward_meters=0.02`
- 右臂录制轨迹逗猫，默认平滑插值参数为 `28 / 0.03 / 0.1`
- 状态报告和日报落盘
- 确定性完整演示脚本：`examples/petpal_demo.py`

## 分层架构

### 1. LLM 任务层

职责：

- 理解主人指令
- 决定调用哪个高级技能
- 根据工具结果决定是否继续、停止、重试或换策略
- 生成给主人看的状态解释

不做：

- 不逐帧控制电机
- 不直接输出连续角度或速度
- 不绕过安全策略直接移动

推荐输出形式：

```json
{
  "task": "approach_pet",
  "mode": "gentle",
  "reason": "The owner asked to check on the cat.",
  "safety": {
    "max_total_forward_meters": 0.2,
    "allow_cat_candidate": true
  }
}
```

### 2. VLM 粗感知层

职责：

- 在 YOLO 漏检时，从整张画面做语义判断
- 判断宠物大致方位：左、中、右、近处、远处、不在画面
- 判断是否适合靠近：睡觉、躲避、被遮挡、环境复杂

推荐工具：

```text
vlm_locate_pet
```

结构化结果：

```json
{
  "pet_visible": true,
  "pet_region": "right",
  "confidence": "medium",
  "recommended_action": "turn_right_small",
  "reason": "A white cat appears near the lower-right floor area."
}
```

### 3. YOLO 精确检测层

职责：

- 返回检测框、中心点、面积占比、置信度
- 支持 `cat` 和 `cat_candidate`
- 保存原图和标注图
- 为靠近策略提供几何输入

接口应保持：

```json
{
  "found": true,
  "best_detection": {
    "label": "cat",
    "model_label": "cat",
    "confidence": 0.66,
    "center_xy": [1151.0, 771.4],
    "area_ratio": 0.0082
  },
  "image_size": {
    "width": 1920,
    "height": 1080
  }
}
```

### 4. 确定性控制层

职责：

- 根据检测框决定小动作
- 限制最大步数、最大总距离、最大转角
- 丢失宠物时停止
- 置信度不足时停止或请求 VLM 辅助

不做：

- 不理解自然语言
- 不生成报告
- 不直接接收开放式 LLM 指令

## 下一阶段优先能力

### A. 安全停止条件

当前问题：

靠近主要依赖 `max_steps`，这只是粗限制。

需要新增：

- `max_total_forward_meters`
- `max_total_turn_degrees`
- `target_area_ratio`
- `min_confidence`
- `max_lost_frames`
- `stop_if_pet_too_close`

建议默认：

```text
max_total_forward_meters = 0.20
max_total_turn_degrees = 30
target_area_ratio = 0.018
min_confidence = 0.20
max_lost_frames = 1
```

预期结果：

```json
{
  "finished": true,
  "stop_reason": "max_total_forward_reached",
  "total_forward_meters": 0.2,
  "total_turn_degrees": 0
}
```

### B. 靠近会话工具

当前 `approach_cat_tool` 更像单次/短循环控制。后续需要高级工具：

```text
approach_cat_session
```

输入：

```json
{
  "mode": "gentle",
  "max_steps": 10,
  "max_total_forward_meters": 0.2,
  "center_tolerance": 0.25,
  "target_area_ratio": 0.018,
  "allow_vlm_assist": true
}
```

输出：

```json
{
  "found": true,
  "finished": true,
  "stop_reason": "target_area_reached",
  "steps": [],
  "total_forward_meters": 0.12,
  "total_turn_degrees": 9
}
```

LLM 只调用这个高级工具，不参与内部每一步电机控制。

### C. VLM 辅助找猫

目标：

当 YOLO 找不到猫时，由 VLM 做一次粗判断，再执行一个小的重定位动作。

流程：

```text
YOLO find_cat
    ↓ not found
VLM locate_pet
    ↓ region = right
turn_right_small
    ↓
YOLO find_cat again
```

第一版只允许离散动作：

```text
turn_left_small
turn_right_small
look_down
observe_only
```

禁止 VLM 输出任意角度或距离。

### D. 巡逻与扫描

第一版不做 SLAM。

建议先做：

- 原地左中右扫描
- 每个角度拍照并 YOLO
- 找到猫后进入 `approach_cat_session`
- 找不到猫则生成“未发现宠物”报告

工具：

```text
scan_for_pet
```

后续再扩展到预设路线：

```text
living_room_route = [
  "turn_left_small",
  "capture",
  "turn_right_small",
  "capture"
]
```

### E. 逗猫反馈闭环

当前逗猫是固定轨迹。

下一步需要：

- 播放前确认宠物仍在画面内
- 每轮轨迹后重新检测
- 如果宠物离开，停止
- 如果宠物仍在且主人允许，再重复一轮

工具升级：

```text
play_with_cat_session
```

默认限制：

```text
max_rounds = 2
max_duration_seconds = 30
require_pet_visible = true
```

### F. 状态识别升级

当前报告主要基于规则和工具结果。

下一步引入 VLM：

```text
analyze_pet_state
```

输出：

```json
{
  "visible": true,
  "behavior": "resting",
  "mood": "calm",
  "risk": "low",
  "owner_message": "猫正趴在右侧地面附近，看起来比较平静。"
}
```

约束：

- 不做医学诊断
- 使用“看起来”“疑似”“从画面判断”
- 保存原图、分析 JSON、Markdown 报告

## LLM 接入位置

短期只接三个点：

1. **任务编排**

用户说“去看看猫”，LLM 调：

```text
scan_for_pet -> approach_cat_session -> analyze_pet_state -> save_pet_status
```

2. **YOLO 失败后的 VLM 粗判断**

YOLO 没找到猫时，LLM/VLM 只输出方位和离散建议。

3. **阶段切换**

靠近结束后，LLM 判断：

```text
生成报告 / 开始逗猫 / 停止 / 再扫描
```

暂时不要接：

- 每帧运动控制
- 任意角度/距离生成
- 没有安全限制的连续移动

## 推荐开发顺序

### 第 1 步：增强靠近安全

修改：

```text
src/petpal/navigation.py
```

新增字段：

- `total_forward_meters`
- `total_turn_degrees`
- `stop_reason`
- `target_area_ratio` 生效停止
- `max_total_forward_meters`

### 第 2 步：新增 approach_cat_session

保留现有 `approach_cat`，新增更高级的 session 函数和工具。

目标是让 LLM 调高级工具，而不是调底层动作。

### 第 3 步：新增 vlm_locate_pet

先只做图片输入和 JSON 输出，不移动。

### 第 4 步：新增 find_cat_with_vlm_assist

YOLO 找不到时调用 VLM，执行一个离散小动作，再 YOLO。

### 第 5 步：新增 scan_for_pet

原地扫描，不做路线巡逻。

### 第 6 步：升级 play_with_cat_session

逗猫前后检查宠物是否仍在视野中。

## 不建议现在做的事

- Web / 手机端控制台
- 完整地图和 SLAM
- ACT 模仿学习
- 自定义模型训练大工程
- 多房间巡逻

这些能力可以写入比赛愿景，但不应该阻塞当前 MVP。

## 当前建议

下一次实现应从安全控制开始：

```text
max_total_forward_meters
target_area_ratio stop
stop_reason
approach_cat_session
```

这样 LLM 接入后，才能放心把“靠近猫”作为高级技能交给它调用。
