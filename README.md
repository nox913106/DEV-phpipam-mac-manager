# MAC Manager

統整的 MAC 地址管理工具，整合 SNMP ARP 收集、LDAP MAC 查詢、月報表產生等功能。

## 📖 文件

- [Docs/MAC_Manager_User_Guide.html](Docs/MAC_Manager_User_Guide.html) - 使用說明書

## 功能

| 子命令 | 說明 |
|--------|------|
| `collect-arp` | 從網路設備收集 ARP 表 (IP-MAC 對應) |
| `query-ldap` | 查詢 LDAP RADIUS 已授權的 MAC 清單 |
| `monthly-report` | 彙整每日收集資料，產生月報表 |
| `compare` | 比對 ARP 與 LDAP 資料，找出未授權設備 |

## 安裝

### 依賴套件

```bash
pip install pyyaml
```

### 系統工具

- `snmpwalk` - 用於 SNMP 查詢
- `ldapsearch` - 用於 LDAP 查詢

```bash
# Ubuntu/Debian
apt install snmp ldap-utils

# CentOS/RHEL
yum install net-snmp-utils openldap-clients
```

## 設定

1. 複製設定檔範例：
   ```bash
   cp config.yaml.example config.yaml
   ```

2. 編輯 `config.yaml`，填入實際設定

3. 設定 LDAP 密碼環境變數：
   ```bash
   export LDAP_PASSWORD='your_password'
   ```

## 使用方式

### 收集 ARP 表

```bash
# 使用設定檔中的設備清單
python mac_manager.py collect-arp

# 使用指定的設備清單檔案
python mac_manager.py collect-arp --device-file /path/to/device_ips.txt
```

### 查詢 LDAP MAC

```bash
# 基本查詢
python mac_manager.py query-ldap

# 查詢並複製到 /tmp
python mac_manager.py query-ldap --copy-to /tmp/mac_addresses.txt
```

### 產生月報表

```bash
# 產生上個月的報表
python mac_manager.py monthly-report

# 產生指定月份的報表
python mac_manager.py monthly-report --month 2024-12
```

### 比對分析

```bash
# 比對 ARP 與 LDAP 資料
python mac_manager.py compare \
    --arp-file ./output/daily/mac_addresses_20241223-0805.csv \
    --ldap-file ./output/ldap_mac.txt \
    --output ./unauthorized_macs.txt
```

## Crontab 設定

```cron
# SNMP ARP 收集（上班時間每小時）
5 8-18 * * 1-5 root cd /home/sysadmin/mac-manager && python3 mac_manager.py collect-arp

# LDAP MAC 查詢（上班時間每2小時）
1 8-17/2 * * 1-5 root cd /home/sysadmin/mac-manager && LDAP_PASSWORD='xxxxx' python3 mac_manager.py query-ldap --copy-to /tmp/mac_addresses.txt

# 月報表（每月1號）
5 7 1 * * root cd /home/sysadmin/mac-manager && python3 mac_manager.py monthly-report
```

## 目錄結構

```
mac-manager/
├── mac_manager.py          # 主程式 CLI 入口
├── config.py               # 設定載入模組
├── config.yaml             # 設定檔（從 .example 複製）
├── config.yaml.example     # 設定檔範例
├── utils.py                # 共用工具函數
├── collectors/
│   ├── __init__.py
│   ├── snmp_collector.py   # SNMP ARP 收集
│   └── ldap_query.py       # LDAP MAC 查詢
├── reports/
│   ├── __init__.py
│   └── monthly_report.py   # 月報表產生
└── output/
    ├── daily/              # 每日 CSV
    └── monthly/            # 月報表
```

## 遷移指南

從原有腳本遷移：

| 原腳本 | 新命令 |
|--------|--------|
| `GetMAC_V6.py` | `python mac_manager.py collect-arp` |
| `RadiusMacV2.py` | `python mac_manager.py query-ldap` |
| `MonthReportV3.py` | `python mac_manager.py monthly-report` |

---

## 🚀 未來整合計畫（Roadmap）

以下功能規劃於未來版本實作：

### Phase 1：MCP 整合
- 在 `mcp_phpipam.py` 新增 `query_mac` 工具
- 讓 AI 助理可查詢「這個 MAC 是否已授權」
- 支援即時比對 ARP 資料與 LDAP 清單

### Phase 2：週報整合
- 在 `weekly_health_report` 加入 MAC 異常統計
- 輸出項目：
  - 未授權 MAC 數量
  - 已授權但未活動的 MAC 數量
  - 新增 MAC 清單（與上週比對）

### Phase 3：phpIPAM 資料同步
- 將 mac-manager 收集的 MAC 寫入 phpIPAM
- 自動更新 IP 地址記錄的 `mac` 欄位
- 找出 phpIPAM 中未登錄的活動設備

---

## 📁 建議部署路徑

```
# 生產環境 (stwphpipam-p)
/opt/tools/mac-manager/

# 或沿用現有結構
/home/sysadmin/mac-manager/
```

建議將維運腳本統一放在 `/opt/tools/` 下，與 Docker 容器內的 phpIPAM 分離。
