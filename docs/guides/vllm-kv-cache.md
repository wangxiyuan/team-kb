---
title: vLLM v1 KV Cache 走读：PagedAttention、块管理与前缀缓存
date: 2026-10-22
author: wangxiyuan
status: active
tags: [kv-cache, paged-attention, prefix-caching, memory]
type: guide
---

# vLLM v1 KV Cache 走读：PagedAttention、块管理与前缀缓存

## 目标读者

需要在 vLLM v1 上做性能调优、显存估算、前缀缓存排障，或准备改 KV cache 相关代码的工程师。默认读者了解 Transformer 的 prefill/decode 流程，知道 K/V 是什么，读过 PagedAttention 的基本思想。

## 正文

### 1. KV cache 解决什么问题

自回归 decode 每生成一个 token，都要对全部历史 token 做 attention。如果每步都重算历史 K/V，单步成本随上下文线性增长，整体接近 O(n²)。KV cache 把已算过的每层 K/V 存下来，后续步骤只计算新 token 的 K/V，历史部分直接读缓存。本质是**用显存换计算**：decode 阶段每步的 attention 读放大仍在，但不再重复做历史 token 的 projection。

vLLM 的关键设计不是“缓存 K/V”本身，而是把缓存切成固定大小的 **block**，用类似操作系统分页的方式管理，从而支持不连续的物理内存、请求间共享和按需回收。

### 2. 核心抽象

| 抽象 | 作用 | 代码位置 |
|---|---|---|
| `block` | KV cache 分配/回收/共享的最小单位，含 `block_size` 个 token | `vllm/config/cache.py:182` |
| `KVCacheBlock` | block 的元数据：`block_id`、`ref_cnt`、`block_hash`、空闲链表指针、`is_null` | `vllm/v1/core/kv_cache_utils.py:162` |
| `FreeKVCacheBlockQueue` | 空闲块双向链表，支持 O(1) 中间摘除；LRU 在队首 | `vllm/v1/core/kv_cache_utils.py:258` |
| `BlockPool` | 全部物理 block + 空闲队列 + 前缀缓存哈希表 | `vllm/v1/core/block_pool.py:136` |
| `KVCacheManager` | 调度器使用的分配接口：查前缀命中、分配 slot、释放 | `vllm/v1/core/kv_cache_manager.py:131` |
| `KVCacheConfig` | 引擎最终解析出的容量与分组：`num_blocks`、`kv_cache_groups` | `vllm/v1/kv_cache_interface.py:1506` |

几个容易混淆的点：

- `block_size` 默认是 **16 个 token**（`CacheConfig.DEFAULT_BLOCK_SIZE`），它是**调度与缓存的分配粒度**，不要求等于 attention kernel 内部的 tile 大小。
- 一个 block 的 `ref_cnt` 表示多少请求正在引用它。多请求共享同一前缀时，靠 `ref_cnt` 防止被回收。
- `null_block` 是 `block_id=0` 的占位块，`is_null=True`，永不缓存，`ref_cnt` 不维护，用于表示“这段逻辑位置没有物理 KV”（如 sliding window 外的块）。
- **KV cache group**：同一张 block table 的层集合。纯 full-attention 模型通常只有一个 group；混合模型（full attention + sliding window / Mamba）会有多个 group，每个 group 有自己的 `KVCacheSpec` 和 block 大小（`vllm/v1/kv_cache_interface.py:1485`）。

### 3. 显存如何变成 block

启动时 vLLM 先做一次 dummy forward 的显存 profiling，得到模型权重、激活、CUDA graph 等占用后，把剩余可用显存按 `gpu_memory_utilization` 划给 KV cache（`vllm/v1/worker/gpu_worker.py:638`）。也可以通过 `kv_cache_memory_bytes` 直接指定 KV cache 字节数、跳过 profiling；`num_gpu_blocks_override` 用于测试。

然后按每种 `KVCacheSpec` 计算每个 block 的字节数，得到 `num_blocks`。对最常见的 dense attention，单层单 block 的近似公式是：

```
block_bytes ≈ 2 * num_kv_heads_per_rank * head_size * dtype_bytes * block_size
```

其中因子 2 是 K 和 V；`num_kv_heads_per_rank` 是 TP 切分后每卡的 KV head 数；`dtype_bytes` 例如 bf16 为 2。整模型还要乘层数（实际布局由 `AttentionSpec.page_size_bytes` 决定，`vllm/v1/kv_cache_interface.py:537`）。MLA、Mamba、量化 KV cache、sliding window 等会走不同的 spec，不要直接套公式。

例：32 层、每卡 8 个 KV head、head_size=128、bf16、block_size=16：

```
2 * 32 * 8 * 128 * 2 * 16 = 2 MiB / block
若 KV 显存 20 GiB，则约 10,240 blocks，即约 163,840 tokens 的容量
```

