#!/usr/bin/env python3
"""
MAC 地址管理工具
統整 SNMP ARP 收集、LDAP MAC 查詢、月報表產生等功能

使用方式:
    python mac_manager.py collect-arp     # 收集 ARP 表
    python mac_manager.py query-ldap      # 查詢 LDAP MAC
    python mac_manager.py monthly-report  # 產生月報表
    python mac_manager.py compare         # 比對分析
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Set, Optional

from config import load_config
from utils import setup_logging, is_valid_mac
from collectors.snmp_collector import SNMPCollector
from collectors.ldap_query import LDAPQuery
from reports.monthly_report import MonthlyReportGenerator


def cmd_collect_arp(args, config, logger):
    """執行 SNMP ARP 收集"""
    logger.info("開始收集 ARP 表...")
    
    # 檢查設備清單
    device_ips = config.snmp_device_ips
    if args.device_file:
        device_ips = []
        with open(args.device_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    device_ips.append(line)
    
    if not device_ips:
        logger.error("沒有指定設備 IP，請在設定檔或使用 --device-file 指定")
        return 1
    
    logger.info(f"將掃描 {len(device_ips)} 台設備")
    
    collector = SNMPCollector(
        communities=config.snmp_communities,
        device_ips=device_ips,
        oid=config.snmp_oid,
        logger=logger
    )
    
    records = collector.collect()
    
    if records:
        output_file = collector.save_to_csv(records, config.daily_dir)
        logger.info(f"完成！共收集 {len(records)} 筆記錄")
        print(f"輸出檔案: {output_file}")
    else:
        logger.warning("未收集到任何記錄")
    
    return 0


def cmd_query_ldap(args, config, logger):
    """執行 LDAP MAC 查詢"""
    logger.info("開始查詢 LDAP...")
    
    # 檢查必要設定
    if not config.ldap_server:
        logger.error("未設定 LDAP 伺服器，請檢查設定檔")
        return 1
    
    password = config.ldap_password
    if not password:
        logger.error(f"請設定環境變數 {config._config['ldap']['password_env']}")
        return 1
    
    query = LDAPQuery(
        server=config.ldap_server,
        bind_dn=config.ldap_bind_dn,
        password=password,
        base_dn=config.ldap_base_dn,
        logger=logger
    )
    
    macs = query.query()
    
    if macs:
        output_file = query.save_to_file(macs, config.ldap_output)
        logger.info(f"完成！共查詢到 {len(macs)} 個 MAC")
        print(f"輸出檔案: {output_file}")
        
        # 如果指定了複製目標
        if args.copy_to:
            import shutil
            shutil.copy(output_file, args.copy_to)
            logger.info(f"已複製至: {args.copy_to}")
    else:
        logger.warning("未查詢到任何 MAC")
    
    return 0


def cmd_monthly_report(args, config, logger):
    """產生月報表"""
    # 決定年月
    if args.month:
        try:
            date = datetime.strptime(args.month, "%Y-%m")
            year, month = date.year, date.month
        except ValueError:
            logger.error("日期格式錯誤，請使用 YYYY-MM 格式")
            return 1
    else:
        # 預設上個月
        today = datetime.now()
        if today.month == 1:
            year, month = today.year - 1, 12
        else:
            year, month = today.year, today.month - 1
    
    logger.info(f"產生 {year}/{month:02} 月報表...")
    
    generator = MonthlyReportGenerator(
        input_dir=config.daily_dir,
        output_dir=config.monthly_dir,
        logger=logger
    )
    
    output_file = generator.generate(year, month)
    
    if output_file:
        print(f"輸出檔案: {output_file}")
        return 0
    else:
        return 1


def cmd_compare(args, config, logger):
    """比對 ARP 與 LDAP 資料"""
    logger.info("開始比對分析...")
    
    # 讀取 ARP MAC 清單
    arp_file = Path(args.arp_file) if args.arp_file else None
    if not arp_file or not arp_file.exists():
        logger.error(f"ARP 檔案不存在: {arp_file}")
        return 1
    
    # 讀取 LDAP MAC 清單
    ldap_file = Path(args.ldap_file) if args.ldap_file else config.ldap_output
    if not ldap_file.exists():
        logger.error(f"LDAP 檔案不存在: {ldap_file}")
        return 1
    
    # 解析 ARP 檔案（CSV 格式）
    arp_macs: Set[str] = set()
    import csv
    with open(arp_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[0].lower() != 'ip':
                arp_macs.add(row[1].lower())
    
    # 解析 LDAP 檔案（每行一個 MAC）
    ldap_macs: Set[str] = set()
    with open(ldap_file, 'r', encoding='utf-8') as f:
        for line in f:
            mac = line.strip().lower()
            if is_valid_mac(mac):
                ldap_macs.add(mac)
    
    logger.info(f"ARP MAC 數量: {len(arp_macs)}")
    logger.info(f"LDAP MAC 數量: {len(ldap_macs)}")
    
    # 比對
    unauthorized = arp_macs - ldap_macs  # 在網路上但未授權
    unused = ldap_macs - arp_macs  # 已授權但未見活動
    
    print("\n" + "=" * 60)
    print("比對結果")
    print("=" * 60)
    print(f"網路上活動的 MAC: {len(arp_macs)}")
    print(f"LDAP 已授權的 MAC: {len(ldap_macs)}")
    print("-" * 60)
    print(f"⚠️  未授權但在使用: {len(unauthorized)}")
    print(f"📋 已授權但未活動: {len(unused)}")
    print("=" * 60)
    
    # 輸出未授權清單
    if unauthorized and args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 未授權但在網路上活動的 MAC 地址\n")
            for mac in sorted(unauthorized):
                f.write(mac + '\n')
        logger.info(f"未授權清單已儲存至: {output_path}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='MAC 地址管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
    %(prog)s collect-arp                    # 收集 ARP 表
    %(prog)s query-ldap                     # 查詢 LDAP MAC
    %(prog)s monthly-report --month 2024-12 # 產生指定月份報表
    %(prog)s compare --arp arp.csv --ldap ldap.txt
        """
    )
    
    parser.add_argument(
        '-c', '--config',
        help='設定檔路徑（預設: config.yaml）',
        default=None
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='顯示詳細日誌'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # collect-arp 子命令
    parser_arp = subparsers.add_parser('collect-arp', help='收集 SNMP ARP 表')
    parser_arp.add_argument(
        '--device-file',
        help='設備 IP 清單檔案（覆蓋設定檔）'
    )
    
    # query-ldap 子命令
    parser_ldap = subparsers.add_parser('query-ldap', help='查詢 LDAP RADIUS MAC')
    parser_ldap.add_argument(
        '--copy-to',
        help='將結果複製到指定路徑'
    )
    
    # monthly-report 子命令
    parser_report = subparsers.add_parser('monthly-report', help='產生月報表')
    parser_report.add_argument(
        '--month',
        help='指定月份（格式: YYYY-MM），預設上個月'
    )
    
    # compare 子命令
    parser_compare = subparsers.add_parser('compare', help='比對 ARP 與 LDAP 資料')
    parser_compare.add_argument(
        '--arp-file',
        required=True,
        help='ARP CSV 檔案路徑'
    )
    parser_compare.add_argument(
        '--ldap-file',
        help='LDAP MAC 檔案路徑（預設使用設定檔路徑）'
    )
    parser_compare.add_argument(
        '-o', '--output',
        help='未授權 MAC 輸出檔案'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 載入設定
    config = load_config(args.config)
    
    # 設定日誌
    log_level = 'DEBUG' if args.verbose else config.log_level
    logger = setup_logging(level=log_level, log_file=config.log_file)
    
    # 執行對應命令
    commands = {
        'collect-arp': cmd_collect_arp,
        'query-ldap': cmd_query_ldap,
        'monthly-report': cmd_monthly_report,
        'compare': cmd_compare
    }
    
    return commands[args.command](args, config, logger)


if __name__ == '__main__':
    sys.exit(main())
