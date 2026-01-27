# ER 数据生成流程 vs `LIBERO-PRO`：差异与“触碰即飞”物理失真原因分析

> 结论先行：你描述的“机械臂刚碰到物体的一瞬间就会飞出去”，在 MuJoCo / robosuite 中最常见的根因不是“物理引擎坏了”，而是**初始状态存在轻微/隐性的穿插（interpenetration）或过近接触**、**被替换物体的碰撞/惯性参数不稳**、以及**生成 init state 与在线评测所用环境/资产/版本不一致**。ER 自动生成相较 `LIBERO-PRO` 更容易触发前两类问题。

---

## 1. 你当前的 ER 侧流程（基于代码实际行为）

你描述的流程在仓库里的对应脚本主要是两部分：

1) **生成/再生成 BDDL（ER suite）**
- `er_extension/regenerate_er_suites.sh`
  - Step 1：对 ER suite（如 `er_object`）调用 `er_extension/scripts/generate_er_object_bddl.py` 等脚本生成 `libero/libero/bddl_files/<suite>/*.bddl`
  - Step 2：`scripts/generate_goal_bddl_files.py`（把 goal 谓词转为“goal-bddl”）
  - Step 3：`scripts/generate_goal_init_files.py`（从 goal-bddl 生成 goal init）
  - Step 4：`scripts/visualize_libero_suites.py`（可视化）

2) **生成 benchmark init 文件（你用于 online evaluation 的 init file）**
- `scripts/generate_benchmark_init_files.py`
  - 对每个任务：`env.seed(seed) -> env.reset() -> dummy step 若干 -> env.get_sim_state()`
  - 默认 `--settle-steps 10`，输出到 `get_libero_path("init_states")/<suite>/<task>.pruned_init`
  - 保存格式：`torch.save(np.ndarray)`（数组形状 `(N, state_dim)`）

### ER 的 BDDL（尤其是 `er_object`）生成方式的关键特征
- **“拼接/置换式生成”**：`generate_er_object_bddl.py` 按注释所述，保留 Source A 的 manipulation（语言/目标/操作物），替换为 Source B 的 scene context（fixtures/regions），可选加入 Source C distractors。
- **区域/位置是“2D footprint + 规则候选点”的启发式分配**：
  - 由 `er_extension/scripts/er_constants.py` 提供对象“脚印”(width/depth)、`COLLISION_MARGIN`、`PLACEMENT_TOLERANCE`、以及一组候选中心点（`OBJECT_PLACEMENT_POSITIONS` / `TARGET_PLACEMENT_POSITIONS`）。
  - `generate_er_object_bddl.py` 的 `allocate_object_region()` 用这些常量做 **AABB 级别的平面碰撞排斥**，并用 `PLACEMENT_TOLERANCE` 给 region 留出随机范围。
  - 这种方法**不检查真实 3D 碰撞几何**、不考虑复杂形状（把手/凸起/凹陷）、也不考虑“目标表面高度/边缘”等细节。

---

## 2. `LIBERO-PRO` 侧流程（你仓库里这一份的实际实现）

`LIBERO-PRO` 这份代码更像是一个“在既有 BDDL 上做 OOD 扰动 + 评估”的工具集，核心差异在两块：

1) **任务生成方式：以“扰动既有 BDDL”为主**
- `LIBERO-PRO/perturbation.py`
  - 通过正则解析与文本替换对 `(:init ...)` 的 `(On obj region)`、`(:language ...)` 等做 swap / replace / language perturbation 等。
  - 这种方式通常**复用原任务的 region 布局**，但会在“换物体/换对象名”时把物体塞进原 region（尺寸/形状不匹配风险更明显，取决于候选集是否严格筛过）。

2) **init-state 文件生成脚本与格式不同**
- `LIBERO-PRO/notebooks/generate_init_states.py`
  - 每个 init：**创建 env 直接读取 `env.get_sim_state()`**，没有显式 `env.reset()`、没有 `seed`、也没有 settle steps。
  - 保存格式：`zipfile + pickle`（写入 `archive/data.pkl` 和 `archive/version`），**不是** `torch.save`。

> 这意味着：如果你把 `LIBERO-PRO` 生成的 `.pruned_init` 拿到当前仓库的 benchmark loader（`libero/libero/benchmark/__init__.py#get_task_init_states`）里用 `torch.load` 读，会直接不兼容；反过来也一样。

