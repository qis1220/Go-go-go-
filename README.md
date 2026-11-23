# Agent Projects

围绕 Agent 工具执行、状态管理与评测构建的个人项目集合。各项目提供可运行代码、设计说明和验证结果。

## 项目

### [Agent Reliability](projects/agent-reliability/README.md)

一个工具执行状态与幂等处理的离线原型，用于验证超时、重复请求、取消和权限限制下的行为。

- 区分执行成功、明确失败与结果未知。
- 使用操作ID避免同一操作被重复发送。
- 记录请求、执行步骤和结果，支持回溯检查。
- 提供9个固定验收用例与评测输出。

## 快速运行

Python 3.10+，无需第三方依赖：

```sh
python3 projects/agent-reliability/demo.py
```

查看终端结果，或打开 `projects/agent-reliability/results/` 下的评测报告与轨迹。

当前版本使用模拟工具，不连接真实设备或模型API。实现范围及后续改进见项目说明。
