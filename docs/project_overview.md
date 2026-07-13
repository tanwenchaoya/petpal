# PetPal 当前能力与后续规划

## 项目定位

PetPal 是一个基于具身智能的家庭宠物陪护机器人项目。当前版本的目标不是直接做完整消费级产品，而是先构建一个稳定、可演示、可持续扩展的比赛原型：

- LLM 作为任务理解与工具编排层
- 摄像头作为环境感知入口
- RoboCrew / XLeRobot 作为机器人运动与硬件控制底座
- PetPal 仓库承载比赛业务逻辑，避免继续修改官方 LeRobot 或依赖库源码

当前设计原则是：**大模型负责决策，不直接逐帧控制电机；具体动作由确定性的工具函数执行。**

## 当前已具备的能力

### 1. 独立项目结构

PetPal 已经从官方 LeRobot 项目中拆分为独立仓库：

```text
petpal/
  src/petpal/
  examples/
  docs/
  README.md
  pyproject.toml
```

这样后续比赛业务能力可以集中维护在 `src/petpal/`，官方 LeRobot 和 RoboCrew 只作为底层依赖或参考。

### 2. LLM Agent 基础闭环

当前 `src/petpal/agent.py` 已实现 PetPal 专用 Agent：

- 接收文字任务
- 拍摄主摄像头画面
- 将任务和图像发送给多模态 LLM
- 接收 LLM tool call
- 调用机器人动作工具
- 保存有限长度的多轮上下文
- 在 `finish_task` 被调用时结束当前任务

这已经形成了最小的“看见环境 -> 理解任务 -> 调用工具 -> 执行动作”的闭环。

### 3. 拍照与状态报告

当前已经新增两个不依赖 YOLO 精度的基础工具：

```text
capture_pet_photo
save_pet_status
```

`capture_pet_photo` 负责从头部摄像头抓取一帧并保存到 `outputs/captures/`。`save_pet_status`
负责把 VLM 基于当前画面的观察结果保存成 JSON 和 Markdown，输出到 `outputs/reports/`。

这条链路可以先支撑“拍张照片发给我”和“看看猫现在状态怎么样”的远程看护演示。

### 4. 模型与运行配置集中管理

当前配置集中在 `src/petpal/config.py`：

- LLM 模型名
- LLM provider
- OpenAI compatible base URL
- API key 环境变量名
- 摄像头索引
- 左右机械臂/底盘串口
- 语音唤醒词
- ASR 模型名
- 麦克风索引

默认 LLM：

```text
qwen3.5-plus-2026-02-15
```

默认 ASR：

```text
qwen3-asr-flash
```

### 5. 语音输入能力

当前 `src/petpal/voice.py` 已经内置本项目自己的语音监听与 ASR 逻辑，不再依赖修改 RoboCrew 的 `sound_receiver.py`。

语音流程：

```text
麦克风监听 -> RMS 音量检测 -> 自动录音 -> 静音后停止 -> 百炼 ASR -> 唤醒词过滤 -> 放入任务队列
```

这意味着后续要调整语音模型、唤醒词、录音阈值、语言参数，都可以在 PetPal 项目内完成。

### 6. 基础机器人动作工具

当前 `src/petpal/tools.py` 已接入 RoboCrew 的基础 XLeRobot 工具：

- `move_forward`
- `turn_left`
- `turn_right`
- `finish_task`

这些工具可以支撑基本移动演示，例如：

```text
往前走一点
左转看看
靠近目标
完成任务
```

### 7. 独立启动入口

当前入口：

```bash
python examples/petpal_agent.py --camera 2
```

语音模式：

```bash
python examples/petpal_agent.py --voice --camera 2 --model qwen3.5-plus-2026-02-15
```

模拟模式：

```bash
python examples/petpal_agent.py --simulate
```

模拟模式只验证 LLM 连接，不连接真实机器人硬件。

## 当前边界

当前版本仍然是 PetPal 的基础框架，不是完整宠物陪护系统。以下能力尚未完成：

- YOLO 找猫工具已接入基础版，但现场识别稳定性还需要继续调参和补数据
- VLM 宠物状态报告和基础日报聚合已具备最小落盘能力
- 逗猫脚本/录制轨迹回放已具备基础工具，真实互动动作仍需要现场录制和调参
- 尚未实现宠物日报
- 尚未实现 Web / 手机端控制台
- 尚未实现完整自主导航、避障、地图和定位
- 尚未接入 ACT 模仿学习策略

