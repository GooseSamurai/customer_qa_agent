# T008-T011 真实业务知识 RAG：业务和设计学习笔记

## 1. 这组任务做什么

T008-T011 现在实现一条真实的本地 RAG 链路：

```text
业务知识文档
→ Markdown 标题切分
→ BGE 中文 Embedding
→ Chroma 向量库
→ BGE CrossEncoder 重排
→ KnowledgeEvidence
```

它服务于 Finding 中需要业务知识核验的问题，例如退款时间、退换货资格、物流异常和优惠解释。

## 2. T008：文档和切分

### 2.1 文档到底指什么

这里不是法律法规，也不是客服会话，而是质检时需要查询的平台业务知识：

- 商品咨询答复规范；
- 物流异常处理规范；
- 退换货资格与处理规范；
- 退款处理规范；
- 优惠与价格保护规范；
- 投诉升级处理规范。

这些文档明确标记为 `synthetic_sample`，用于模拟企业平台内部规则，不冒充淘宝或京东官方文档。

### 2.2 Metadata

每份文档包含：

```text
source_id
title
source_type
source_url
channel
category
policy_type
effective_date
expire_date
```

其中：

- `category` 表示业务场景；
- `policy_type` 表示规则类型；
- `effective_date` 和 `expire_date` 用于后续过滤不适用政策；
- `source_id` 和 `source_url` 用于追溯来源。

### 2.3 切分方式

使用 LangChain：

```python
MarkdownHeaderTextSplitter
```

按 `#`、`##`、`###` 标题切分。

这样每个 chunk 通常对应：

```text
适用范围
回答要求
禁止承诺
退款路径
到账时间
升级要求
```

比按固定字符数切更贴近业务文档结构。

当前六份样例文档共产生：

```text
19 个 chunk
```

## 3. T009：中文 Embedding 和 Chroma

### 3.1 Embedding 模型

使用：

```text
BAAI/bge-small-zh-v1.5
```

它把文本转换成真正的语义向量，而不是字符频次。

例如：

```text
查询：客服承诺今晚退款到账
文档：没有预计到账时间时不得承诺当晚到账
```

即使个别词不完全相同，也可能被召回。

### 3.2 Chroma 向量库

每个 `KnowledgeChunk` 被转换成 LangChain `Document`：

```text
page_content = chunk.text
metadata = source_id + chunk_id + section + 业务元数据
```

然后写入 Chroma。

Chroma 负责：

- 保存向量；
- 根据查询向量做相似度召回；
- 按 Metadata Filter 筛选；
- 返回 `(Document, relevance_score)`。

### 3.3 Metadata Filter

例如只查询退款业务：

```python
{"channel": "web", "category": "refund"}
```

Chroma 多条件过滤使用 `$and` 格式，因此代码中转换为：

```python
{"$and": [{"channel": "web"}, {"category": "refund"}]}
```

### 3.4 离线模型加载

模型已经提前下载到 Hugging Face 缓存。代码从缓存中找到实际模型目录，再把目录路径交给模型加载器，避免运行阶段再访问网络。

## 4. T010：真实 Reranker

第一次向量召回负责“找出一批可能相关的片段”，但不保证顺序完全准确。

T010 使用：

```text
BAAI/bge-reranker-base
```

对候选片段做第二次打分：

```text
query + chunk.text
→ CrossEncoder
→ 相关性分数
→ 降序排列
```

重排过程不会修改原始 `KnowledgeChunk`，因此 `source_id`、`chunk_id` 和文本仍然可追溯。

## 5. T011：知识工具

工具接口：

```python
search_knowledge(
    query,
    chunks,
    filters=None,
    top_k=3,
    as_of=None,
)
```

内部流程：

```text
retrieve
→ BGE + Chroma
→ rerank
→ 转成 KnowledgeEvidence
```

输出：

```text
list[KnowledgeEvidence]
```

它不决定是否调用，也不判断知识是否能证明客服违规。调用时机和最终结论属于后续 Agent 和复判流程。

## 6. 实际验证

真实文档和真实模型的端到端查询：

```text
查询：客服没有确认订单就承诺今晚退款到账
filter：channel=web, category=refund
```

返回结果的第一相关片段来自：

```text
refund_processing_rules-chunk-2
```

内容包含：

```text
如果订单系统中没有预计到账时间，客服不得承诺“今晚到账”“马上到账”等确定时间。
```

这说明 Embedding、Chroma、Metadata Filter 和 Reranker 已经共同工作。

## 7. 设计取舍

### 7.1 为什么不继续使用字符频次

字符频次只能比较字面重叠，无法理解语义，不适合作为简历里的 RAG 能力。

### 7.2 为什么使用本地 BGE

优点：

- 中文效果比通用小模型更合适；
- 可以离线复现；
- 不依赖外部 API 和密钥。

代价：

- 模型文件较大；
- 首次加载和推理需要时间和内存。