---

## 3. 差异对比（与“触碰即飞”相关的部分）

### 3.1 BDDL 层面的差异（最可能影响物理稳定性）

**ER（你在用）**
- 自动生成 region 的中心点/范围，靠 `er_constants.py` 的“估计脚印”与 AABB 排斥。
- 你手动调位置本质上是在调 region ranges 或 init 中引用的 region。
- 仍然存在以下隐患：
  - **脚印估计与真实碰撞几何不一致**：AABB 不重叠 ≠ MuJoCo 碰撞体不接触/不穿插。
  - **随机扰动仍然存在**：`PLACEMENT_TOLERANCE` 会让每次 reset 在 region 内有小扰动；如果你把物体挪得很紧（靠“刚好不交叉”），某些 seed 仍会采样出轻微穿插。
  - **fixture 相关的“边界/高度”问题**：把物体放在靠近柜子/炉子/托盘等复杂几何附近时，2D 检查很容易漏掉与侧壁/把手/凸起的穿插。

**LIBERO-PRO**
- 多数情况下复用原任务 region，不做“为新物体重新分配 region”。
- 如果做了“对象替换/交换”，但 region 不变，**尺寸更大的物体可能被塞进原本只适配小物体的 region**，更容易导致初始穿插。

### 3.2 init-state 生成方式差异（会把“不稳定 reset”固化成文件）

**你当前的 ER init 生成（`scripts/generate_benchmark_init_files.py`）**
- 有 `reset + settle_steps`，比 `LIBERO-PRO/notebooks/generate_init_states.py` 更“稳”。
- 但 settle 默认只有 10 步：如果某个 seed 的 reset 已经有穿插，10 步未必能完全消除（尤其是复杂 mesh、接触刚度大、或与 fixture 边界接触时）。

**LIBERO-PRO 的 init 生成**
- 没有显式 reset/seed/settle：更容易生成“未充分 forward/未稳定”的状态；并且不同 init 可能高度重复。

### 3.3 代码/资产/配置层差异（容易导致“生成用 A，评测用 B”）

在你这个仓库里同时存在两套 `libero` 包：
- 当前仓库：`libero/`（你 ER 脚本默认用这一套）
- `LIBERO-PRO/libero/`（PRO 也带一套）

风险点：
- **Python import 路径混用**：在线评测时如果 `PYTHONPATH` / `pip install -e` / 工作目录导致导入了另一套 `libero`，就可能出现：
  - 读取了另一套 `TASK_MAPPING`/env wrapper 默认参数；
  - 或 `get_libero_path()` 指到不同的 `bddl_files/init_states/assets` 根目录；
  - 进而造成“看起来同名任务，但加载的 XML/资产/碰撞几何不是你生成 init 时那一份”。

这种“生成-评测不一致”在症状上经常表现为：**某些任务特别不稳定、接触瞬间爆炸/弹飞、但你在本地可视化又未必能稳定复现**。

---

## 4. 哪些差异最可能导致你观察到的“触碰即飞”

下面按“可能性/匹配度”从高到低排序：

### A. 初始状态存在轻微穿插（最常见、也最符合“触碰瞬间爆炸”）
触碰瞬间弹飞通常意味着：接触求解器突然要同时满足多组 contact/constraint，而其中某些接触在初始就有较深 penetration 或几何配置很糟，导致**巨大的纠正冲量**。

ER 流程中更容易触发该问题的原因：
- region 基于 `er_constants.py` 的脚印估计；复杂形状（把手、细长凸起、非凸）会让“脚印”偏乐观。
- 你手动调位置后，如果只是“视觉上不交叉”，但仍可能存在：
  - 与 fixture 侧壁轻微穿插；
  - 物体底部与台面/托盘边缘轻微穿插（高度/倾角问题）；
  - 多物体之间“几乎接触”的状态在某些 seed 下变成穿插。

### B. “换物体”导致碰撞几何/惯性参数不稳定（尤其是 turbosquid / 扫描类资产）
即使初始不穿插，某些物体的碰撞 mesh 如果很碎/很薄/非凸组合不合理、或惯性/质量异常，抓取/推挤时也会出现“轻触就飞”的反常动力学。

