# US West CN2 GIA Stock Monitor (GitHub Actions Edition)

运行在 GitHub Actions 云端的**美西 CN2 GIA 限量版专精监控**，聚焦搬瓦工（BandwagonHost）与 DMIT 的美西 CN2 GIA 限量主力套餐，具备以下能力：

- **12 款核心目标清单**：覆盖 MegaBox Pro / BiggerBox Pro / DC9 / DC6 / GIA-E / THE PLAN 及 DMIT LAX.Pro（MALIBU / Wee / PalmSpring / AN3.Pro.TINY）
- **未知新品 PID 动态捕获**：自动扫描 `stock.bwg.net` 与 `vpsding.com` 中未收录的低价美西 CN2 GIA 及全新高编号限量 PID，并对搬瓦工做官网购物车二次核验
- **抗抖动状态管理**：数据源异常时保留旧状态防止重复轰炸，全部数据源不可用时以非零退出码告警，邮件发送成功后再写入 `state.json`
- **官方频道全量增量追踪**：按消息序号单调递增扫描 `@dmitnews` 与 `@BandwagonHostNews`，连发多条不漏消息

## 环境变量 / GitHub Actions Secrets
在仓库 **Settings -> Secrets and variables -> Actions -> New repository secret** 中配置：
- `SMTP_USER`：发件邮箱账号（**必填**）
- `SMTP_PASS`：邮箱客户端授权码（**必填**）
- `RECIPIENT`：收件邮箱（可选，留空默认发给 `SMTP_USER`）

## 本地调试
```bash
# 只跑接口与解析检查，不发邮件、不改 state.json
python3 vps_stock_monitor.py --dry-run
```

> **提示**：GitHub Actions 公开仓库若连续 60 天无任何提交会自动停用定时任务；黑五等高峰时段免费队列也存在延迟，建议配合手机端 Telegram 频道强提醒一起使用。
