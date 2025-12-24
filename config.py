#!/usr/bin/env python3
"""
設定載入模組
從 YAML 檔案讀取設定，支援環境變數覆蓋
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


class Config:
    """設定管理類別"""
    
    DEFAULT_CONFIG = {
        'snmp': {
            'communities': ['public'],
            'oid': '1.3.6.1.2.1.4.22.1.2',
            'device_ips': []
        },
        'ldap': {
            'server': '',
            'bind_dn': '',
            'password_env': 'LDAP_PASSWORD',
            'base_dn': ''
        },
        'output': {
            'daily_dir': './output/daily',
            'monthly_dir': './output/monthly',
            'ldap_output': './output/ldap_mac.txt'
        },
        'logging': {
            'level': 'INFO',
            'file': ''
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化設定
        
        Args:
            config_path: 設定檔路徑，預設為同目錄下的 config.yaml
        """
        self._config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        
        if config_path is None:
            # 預設使用腳本所在目錄的 config.yaml
            script_dir = Path(__file__).parent
            config_path = script_dir / 'config.yaml'
        else:
            config_path = Path(config_path)
        
        if config_path.exists():
            self._load_from_file(config_path)
        else:
            print(f"警告: 設定檔 {config_path} 不存在，使用預設設定")
    
    def _load_from_file(self, config_path: Path) -> None:
        """從 YAML 檔案載入設定"""
        with open(config_path, 'r', encoding='utf-8') as f:
            file_config = yaml.safe_load(f)
            if file_config:
                self._merge_config(file_config)
    
    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """合併設定，新設定覆蓋預設值"""
        for section, values in new_config.items():
            if section in self._config and isinstance(values, dict):
                self._config[section].update(values)
            else:
                self._config[section] = values
    
    # SNMP 設定
    @property
    def snmp_communities(self) -> List[str]:
        return self._config['snmp']['communities']
    
    @property
    def snmp_oid(self) -> str:
        return self._config['snmp']['oid']
    
    @property
    def snmp_device_ips(self) -> List[str]:
        return self._config['snmp']['device_ips']
    
    # LDAP 設定
    @property
    def ldap_server(self) -> str:
        return self._config['ldap']['server']
    
    @property
    def ldap_bind_dn(self) -> str:
        return self._config['ldap']['bind_dn']
    
    @property
    def ldap_password(self) -> str:
        """從環境變數讀取密碼"""
        env_var = self._config['ldap']['password_env']
        return os.environ.get(env_var, '')
    
    @property
    def ldap_base_dn(self) -> str:
        return self._config['ldap']['base_dn']
    
    # 輸出設定
    @property
    def daily_dir(self) -> Path:
        return Path(self._config['output']['daily_dir'])
    
    @property
    def monthly_dir(self) -> Path:
        return Path(self._config['output']['monthly_dir'])
    
    @property
    def ldap_output(self) -> Path:
        return Path(self._config['output']['ldap_output'])
    
    # 日誌設定
    @property
    def log_level(self) -> str:
        return self._config['logging']['level']
    
    @property
    def log_file(self) -> Optional[str]:
        log_file = self._config['logging'].get('file', '')
        return log_file if log_file else None


def load_config(config_path: Optional[str] = None) -> Config:
    """載入設定的便利函數"""
    return Config(config_path)
