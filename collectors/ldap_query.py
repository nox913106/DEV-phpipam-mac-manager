#!/usr/bin/env python3
"""
LDAP RADIUS MAC 查詢模組
從 LDAP 伺服器查詢已授權的 MAC 地址
重構自 RadiusMacV2.py
"""

import subprocess
import re
from pathlib import Path
from typing import List, Optional
import logging

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import uid_to_mac, is_valid_mac, ensure_dir


class LDAPQuery:
    """LDAP RADIUS MAC 查詢器"""
    
    def __init__(
        self,
        server: str,
        bind_dn: str,
        password: str,
        base_dn: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化 LDAP 查詢器
        
        Args:
            server: LDAP 伺服器位址（如 ldap://172.16.5.50）
            bind_dn: 綁定 DN
            password: 綁定密碼
            base_dn: 搜尋基底 DN
            logger: Logger 物件
        """
        self.server = server
        self.bind_dn = bind_dn
        self.password = password
        self.base_dn = base_dn
        self.logger = logger or logging.getLogger(__name__)
    
    def _run_ldapsearch(self) -> Optional[str]:
        """
        執行 ldapsearch 命令
        
        Returns:
            命令輸出，若失敗則返回 None
        """
        command = [
            'ldapsearch',
            '-H', self.server,
            '-s', 'sub',
            '-x',
            '-D', self.bind_dn,
            '-w', self.password,
            '-b', self.base_dn,
            'uid=*'
        ]
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                self.logger.error(f"ldapsearch 失敗: {result.stderr}")
                return None
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            self.logger.error("ldapsearch 執行逾時")
            return None
        except FileNotFoundError:
            self.logger.error("找不到 ldapsearch 命令，請確認已安裝 ldap-utils")
            return None
        except Exception as e:
            self.logger.error(f"執行錯誤: {e}")
            return None
    
    def _parse_uids(self, ldap_output: str) -> List[str]:
        """
        從 LDAP 輸出中提取 UID
        
        Args:
            ldap_output: ldapsearch 的輸出
        
        Returns:
            UID 清單
        """
        uids = re.findall(r'uid:\s*(\S+)', ldap_output)
        return uids
    
    def query(self) -> List[str]:
        """
        查詢 LDAP 並返回有效的 MAC 地址清單
        
        Returns:
            排序後的 MAC 地址清單
        """
        self.logger.info(f"連線至 LDAP: {self.server}")
        
        ldap_output = self._run_ldapsearch()
        if not ldap_output:
            self.logger.error("無法取得 LDAP 資料")
            return []
        
        uids = self._parse_uids(ldap_output)
        self.logger.info(f"找到 {len(uids)} 個 UID")
        
        valid_macs = []
        invalid_count = 0
        
        for uid in uids:
            mac = uid_to_mac(uid)
            if is_valid_mac(mac):
                valid_macs.append(mac)
            else:
                invalid_count += 1
                self.logger.debug(f"無效的 MAC 格式: {uid} -> {mac}")
        
        if invalid_count > 0:
            self.logger.warning(f"過濾掉 {invalid_count} 個無效的 MAC 格式")
        
        # 排序並去重
        sorted_macs = sorted(set(valid_macs))
        self.logger.info(f"有效 MAC 數量: {len(sorted_macs)}")
        
        return sorted_macs
    
    def save_to_file(
        self,
        mac_addresses: List[str],
        output_path: Path
    ) -> Path:
        """
        將 MAC 地址儲存到檔案
        
        Args:
            mac_addresses: MAC 地址清單
            output_path: 輸出檔案路徑
        
        Returns:
            輸出檔案路徑
        """
        ensure_dir(output_path.parent)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for mac in mac_addresses:
                f.write(mac + '\n')
        
        self.logger.info(f"已儲存 {len(mac_addresses)} 個 MAC 至: {output_path}")
        return output_path


def query_ldap_macs(
    server: str,
    bind_dn: str,
    password: str,
    base_dn: str,
    output_path: Path,
    logger: Optional[logging.Logger] = None
) -> Path:
    """
    便利函數：查詢 LDAP MAC 並儲存
    
    Args:
        server: LDAP 伺服器位址
        bind_dn: 綁定 DN
        password: 密碼
        base_dn: 基底 DN
        output_path: 輸出檔案路徑
        logger: Logger 物件
    
    Returns:
        輸出檔案路徑
    """
    query = LDAPQuery(server, bind_dn, password, base_dn, logger=logger)
    macs = query.query()
    return query.save_to_file(macs, output_path)