启动日志会直接给出结果（`vllm/v1/core/kv_cache_utils.py:1102`）：

```
GPU KV cache size: 163,840 tokens, Maximum concurrency for 8,192 tokens per request: 20.00x
```

### 4. 一次请求的 KV 生命周期（调度视角）

调度器在每个 step 为请求调用 `allocate_slots`（`vllm/v1/core/sched/scheduler.py:831`）。核心流程：

1. **查前缀命中**：`KVCacheManager.get_computed_blocks` 用请求的 block hash 链在缓存里找最长连续前缀（`vllm/v1/core/kv_cache_manager.py:264`）。注意 `max_cache_hit_length = num_tokens - 1`：即使全命中，也必须留最后一个 token 重算以产生 logits（`kv_cache_manager.py:289-295`）。
2. **分配 slot**：`allocate_slots` 把请求的 token 划分成 `comp | new_comp | ext_comp | new | lookahead` 几段（`kv_cache_manager.py:420-452`）。其中 `comp` 是已计算、`new_comp` 是本次前缀命中、`ext_comp` 是外部 KV connector 提供、`new` 是新 token、`lookahead` 是投机解码预留。
3. **先释放再分配**：sliding window 之外不再需要的块会先被释放，减少不必要的淘汰（`kv_cache_manager.py:546-559`）。
4. **空间不足**：`allocate_slots` 返回 `None`，调度器从 running 队列尾部抢占最低优先级请求（`scheduler.py:843-899`）。v1 的抢占是**重算**：`_preempt_request` 释放该请求全部 block、把 `num_computed_tokens` 清零、放回 waiting 队列（`scheduler.py:1651-1694`），下次重新 prefill。
5. **请求结束**：`KVCacheManager.free` 逆序释放 block，让尾部块先成为淘汰候选（`kv_cache_manager.py:620`）。

### 5. 前缀缓存

前缀缓存让相同前缀的请求复用已有 K/V。关键在 block hash 的设计：

```python
block_hash = hash(parent_block_hash, curr_block_token_ids, extra_keys)
```

见 `hash_block_tokens`（`vllm/v1/core/kv_cache_utils.py:707`）。哈希链式包含父块，因此“前缀相同”是严格从第 0 个 token 开始逐块相同的；只匹配中间一段不算命中。`extra_keys` 用于把多模态特征、LoRA、`cache_salt` 等纳入 key，避免不同语义的内容误命中。

几个工程细节：

- **哈希粒度**：`hash_block_size`（配置项 `prefix_match_unit`）可以比物理 block 更细，例如物理块 1024 token、哈希每 32 token 一个点，从而在块内部也能命中（`vllm/config/cache.py:200`）。
- **默认算法**：`sha256`（`vllm/config/cache.py:256`）。非加密哈希需要固定 `PYTHONHASHSEED` 才能跨进程复用缓存。
- **group 维度**：缓存 key 实际是 `BlockHashWithGroupId`，即 block hash 后追加 4 字节 group id（`kv_cache_utils.py:60`），因为不同 KV cache group 的块不能混用。
- **登记时机**：block 写满后才调用 `cache_full_blocks` 登记到 `cached_block_hash_to_block`（`vllm/v1/core/block_pool.py:226`）；部分块不会作为前缀缓存命中点（除非使用 partial entry 机制）。
- **命中即 pin**：命中块会 `touch`，`ref_cnt += 1` 并从空闲队列摘除，防止在本次请求用完前被淘汰（`block_pool.py:752`）。
- **清理**：真正复用块时才 `_maybe_evict_cached_block` 清掉旧 hash 并失效（`block_pool.py:729`）；`reset_prefix_cache` 可整体失效，但要求除 null block 外没有其他块在用（`block_pool.py:831`）。

### 6. 回收、淘汰与 LRU

`BlockPool.free_blocks` 的淘汰顺序是有讲究的（`block_pool.py:776`）：

- `ref_cnt -= 1`，只有降到 0 才进入空闲队列。
- **没有 hash 的块**（从未被前缀缓存、或缓存未启用）：插到空闲队列**队首**，优先复用，提升 GPU 局部性（LIFO）。
- **有 hash 的块**（前缀缓存候选）：插到**队尾**，让最久未使用的先被淘汰（LRU）。

空闲队列本身的顺序是：队首最久未使用、同一次释放时尾部块优先（`kv_cache_utils.py:258-274`）。这解释了为什么 `free` 要逆序释放：尾部 block 更可能是“整条链的末端”，先淘汰它损失最小。

KV cache 使用率 = 已用块 / (总块数 - 1)，减 1 是排除 null block（`block_pool.py:881`）。

### 7. 关键配置与调优

