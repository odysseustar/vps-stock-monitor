# VPS CN2 GIA Stock Monitor (GitHub Actions Edition)

24 小时运行在 GitHub Actions 免费云端节点，自动监控搬瓦工（BandwagonHost）与 DMIT 的纯血 CN2 GIA 限量神机库存及官方 Telegram 促销动态，发现补货立即发送分级提醒邮件。

## 环境变量 / GitHub Actions Secrets
在 GitHub 仓库的 **Settings -> Secrets and variables -> Actions -> New repository secret** 中添加：
- `SMTP_PASS`：163 邮箱客户端授权码（必填）
- `SMTP_USER`：发件邮箱（可选）
- `RECIPIENT`：收件邮箱（可选）