这些边界需要在比赛展示时明确表述，避免把规划能力误说成已完成能力。

## 推荐演示目标

比赛 MVP 建议收敛为以下闭环：

```text
主人输入或语音下发任务
        ↓
PetPal LLM Agent 理解任务
        ↓
调用 find_cat 找猫
        ↓
调用 approach_cat_tool 靠近
        ↓
调用 capture_pet_photo / save_pet_status 生成状态报告
        ↓
主人下发“逗逗猫”
        ↓
调用 play_with_cat 执行激光互动脚本
        ↓
调用 generate_pet_daily_report 生成日报
```

其中 LLM 只负责任务编排，找猫、靠近、逗猫都由确定性工具执行。

当前也提供了一个确定性演示脚本，避免比赛现场完全依赖 LLM 自由规划：

```bash
PYTHONPATH=src python examples/petpal_demo.py --run-approach --run-play
```

该脚本会执行：拍照、一次小步靠近决策、状态报告、平滑逗猫轨迹、日报生成。

如果需要让靠近阶段形成短闭环，可以增加步数：

```bash
PYTHONPATH=src python examples/petpal_demo.py --run-approach --run-play --approach-steps 3 --forward-meters 0.02
```

## 后续开发规划

### 阶段 1：视觉找猫

目标：让机器人能在摄像头画面中识别猫，并返回检测结果。

当前状态：基础版已完成，现场识别稳定性仍需要继续调参。

已新增：

```text
src/petpal/vision.py
```

核心能力：

- 使用 YOLO 检测 `cat`
- 如果 YOLO 将猫误识别为 `dog`，会作为 `cat_candidate` fallback 返回，并保留 `model_label`
- 返回猫的 bounding box、中心点、置信度
- 返回检测框面积占比，供后续粗略距离判断使用
- 全图未检出时，会对画面分块放大后再次检测
- 保存关键帧截图

新增工具：

```text
find_cat
```

当前 `find_cat` 会从头部摄像头抓取一帧图像，使用 YOLO 检测 `cat`，返回检测框、置信度、中心点、面积比例，并将原图和带框结果图保存到：

```text
outputs/captures/
```

### 阶段 2：视觉伺服靠近猫

目标：让机器人根据猫在画面中的位置，执行低速、短步、可停止的靠近动作。

当前状态：基础版已完成，默认 dry-run，不会直接移动真实机器人。

新增工具：

```text
approach_cat_tool
```

策略：

- 猫在画面左侧：小角度左转
- 猫在画面右侧：小角度右转
- 猫在画面中央且距离较远：低速前进
- 猫消失：停止并重新扫描
- 靠近超时或距离足够近：停止
- 默认 `dry_run=true`，只返回计划动作；真实执行时需要显式设置 `dry_run=false`

命令行测试：

```bash
PYTHONPATH=src python examples/petpal_approach.py --camera 2
PYTHONPATH=src python examples/petpal_approach.py --camera 2 --run
```

注意：这个阶段不做完整 SLAM，只做比赛场景内的受控视觉靠近。

### 阶段 3：宠物状态识别

目标：找到猫后生成可读的状态报告。

新增模块：

```text
src/petpal/reports.py
```

新增工具：

```text
capture_pet_photo
save_pet_status
```

报告内容：

- 当前是否看到猫
- 猫的位置描述
- 行为状态：休息、走动、玩耍、进食、未知
- 情绪倾向：平静、活跃、疑似紧张、无法判断
- 是否需要主人关注

表达原则：

- 使用“疑似”“看起来”“从画面判断”等措辞
- 不做医学诊断
- 不声称能准确识别宠物情绪

### 阶段 3.5：宠物日报

目标：把当天多次状态报告汇总成一份可展示的日报。

新增工具：

```text
generate_pet_daily_report
```

当前日报会读取 `outputs/reports/` 下当天的状态报告，统计报告次数、情绪计数、最近一次状态和建议，并保存 JSON/Markdown 文件。

### 阶段 4：脚本/录制轨迹逗猫