ER 相较于官方 LIBERO 任务更容易发生：因为 ER 可能把原本没有一起出现过的物体、fixture、region 组合到同一场景中；而这些资产在原 benchmark 中未必被验证过“互相接触时仍稳定”。

### C. 生成 init 与在线评测使用了不同的 `libero` 代码/资产/配置
如果在线评测导入的是 `LIBERO-PRO/libero`（或 `~/.libero/config.yaml` 指向了不同根目录），你生成的 `.pruned_init` 可能会被应用到“结构不同但 state_dim 恰好一致/或被静默处理”的仿真上，造成很难解释的动力学异常。

### D. settle steps 不足，把“不稳定 reset”固化进 init 文件
`scripts/generate_benchmark_init_files.py` 默认 `--settle-steps 10`，对一些“刚好卡在边界”的 reset 不够。
这种情况下物体可能在前几十步表面看起来稳定，但一旦引入机械臂接触，就触发爆炸。

---

## 5. 建议的定位顺序（最省时间的排查路径）

### 5.1 先确认“评测时到底用的是哪一套 libero/哪一份资源路径”
重点看这两件事是否与生成 init 时一致：
- Python import 来自哪里：`import libero; print(libero.__file__)`
- 配置路径指向哪里：`~/.libero/config.yaml` 里的 `bddl_files` / `init_states`（以及如果存在的 `assets`）

### 5.2 针对“会飞”的具体任务/seed，检查是否存在初始穿插
建议做两类检查（都只需要在 reset 后做）：
- **可视化 collision mesh**（`render_collision_mesh=True` 类似参数）看是否有明显穿插。
- **数值检查**：reset + settle 后读取接触信息（接触数量、最小接触距离、是否存在明显负距离 penetration）。  
  如果在“还没动机械臂”时就有很深 penetration，基本可以直接判定是初始状态问题。

### 5.3 用 ER 自带的 overlap/validation 工具先过滤掉明显问题任务
仓库已经提供了针对 BDDL region 的分析/修复工具（但它们仍是 2D 近似，不保证 100%）：
- `er_extension/scripts/check_bddl_overlaps.py`
- `er_extension/scripts/bddl_validation.py`

### 5.4 生成 init 时加大 settle，并丢弃“不稳定”的 init
最直接的对照实验：
- 把 `scripts/generate_benchmark_init_files.py` 的 `--settle-steps` 从 10 提到 50/100，看“触碰即飞”的比例是否显著下降。  
下降明显就说明主要矛盾在“初始不稳/穿插未被消解”。

---

## 6. 针对你当前情况的“高概率改进点”

结合你已经“手动调整了所有 object 位置”这一事实，最容易忽略、但最关键的点是：

1) **你调整的是 region 的中心/范围，但 reset 会在 region 内再次采样**  
只要 region 还保留一定面积（即使很小），某些 seed 仍可能采到不稳定位置；尤其在多物体拥挤、靠近 fixture 边界时。

2) **2D 不交叉不等于 3D 不穿插**  
特别是：
- 有把手/细长突出部分的 mug / frypan；
- 有侧壁的 basket / tray；
- 与 cabinet/stove 等 fixture 的几何相邻时。

3) **请避免把“大替换物体”放进原本为“小物体”设计的 region**  
如果你在 er_object 中做了 object type 替换（或 source 组合导致等价效果），即便 region 的 AABB 不交叉，也可能出现“物体的一部分伸出 region，直接顶进别的几何体”。

---

## 7. 你可以直接照抄的自查清单（建议按顺序）

1. 评测进程里确认 `libero.__file__` 指向与你生成 init 时同一套代码库。
2. 确认 `~/.libero/config.yaml` 的 `bddl_files/init_states` 指向你期望的目录（避免加载到旧 init 文件）。
3. 对“会飞”的任务挑 1–2 个 init state：reset 后渲染 collision mesh，观察是否初始就穿插/卡边。
4. 把该任务的 init 生成 `settle_steps` 提到 100 做对照。
5. 若仍不稳，优先怀疑“该物体资产的碰撞/惯性不稳”或“与特定 fixture 组合时碰撞几何很糟”，需要进一步限制候选物体或重新定义更宽松的 region。

