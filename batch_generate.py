#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量生成含密图像，支持多个秘密文本和多个公钥提示的组合。
"""

import os
import csv
from stego_working import hide, load_pipe

PRIVATE_IMAGE = "private_cat.jpg"
SECRETS = ["cat", "dog", "hello", "JNU", "secret"]
PROMPTS = [
    "A majestic mountain landscape",
    "A cute cat sitting on a windowsill",
    "A beautiful ocean beach scene",
    "A friendly dog running in a park",
    "A colorful bird perched on a branch",
]
INSTANCES_PER_COMBINATION = 2   # 每个组合生成20张
DELTA = 5.0
OUTPUT_BASE = "RESULT/batch_experiment"

def main():
    load_pipe()
    os.makedirs(OUTPUT_BASE, exist_ok=True)

    metadata_path = os.path.join(OUTPUT_BASE, "metadata.csv")
    with open(metadata_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["image_path", "secret", "prompt", "instance_id"])

    total = 0
    for secret in SECRETS:
        for prompt in PROMPTS:
            safe_secret = secret.replace("/", "_").replace(" ", "_")
            safe_prompt = prompt[:20].replace(" ", "_").replace("/", "_")
            subdir = os.path.join(OUTPUT_BASE, f"{safe_secret}_{safe_prompt}")
            os.makedirs(subdir, exist_ok=True)

            for i in range(1, INSTANCES_PER_COMBINATION+1):
                total += 1
                output_path = os.path.join(subdir, f"instance_{i:04d}.png")
                print(f"\n[{total}] secret='{secret}', prompt='{prompt[:30]}...'")
                try:
                    hide(secret, PRIVATE_IMAGE, prompt, output_path, delta=DELTA)
                except Exception as e:
                    print(f"  生成失败: {e}")
                    continue
                with open(metadata_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([output_path, secret, prompt, i])

    print(f"\n✅ 批量生成完成！共生成 {total} 张含密图像。")
    print(f"元数据文件：{metadata_path}")

if __name__ == "__main__":
    main()