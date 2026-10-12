# Battery Dispatch Sim｜储能削峰仿真

一个标准库 Python 小项目：对单个表后电池进行 24 小时逐时仿真，在低负荷时段充电、超过设定阈值时放电，并检查 SoC、电池功率和能量守恒。

## 运行

需要 Python 3.10 或以上版本，在项目目录运行：

```powershell
python battery_dispatch_sim.py
python -m unittest discover -s tests -v
```

生成文件：`data/hourly_load.csv` 是仿真负荷，`results/dispatch.csv` 是逐时功率与 SoC，`results/report.json` 汇总削峰和能量核算。固定随机种子使示例可复现。

## 仿真规则

电池在 0–5 时段尝试充电，负荷超过 31 kW 时尝试放电。充放电功率上限均为 7 kW；SoC（荷电状态）限制在 2–22 kWh，电池容量为 24 kWh；充电与放电效率均设为 95%。这些数值只为演示而选。

每个小时检查状态方程：`SoC_after = SoC_before + charge × charge_efficiency − discharge / discharge_efficiency`。报告也会检查全天能量平衡残差，并将峰值变化、充放电量和转换损耗分别列出。损耗不是“节省”的另一种叫法：电池会因效率小于 100% 而增加能量需求。

## 术语备注

- **表后储能（behind-the-meter）**：电池安装在用户侧电表之后，参与本地负荷管理。
- **削峰（peak shaving）**：在负荷高时放电，以降低电网侧观察到的最大功率。
- **SoC**：电池当前储存的能量状态，本例以 kWh 表示。
- **充放电效率**：电能输入或从电池取出时，电池内可用能量变化的比例。
- **能量守恒残差**：状态方程两边的数值差；本程序中应接近浮点数误差范围内的 0。

## 数据边界

负荷曲线、电池规格、阈值和效率都是合成教学参数。仿真未建模电池老化、温度、逆变器、备用容量、费率、并网规则或预测不确定性。削峰结果不是现场实测、真实减排证明或储能调度建议。
