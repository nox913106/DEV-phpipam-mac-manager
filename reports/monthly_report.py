#!/usr/bin/env python3
"""
月報表產生器
彙整指定月份的所有 MAC 收集記錄，每個 MAC 只保留最新記錄
重構自 MonthReportV3.py
"""

import csv
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
import logging

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import ensure_dir


class MonthlyReportGenerator:
    """月報表產生器"""
    
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化報表產生器
        
        Args:
            input_dir: 每日 CSV 檔案所在目錄
            output_dir: 月報表輸出目錄
            logger: Logger 物件
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.logger = logger or logging.getLogger(__name__)
    
    def _read_csv(self, file_path: Path) -> List[Tuple[str, str, str]]:
        """
        讀取單一 CSV 檔案
        
        Args:
            file_path: CSV 檔案路徑
        
        Returns:
            [(IP, MAC, 日期), ...] 清單
        """
        records = []
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                # 跳過 header 或空行
                if len(row) < 3:
                    continue
                if row[0].lower() == 'ip':  # 跳過 header
                    continue
                # 過濾全零 MAC
                if row[1] != "00:00:00:00:00:00":
                    records.append((row[0], row[1], row[2]))
        return records
    
    def _filter_latest_mac(
        self,
        records: List[Tuple[str, str, str]]
    ) -> List[Tuple[str, str, str]]:
        """
        過濾每個 MAC 只保留最新日期的記錄
        
        Args:
            records: [(IP, MAC, 日期), ...] 清單
        
        Returns:
            過濾後的記錄清單
        """
        latest_records = {}  # {MAC: (IP, date_obj)}
        
        for ip, mac, date_str in records:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                self.logger.warning(f"無效的日期格式: {date_str}")
                continue
            
            if mac not in latest_records or date_obj > latest_records[mac][1]:
                latest_records[mac] = (ip, date_obj)
        
        # 轉換回 (IP, MAC, 日期) 格式
        result = [
            (ip, mac, date_obj.strftime("%Y-%m-%d"))
            for mac, (ip, date_obj) in latest_records.items()
        ]
        
        return result
    
    def generate(
        self,
        year: int,
        month: int,
        include_header: bool = True
    ) -> Optional[Path]:
        """
        產生指定月份的報表
        
        Args:
            year: 年份
            month: 月份
            include_header: 是否包含 header 列
        
        Returns:
            輸出檔案路徑，若無資料則返回 None
        """
        # 搜尋該月份的所有 CSV 檔案
        pattern = str(self.input_dir / f"mac_addresses_{year}{month:02}*.csv")
        files = glob.glob(pattern)
        
        if not files:
            self.logger.warning(f"找不到 {year}/{month:02} 的資料檔案")
            self.logger.debug(f"搜尋路徑: {pattern}")
            return None
        
        self.logger.info(f"找到 {len(files)} 個檔案")
        
        # 讀取所有檔案
        all_records = []
        for file_path in files:
            records = self._read_csv(Path(file_path))
            self.logger.debug(f"{file_path}: {len(records)} 筆記錄")
            all_records.extend(records)
        
        self.logger.info(f"總計讀取 {len(all_records)} 筆記錄")
        
        # 過濾最新記錄
        filtered_records = self._filter_latest_mac(all_records)
        self.logger.info(f"過濾後: {len(filtered_records)} 個唯一 MAC")
        
        # 排序（按 MAC 和日期）
        sorted_records = sorted(filtered_records, key=lambda x: (x[1], x[2]))
        
        # 輸出
        ensure_dir(self.output_dir)
        output_file = self.output_dir / f"Result{year}{month:02}.csv"
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if include_header:
                writer.writerow(['IP', 'MAC', 'Last_Seen'])
            for ip, mac, date in sorted_records:
                writer.writerow([ip, mac, date])
        
        self.logger.info(f"月報表已儲存至: {output_file}")
        return output_file


def generate_monthly_report(
    input_dir: Path,
    output_dir: Path,
    year: int,
    month: int,
    logger: Optional[logging.Logger] = None
) -> Optional[Path]:
    """
    便利函數：產生月報表
    
    Args:
        input_dir: 每日資料目錄
        output_dir: 輸出目錄
        year: 年份
        month: 月份
        logger: Logger 物件
    
    Returns:
        輸出檔案路徑
    """
    generator = MonthlyReportGenerator(input_dir, output_dir, logger=logger)
    return generator.generate(year, month)
