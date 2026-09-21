# T020-T021 SFT 数据与 LoRA 训练：业务和设计学习笔记

## 1. 这组任务解决什么

T020-T021 把人工复核结果转成可用于 LoRA-SFT 的数据，并提供真实训练入口。

```text
Review 候选数据
→ Conversation + QARule + Finding
→ Chat 训练格式
→ train / valid / test
→ LoRA-SFT
→ adapter
```

## 2. T020：SFT 数据构建

### 2.1 输入数据

候选 JSONL 来自 T019，每条样本包含：

- review_id；
- decision；
- Conversation；
- 人工确认或修正后的 Finding。

QARule 单独作为规则文件传入，保证模型学习的是：

```text
Conversation + 当前规则
→ Finding
```

### 2.2 训练样本格式

每条训练样本包含：

```text
messages = [
    {"role": "user", "content": 质检 Prompt},
    {"role": "assistant", "content": Finding JSON}
]
```

用户消息复用 `build_qa_prompt()`，保证训练输入和推理输入结构一致。

助手消息只输出 Finding JSON。

### 2.3 为什么不把政策答案写进训练目标

活动、退款和售后政策会变化。SFT 应学习：

- 如何按规则识别问题；
- 如何输出 Finding；
- 如何引用 Conversation Evidence；
- 何时提出 Claim 和 required_evidence。

动态政策答案由 RAG 检索，不写进模型参数。

### 2.4 train / valid / test

当前使用固定随机种子切分：

```text
train：训练 adapter
valid：训练过程中观察泛化
test：后续离线评测
```

切分后输出：

```text
train.jsonl
valid.jsonl
test.jsonl
statistics.json
```

小数据少于三条时全部留作训练，避免伪造有效验证集。

## 3. T021：LoRA 训练

### 3.1 配置文件

训练入口通过 JSON 配置指定：

- base_model_path；
- train_data_path；
- valid_data_path；
- output_dir；
- max_length；
- batch size；
- learning rate；
- LoRA r / alpha / dropout；
- target modules；
- bf16 和 gradient checkpointing。

参数不写死在业务代码中，训练实验通过配置调整。

### 3.2 训练流程

```text
加载 tokenizer
→ 加载 Qwen base model
→ PEFT 挂载 LoRA
→ 读取 train/valid JSONL
→ Chat Template 转 token
→ Transformers Trainer
→ 训练
→ 保存 adapter
```

LoRA 只训练新增的低秩参数，不全量更新基础模型，显存和存储成本更低。

### 3.3 实际冒烟验证

使用本地：

```text
G:\LLM\modelscope\hub\models\qwen\Qwen3-VL-2B-Instruct
```

执行了 1-step 冒烟训练：

```text
max_steps = 1
max_length = 128
lora_r = 4
lora_alpha = 8
bf16 = true
gradient_checkpointing = true
```

实际结果：

```text
train_loss = 4.241
eval_loss = 4.217
adapter_model.safetensors 已保存
adapter_config.json 已保存
trainer_state.json 已保存
```

这证明训练入口可以真实运行，但 1-step 只用于冒烟验证，不代表模型已经有效微调。

## 4. 业务场景

### 确认样本

人工确认 Finding 正确：

```text
assistant 目标 = 原 Finding
```

### 修正样本

人工修正原因、标签或证据：

```text
assistant 目标 = 修正后的 Finding
```

### 误报样本

false_positive 不进入正例 SFT，避免把错误质检行为教给模型。

### 数据泄漏控制

train / valid / test 必须按 case 或会话切分，不能把同一会话复制到三个集合中，否则评测会虚高。

## 5. 真实面试问题

### 问题 1：为什么 SFT 输入要复用推理 Prompt？

**回答：**

如果训练格式和推理格式不同，模型会学习一套格式，上线却又接收另一套格式。复用同一个 Prompt 构造函数可以保证训练、验证和推理一致。

### 问题 2：为什么动态政策不能作为 SFT 目标？

**回答：**

政策频繁变化，写进模型参数后每次变化都要重新训练。SFT 应学习质检能力和结构化输出，动态业务事实通过 RAG 或 Tool 获取。

### 问题 3：LoRA 和全量微调的区别是什么？

**回答：**

全量微调更新所有参数，成本高且容易破坏基础能力；LoRA 通过低秩增量矩阵适配任务，只保存小 adapter，适合快速迭代和多版本管理。

### 问题 4：为什么要保留 valid 和 test？

**回答：**

valid 用于训练过程观察泛化，test 用于最终评测。如果把所有数据都用于训练，就无法判断模型是真的提升还是记住了训练样本。

### 问题 5：1-step 训练成功代表模型可用了吗？

**回答：**

不代表。它只说明训练入口、显存、数据格式和保存流程可运行。模型效果必须通过正式数据规模、训练配置和离线指标验证。

## 6. 学习检查与答案

### 1. T020 的输入是什么？

人工复核候选 JSONL、QARule 和输出目录。

### 2. assistant 目标是什么？

一条标准 Finding JSON。

### 3. 为什么 false_positive 不进入正例？

它表示模型误报，直接训练会强化错误行为。

### 4. LoRA 保存了什么？

保存 adapter、adapter 配置、tokenizer 配置和 Trainer 状态，不复制完整 base model。

### 5. 为什么需要 train/valid/test？

分别用于学习、调参和最终评测，避免数据泄漏和过拟合判断失真。

## 7. 一句话总结

T020 将复核结果构造成统一 Chat SFT 数据，T021 使用 PEFT LoRA 和 Transformers Trainer 真实训练并保存 adapter；动态政策仍由 RAG 提供，1-step 冒烟只证明流程可运行，模型效果需要正式训练和评测。