| 配置 | 默认 | 影响 |
|---|---|---|
| `block_size` | 16 | 越大：元数据/调度开销越小，内部碎片越大，前缀命中粒度越粗 |
| `gpu_memory_utilization` | 0.92 | 越高：KV 容量越大、并发越高，但留给激活/通信的余量越小 |
| `kv_cache_memory_bytes` | 未设置 | 手动指定 KV 字节数，跳过 profiling，适合精确控制 |
| `enable_prefix_caching` | True | 关闭后不建哈希表，省 CPU/内存，但相同前缀全部重算 |
| `prefix_match_unit` | 未设置 | 哈希粒度；可细于物理 block，提升块内命中率 |
| `kv_cache_dtype` | auto | fp8 可显著提升容量，需模型/后端支持 |

调优直觉：

- **长上下文、多轮对话、RAG**：前缀缓存收益最大，优先确认 hit rate，而不是盲目加显存。
- **高并发短请求**：block_size 过大导致尾部浪费；关注 `Maximum concurrency` 与 KV usage。
- **混合模型**：不同 attention 类型的 block 大小可能不同，容量与命中行为要按 group 分别看。

### 8. 可观测性

- **日志**：启动时的 `GPU KV cache size` 与 `Maximum concurrency` 是最直接的容量指标（`kv_cache_utils.py:1102`）。
- **指标**：`vllm:kv_cache_usage_perc`、`vllm:prefix_cache_queries`、`vllm:prefix_cache_hits`（`vllm/v1/metrics/loggers.py:620,662,673`）。命中率 = hits / queries。
- **统计开关**：`log_stats` 打开后 `KVCacheManager` 会记录 `PrefixCacheStats`（`kv_cache_manager.py:236`）。

### 9. 常见误区

1. **“block 就是 attention kernel 的 tile”**：不是。block 是分配/缓存单位；kernel 内部布局由 attention backend 和 `AttentionSpec` 决定。
2. **“任意相同片段都能命中”**：必须从第 0 个 token 开始的连续整块前缀，且同一 KV cache group。
3. **“全命中就不用算了”**：最后一个 token 必须重算以产生 logits；实际还会因块对齐重算整个尾块。
4. **“前缀缓存是额外缓存”**：它复用同一池物理 block，命中块通过 `ref_cnt` pin 住；容量不足时照样被淘汰。
5. **“抢占是 swap 到 CPU”**：v1 当前是释放并重算（`_preempt_request` 清零 `num_computed_tokens`），代价是重复 prefill。
6. **“prefix hit 高就一定吞吐高”**：还要看 prefill/decode 比例、块对齐浪费、以及命中块是否被 pin 住导致其他请求被抢占。

## 实践验证

### 1. 代码级验证

在 vLLM 仓库运行 KV cache 单元测试：

```bash
uv run pytest tests/v1/core/test_single_type_kv_cache_manager.py -q
uv run pytest tests/v1/core/test_kv_cache_utils.py -q
```

### 2. 运行时容量验证

启动一个开启前缀缓存的服务，观察启动日志：

```bash
vllm serve <model> --enable-prefix-caching --max-model-len 8192
```

在日志中确认：

```
GPU KV cache size: <N> tokens, Maximum concurrency for 8,192 tokens per request: <X>xx
```

用第 3 节的公式反算 `N ≈ num_gpu_blocks * block_size`，与日志对照；若差异大，检查是否使用了 MLA/Mamba/量化 KV、TP 切分或 `kv_cache_memory_bytes`。

### 3. 前缀命中的端到端验证

1. 启动带 metrics 的服务（默认 `/metrics` 可用）。
2. 先用一个长前缀（例如 2,000 token 的固定文档）发一次请求。
3. 再用**完全相同的前缀**加不同后缀发第二次请求。
4. 观察 `vllm:prefix_cache_hits / vllm:prefix_cache_queries` 是否上升；同时对比两次请求的 TTFT。

如果命中率不涨，优先检查：前缀是否从第一个 token 起完全一致、`enable_prefix_caching` 是否开启、是否跨了不同 KV cache group、`cache_salt`/LoRA/多模态 extra keys 是否不同。

### 4. 抢占行为验证

把 `gpu_memory_utilization` 调低或 `max_num_seqs` 调大，制造显存压力；在日志/指标里观察 `num_preemptions` 与 KV usage。预期现象：KV usage 接近 1 时开始抢占，被抢占请求的 `num_computed_tokens` 归零并重新 prefill，吞吐下降。

### 5. 快速自检清单

- [ ] 启动日志的 KV tokens 与手算量级一致
- [ ] 重复前缀请求的 hit rate 明显上升
- [ ] TTFT 在第二次请求下降（长前缀场景）
- [ ] 显存压力下出现抢占而非 OOM
- [ ] `kv_cache_usage_perc` 不长期贴近 100%（否则并发/显存配置需调整）
