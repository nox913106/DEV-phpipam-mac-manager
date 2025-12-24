#!/usr/bin/env python3
"""
SNMP ARP 表收集器
從網路設備收集 ARP 表中的 IP-MAC 對應關係
重構自 GetMAC_V6.py
"""

import subprocess
import re
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
import logging

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import is_zero_mac, normalize_mac, ensure_dir


class SNMPCollector:
    """SNMP ARP 表收集器"""
    
    # ARP 表 OID (ipNetToMediaPhysAddress)
    DEFAULT_OID = "1.3.6.1.2.1.4.22.1.2"
    
    def __init__(
        self,
        communities: List[str],
        device_ips: List[str],
        oid: str = DEFAULT_OID,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化收集器
        
        Args:
            communities: SNMP community strings 清單
            device_ips: 要掃描的設備 IP 清單
            oid: SNMP OID（預設為 ARP 表）
            logger: Logger 物件
        """
        self.communities = communities
        self.device_ips = device_ips
        self.oid = oid
        self.logger = logger or logging.getLogger(__name__)
    
    def _run_snmpwalk(self, device_ip: str) -> Optional[str]:
        """
        對單一設備執行 snmpwalk，依序嘗試不同的 community
        
        Args:
            device_ip: 設備 IP
        
        Returns:
            SNMP 輸出，若全部失敗則返回 None
        """
        for community in self.communities:
            command = ['snmpwalk', '-v', '2c', '-c', community, device_ip, self.oid]
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.stdout:
                    self.logger.debug(f"{device_ip}: 使用 community '{community}' 成功")
                    return result.stdout
                else:
                    self.logger.debug(f"{device_ip}: community '{community}' 無回應")
            except subprocess.TimeoutExpired:
                self.logger.warning(f"{device_ip}: community '{community}' 逾時")
            except Exception as e:
                self.logger.error(f"{device_ip}: 執行錯誤 - {e}")
        
        self.logger.warning(f"{device_ip}: 所有 community 都無法取得資料")
        return None
    
    def _parse_snmp_output(self, snmp_output: str) -> List[Tuple[str, str]]:
        """
        解析 SNMP 輸出，提取 IP-MAC 對應
        
        Args:
            snmp_output: snmpwalk 的輸出
        
        Returns:
            [(IP, MAC), ...] 清單
        """
        # 匹配格式：iso.3.6.1.2.1.4.22.1.2.{介面}.{IP} = Hex-STRING: XX XX XX XX XX XX
        pattern = re.compile(
            r"iso\.3\.6\.1\.2\.1\.4\.22\.1\.2\.(\d+)\.(\d+\.\d+\.\d+\.\d+)\s*=\s*Hex-STRING:\s*(([0-9A-F]{2}\s*){5}[0-9A-F]{2})",
            re.IGNORECASE
        )
        
        results = []
        for match in pattern.finditer(snmp_output):
            ip = match.group(2)
            mac_raw = match.group(3).strip()
            mac = normalize_mac(mac_raw.replace(" ", ":"))
            
            # 過濾全零 MAC
            if not is_zero_mac(mac):
                results.append((ip, mac))
        
        return results
    
    def collect(self) -> List[Tuple[str, str]]:
        """
        收集所有設備的 ARP 表
        
        Returns:
            去重排序後的 [(IP, MAC), ...] 清單
        """
        all_records: List[Tuple[str, str]] = []
        
        for device_ip in self.device_ips:
            self.logger.info(f"掃描設備: {device_ip}")
            snmp_output = self._run_snmpwalk(device_ip)
            
            if snmp_output:
                records = self._parse_snmp_output(snmp_output)
                self.logger.info(f"{device_ip}: 找到 {len(records)} 筆 IP-MAC 記錄")
                all_records.extend(records)
            else:
                self.logger.warning(f"{device_ip}: 無法取得資料")
        
        # 去重並排序
        unique_records = sorted(set(all_records), key=lambda x: x[0])
        self.logger.info(f"總計: {len(unique_records)} 筆唯一記錄")
        
        return unique_records
    
    def save_to_csv(
        self,
        records: List[Tuple[str, str]],
        output_dir: Path,
        include_header: bool = True
    ) -> Path:
        """
        將記錄儲存為 CSV 檔案
        
        Args:
            records: [(IP, MAC), ...] 清單
            output_dir: 輸出目錄
            include_header: 是否包含 header 列
        
        Returns:
            輸出檔案路徑
        """
        ensure_dir(output_dir)
        
        current_datetime = datetime.now().strftime("%Y%m%d-%H%M")
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = output_dir / f"mac_addresses_{current_datetime}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if include_header:
                writer.writerow(['IP', 'MAC', 'Date'])
            for ip, mac in records:
                writer.writerow([ip, mac, current_date])
        
        self.logger.info(f"已儲存至: {filename}")
        return filename


def collect_arp(
    communities: List[str],
    device_ips: List[str],
    output_dir: Path,
    logger: Optional[logging.Logger] = None
) -> Path:
    """
    便利函數：收集 ARP 表並儲存
    
    Args:
        communities: SNMP community strings
        device_ips: 設備 IP 清單
        output_dir: 輸出目錄
        logger: Logger 物件
    
    Returns:
        輸出檔案路徑
    """
    collector = SNMPCollector(communities, device_ips, logger=logger)
    records = collector.collect()
    return collector.save_to_csv(records, output_dir)