### 7.3 为什么先召回再重排

召回追求快速覆盖，重排追求更准确的相关性顺序。两阶段组合比只做其中一步更接近真实 RAG 系统。

### 7.4 为什么当前每次查询重新构建 Chroma

当前知识库只有 19 个 chunk，直接构建便于理解和验证。生产环境会改为持久化索引、增量更新和独立的索引构建任务。

## 8. 业务场景问题

### 8.1 客户问退款为什么还没到账，应该检索什么？

检索退款处理规范中的“到账时间”和“延迟处理”章节，并核对订单上下文中的退款状态。

### 8.2 客服说“超过 7 天不能退”，应该检索什么？

检索退换货规范的“七天无理由退货”和“质量问题退换”章节，再结合订单签收时间和商品情况复判。

### 8.3 客服承诺无依据的到账时间怎么办？

先检索退款规则，确认是否存在预计到账时间；如果没有依据，后续 Finding 可判定为无依据承诺。

### 8.4 物流长时间没有更新怎么办？

检索物流异常处理规范，核对 48 小时无更新、派送失败和丢件等处理条件。

### 8.5 优惠券和价保解释不一致怎么办？

检索优惠与价格保护规范，区分优惠券、活动价、会员价和价保条件，避免把不适用规则当成通用规则。

### 8.6 如果未来接入真实平台文档怎么办？

保持 `documents.json`、Metadata 和 chunk 输出结构不变，替换 Markdown 文档和来源信息即可。Embedding、Chroma 和工具接口不需要跟着变化。

## 9. 面试问题与回答

### 问题 1：你如何设计业务知识 RAG？

**回答：**

我会先按业务场景整理文档和元数据，再做结构化切分；然后用中文 Embedding 写入向量库，先召回候选片段，再用 CrossEncoder 重排，最后把来源、片段编号和文本转换为可追溯证据。

### 问题 2：为什么不能只依赖向量相似度？

**回答：**

向量召回适合快速找出候选，但排序不一定稳定，而且无法独立完成业务过滤。因此需要 Metadata Filter、有效期判断和二次重排，才能更贴近真实质检场景。

### 问题 3：为什么 Metadata 和文档内容一样重要？

**回答：**

内容决定语义相关性，Metadata 决定适用范围。同一个退款问题在 web、app 或不同活动条件下可能有不同规则，只靠文本相似度可能召回错误政策。

### 问题 4：为什么选择 BGE 中文模型？

**回答：**

项目输入是中文客服会话和中文业务规则，BGE 中文模型在本地部署、中文语义检索和可复现性之间比较平衡，也便于后续替换为更大的模型。

### 问题 5：召回和重排的职责有什么不同？

**回答：**

召回负责从整个知识库中缩小范围，重排负责对少量候选做更精细的相关性判断。先召回再重排，兼顾速度和准确性。

### 问题 6：如何避免使用过期政策？

**回答：**

文档入库时保存生效和失效日期，检索时传入查询时间，排除失效日期早于该时间的片段。复杂的政策优先级后续再结合规则版本处理。

### 问题 7：知识工具和 Agent 的边界是什么？

**回答：**

工具负责查询知识并返回证据，Agent 负责决定是否需要查询、查询什么条件，以及如何结合其他证据判断。工具不决定最终质检结论。

## 10. 学习检查与答案

### 1. RAG 的文档和 Conversation 有什么区别？

Conversation 是被检查的客服对话，RAG 文档是核验业务事实时使用的平台规则和 SOP。

### 2. chunk 为什么要保留 source_id 和 chunk_id？

后续质检结论需要能定位到原始文档的具体片段，形成可追溯证据。

### 3. Embedding 的作用是什么？

把文本变成能表达语义关系的向量，让语义接近的内容在向量空间中也接近。

### 4. Chroma 在链路中负责什么？

保存向量、执行相似度召回，并支持基于 Metadata 的筛选。

### 5. Reranker 和向量召回的区别是什么？

向量召回先快速找候选，Reranker 再对候选逐条进行更精细的相关性打分和排序。

### 6. Metadata Filter 解决什么问题？

限制检索范围，避免把不同渠道、场景或政策类型的片段混在一起。

### 7. KnowledgeEvidence 包含哪些关键信息？

来源编号、片段编号、文本和 metadata，能够支持后续证据校验和引用。

### 8. 当前 RAG 距离生产环境还缺什么？

还缺企业真实文档接入、持久化索引、增量更新、权限控制、批量评测和线上性能优化。

## 11. 一句话总结

T008 把真实业务知识按标题切分成可追溯片段，T009 用 BGE Embedding 和 Chroma 做语义召回与 Metadata Filter，T010 用 BGE CrossEncoder 做二次重排，T011 返回可追溯的 KnowledgeEvidence；这套实现使用真实模型和向量库，而不是字符频次模拟。