目标：不接 ACT 的情况下，先实现稳定可演示的互动动作。

新增模块：

```text
src/petpal/trajectories.py
```

新增工具：

```text
record_petpal_pose
play_with_cat
```

当前实现方式：

- 先用 `record_petpal_pose` 录制几个右臂姿态，例如 `petpal_tease_left`、`petpal_tease_center`、`petpal_tease_right`
- 再用 `play_with_cat` 按顺序回放这些姿态
- 回放会对关键姿态之间做插值，避免机械臂直接跳变
- 当前默认基准参数为 `interpolation_steps=28`、`step_seconds=0.03`、`dwell_seconds=0.1`
- 默认 `dry_run=true`，只返回计划步骤，不会让真实机器人动
- 只有在主人明确要求并确认周围安全后，才把 `dry_run` 设为 `false`

命令行录制流程：

```bash
PYTHONPATH=src python examples/petpal_trajectory.py release --arm-side right
PYTHONPATH=src python examples/petpal_trajectory.py record --position-name petpal_tease_left --arm-side right
PYTHONPATH=src python examples/petpal_trajectory.py record --position-name petpal_tease_center --arm-side right
PYTHONPATH=src python examples/petpal_trajectory.py record --position-name petpal_tease_right --arm-side right
PYTHONPATH=src python examples/petpal_trajectory.py play --arm-side right
PYTHONPATH=src python examples/petpal_trajectory.py play --arm-side right --run
```

优先支持两种方式：

1. 手写轨迹
   - 左右扫动
   - 停顿后突然移动
   - 小范围画圈
   - 折线移动

2. 录制轨迹回放
   - 手柄或键盘遥操作机械臂
   - 保存关节目标序列
   - 运行时按时间戳回放

安全限制：

- 单次互动最长 30 秒
- 检测不到猫时停止
- 猫疑似焦躁时停止
- 机械臂动作限制在安全角度范围内

### 阶段 5：宠物日报

目标：把巡逻和互动记录汇总成可展示结果。

新增能力：

- 记录每次找猫时间
- 记录检测到猫的位置或巡逻点
- 保存关键截图
- 汇总行为状态
- 生成一段中文日报

新增工具：

```text
generate_daily_report
```

日报示例：

```text
今天共检测到猫 4 次，主要出现在沙发区和猫窝附近。
上午状态以休息为主，下午有一次主动玩耍。
未观察到明显异常行为。
```

### 阶段 6：Web / 手机端控制台

目标：让主人可以通过手机浏览器远程查看和控制。

推荐技术路线：

- FastAPI 后端
- 浏览器页面作为手机端 UI
- 视频流或定时截图
- 文本指令输入框
- 状态报告展示区
- 日报展示区

页面能力：

- 实时/准实时查看摄像头
- 输入“去看看猫”
- 输入“逗逗猫”
- 查看最近一次分析报告
- 查看今日日报

### 阶段 7：ACT 模仿学习升级

目标：将脚本/录制轨迹升级为学习到的动作策略。

前置条件：

- 已有稳定的 `play_with_cat` 工具接口
- 已有多段遥操作逗猫数据
- 已定义动作输入输出格式
- 已确定摄像头和关节状态特征

升级方式：

- 保持 `play_with_cat` 这个工具名不变
- 内部从脚本轨迹切换为 ACT policy 推理
- 这样 LLM 层无需重写，只替换执行层

## 代码维护原则

1. PetPal 业务逻辑优先放在 `src/petpal/`
2. 不直接修改 `site-packages` 里的 RoboCrew 文件
3. LLM 只调用工具，不直接输出底层电机控制
4. 所有真实运动工具必须有超时、停止和安全边界
5. 比赛演示优先稳定性，不优先追求复杂自主导航
6. 已完成能力和规划能力要在文档和演示中分开表述

## 下一步优先级

建议按这个顺序推进：

1. 实现 `find_cat`
2. 实现 `approach_cat`
3. 实现 `analyze_cat_state`
4. 实现 `play_with_cat` 的脚本版
5. 接入基础日报
6. 做手机 Web 控制台
7. 再考虑 ACT 策略替换

这个顺序可以最快形成可演示闭环，同时避免一开始被 ACT、SLAM、App 开发等高风险任务拖慢。
