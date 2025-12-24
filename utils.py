#!/usr/bin/env python3
"""
共用工具函數模組
提供 MAC 地址處理、日誌設定等通用功能
"""

import re
import logging
from typing import Optional
from pathlib import Path


def is_valid_mac(mac: str) -> bool:
    """
    驗證 MAC 地址格式是否正確
    
    Args:
        mac: MAC 地址字串（格式：XX:XX:XX:XX:XX:XX）
    
    Returns:
        是否為有效的 MAC 地址
    """
    pattern = r"^([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})$"
    return re.match(pattern, mac) is not None


def normalize_mac(mac: str) -> str:
    """
    標準化 MAC 地址格式
    
    Args:
        mac: 原始 MAC 地址（可能包含各種分隔符）
    
    Returns:
        標準化的 MAC 地址（小寫，冒號分隔）
    """
    # 移除所有非十六進位字元
    mac_clean = ''.join(filter(lambda c: c.isalnum(), mac))
    
    if len(mac_clean) != 12:
        return mac  # 無法標準化，返回原值
    
    # 轉換為小寫並用冒號分隔
    mac_normalized = ':'.join(mac_clean[i:i+2] for i in range(0, 12, 2))
    return mac_normalized.lower()


def uid_to_mac(uid: str) -> str:
    """
    將 LDAP UID 轉換為 MAC 地址格式
    
    Args:
        uid: LDAP 中的 UID（通常是無分隔符的 MAC）
    
    Returns:
        MAC 地址格式（XX:XX:XX:XX:XX:XX）
    """
    uid_clean = ''.join(filter(str.isalnum, uid))
    mac = ':'.join(uid_clean[i:i+2] for i in range(0, len(uid_clean), 2))
    return mac.lower()


def is_zero_mac(mac: str) -> bool:
    """
    檢查是否為全零的 MAC 地址
    
    Args:
        mac: MAC 地址字串
    
    Returns:
        是否為 00:00:00:00:00:00
    """
    normalized = normalize_mac(mac)
    return normalized == "00:00:00:00:00:00"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    name: str = "mac_manager"
) -> logging.Logger:
    """
    設定日誌系統
    
    Args:
        level: 日誌等級（DEBUG, INFO, WARNING, ERROR）
        log_file: 日誌檔案路徑（可選）
        name: Logger 名稱
    
    Returns:
        設定好的 Logger 物件
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 清除現有的 handlers
    logger.handlers.clear()
    
    # 日誌格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 終端輸出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 檔案輸出（如果指定）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def ensure_dir(path: Path) -> Path:
    """
    確保目錄存在，如不存在則建立
    
    Args:
        path: 目錄路徑
    
    Returns:
        確認存在的目錄路徑
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
