# Model Evaluation｜模型配置与Token成本对比

为知识问答应用比较候选模型配置：保存回答、API返回的Token用量、请求总耗时和按显式费率计算的Token成本，避免只看单价或回答观感。

## 快速运行

Python 3.9+，无第三方依赖，在仓库根目录执行：

```sh
python3 projects/model-evaluation/compare.py
python3 -m unittest discover -s projects/model-evaluation -p 'test_*.py'
```

默认只使用合成回答与用量，不联网、不收费。结果保存到 `results/offline.json`；DEMO费率与示例模型不是任何厂商的实际报价或性能。离线模式不填写延迟，不自动给质量打分。

## 实际调用

复制配置文件到本地，填入你获准使用的模型、HTTPS API基础地址、同币种费率及报价来源/日期。显式设置环境变量 `MODEL_EVAL_API_KEY`，再执行：

```sh
python3 projects/model-evaluation/compare.py --config /path/to/local-config.json --live --output /path/to/private-live-result.json
```

真实调用可能收费；脚本不自动发现账号、读取其他项目凭据或选择模型。使用固定合成问题，不传入业务资料。支持的接口是提供 `choices` 和 `usage` 的 Chat Completions 风格子集，基础地址应包含适当版本路径，例如`https://provider.example/v1`。不代表兼容所有供应商、模型或Responses接口。

## 成本口径

`((输入Token-其中缓存Token)×普通输入单价 + 缓存Token×缓存单价 + 输出Token×输出单价)/1,000,000`

缓存Token是输入的一部分，不能重复相加。输出Token按API口径使用，不根据可见文字猜测。这里只估算配置所覆盖的Token费用；缓存写入、工具、检索、沙箱、服务层级及税费等另计。价格需要人工更新，并核对上下文分档等附加规则。

## 验证与边界

- 5项自动检查覆盖缓存子集、无缓存、非法用量/价格，以及单配置失败时保留其他结果。
- 两个离线配置成功生成记录。只有成本算术和记录链路得到验证；未进行真实模型调用、延迟或质量测评。
- 请求失败成本标为未知，不当作零费用；错误记录不输出异常正文、凭据或响应头。
- 真实调用无自动重试，不跟随携带凭据的重定向。
- API成功不代表答案正确，需同任务人工评分及更多保留样本。
- 全量响应usage可含厂商扩展；缺少必要字段时本配置报错，不能静默猜测。
- 当前仅单任务顺序比较、单次请求、文本响应。没有流式首字测量、重复试验、并发或生产监控。

## 后续方向

扩展固定任务集、人工评分、版本追踪与重复试验，结合任务通过率和单次成功任务成本选择方案，再验证是否值得加入工具或更复杂编排。
