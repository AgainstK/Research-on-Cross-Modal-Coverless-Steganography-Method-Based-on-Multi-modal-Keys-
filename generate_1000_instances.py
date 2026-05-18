#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 1000 个含密图像实例（秘密固定为 "cat"）
公钥为文本 prompt，从预定义列表中循环选取。
"""

import os
import csv
from stego_working import hide, load_pipe

PRIVATE_IMAGE = "private_cat.jpg"
SECRET = "JiNanDaXue"
DELTA = 3.5                     # 提高强度
OUTPUT_DIR = "RESULT/1000_instances"
TOTAL_COUNT = 100              # 先测试100张

# 预定义的 prompt 列表（可自行扩充）
PROMPT_LIST = [
    "A majestic mountain landscape",
    "A cute cat sitting on a windowsill",
    "A beautiful ocean beach scene",
    "A friendly dog running in a park",
    "A colorful bird perched on a branch",
    "A serene forest with sunlight",
    "A modern city skyline at sunset",
    "A delicious pizza on a wooden table",
    "A red sports car on a rainy street",
    "A peaceful rural village",
]

def main():
    load_pipe()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 重复 prompt 直到凑够 TOTAL_COUNT
    prompts = (PROMPT_LIST * ((TOTAL_COUNT // len(PROMPT_LIST)) + 1))[:TOTAL_COUNT]
    
    csv_path = os.path.join(OUTPUT_DIR, "instances_metadata.csv")
    # 在循环外部打开文件一次（写模式）
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["instance_id", "prompt", "output_path"])
        
        for i, raw_prompt in enumerate(prompts, start=1):
            prompt = raw_prompt.strip()   # 去除首尾空格
            output_path = os.path.join(OUTPUT_DIR, f"instance_{i:04d}.png")
            print(f"\n[{i}/{TOTAL_COUNT}] prompt: {prompt}")
            try:
                hide(SECRET, PRIVATE_IMAGE, prompt, output_path, delta=DELTA)
            except Exception as e:
                print(f"  生成失败: {e}")
                writer.writerow([i, prompt, f"FAILED: {e}"])
                continue
            
            writer.writerow([i, prompt, output_path])
    
    print(f"\n✅ 生成完成！输出目录: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()