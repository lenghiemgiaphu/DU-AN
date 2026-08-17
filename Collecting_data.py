#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrape danh mục thuốc từ dav.gov.vn (tra-cuu-thuoc), trang 1 -> 243.

Cài đặt trước khi chạy:
    pip install requests beautifulsoup4 lxml

Cách chạy:
    python scrape_dav_thuoc.py

Kết quả:
    - thuoc_data.csv.gz   -> file nén cuối cùng, dung lượng nhỏ nhất, mở được
                             bằng Excel (giải nén trước) hoặc pandas.read_csv trực tiếp.
    - checkpoint.json     -> file tạm lưu tiến trình, để nếu bị đứt giữa chừng
                             (mất mạng, bị chặn...) thì chạy lại script sẽ tự
                             tiếp tục từ trang còn dang dở, không cào lại từ đầu.

Lưu ý:
    - robots.txt của dav.gov.vn không cho phép bot tự động truy cập, nên script
      này chỉ nên dùng cho mục đích cá nhân/nghiên cứu, chạy chậm rãi (có delay
      giữa các request) để không gây tải cho server, không dùng cho mục đích
      thương mại/khai thác hàng loạt.
    - Nếu bị lỗi 403/429 liên tục, hãy tăng DELAY_SECONDS lên hoặc tạm dừng.
"""

import csv
import gzip
import json
import os
import time
import random

import requests
from bs4 import BeautifulSoup

BASE_FIRST_PAGE = "https://dav.gov.vn/tra-cuu-thuoc.html"
BASE_PAGE_FMT = "https://dav.gov.vn/tra-cuu-thuoc-page{}.html"
TOTAL_PAGES = 243

CHECKPOINT_FILE = "checkpoint.json"
RAW_JSONL_FILE = "thuoc_data_raw.jsonl"   # ghi từng dòng ngay khi cào được (an toàn khi bị đứt)
FINAL_CSV_GZ = "thuoc_data.csv.gz"

DELAY_SECONDS = (1.5, 3.0)  # random delay (min, max) giữa các request - lịch sự với server
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_done_page": 0}


def save_checkpoint(page_num):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_done_page": page_num}, f)


def fetch_page(url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            else:
                print(f"  [!] {url} -> HTTP {resp.status_code} (lần {attempt})")
        except requests.RequestException as e:
            print(f"  [!] Lỗi mạng ở {url}: {e} (lần {attempt})")
        time.sleep(2 * attempt)
    return None


def parse_table(html):
    """Trả về (headers, rows) từ <table> đầu tiên chứa dữ liệu thuốc trong trang."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return None, []

    rows = table.find_all("tr")
    if not rows:
        return None, []

    # Dòng đầu coi là header
    header_cells = rows[0].find_all(["th", "td"])
    headers = [c.get_text(strip=True) for c in header_cells]

    data_rows = []
    for tr in rows[1:]:
        cells = tr.find_all("td")
        if not cells:
            continue
        row_vals = [c.get_text(" ", strip=True) for c in cells]
        # Bỏ dòng trống hoàn toàn
        if any(v for v in row_vals):
            data_rows.append(row_vals)

    return headers, data_rows


def main():
    checkpoint = load_checkpoint()
    start_page = checkpoint["last_done_page"] + 1

    if start_page > TOTAL_PAGES:
        print("Đã cào xong toàn bộ trước đó. Chỉ tổng hợp lại file nén cuối cùng...")
        build_final_csv_gz()
        return

    # Mở file jsonl ở chế độ append để không mất dữ liệu cũ khi resume
    mode = "a" if start_page > 1 else "w"
    with open(RAW_JSONL_FILE, mode, encoding="utf-8") as out_f:
        for page_num in range(start_page, TOTAL_PAGES + 1):
            url = BASE_FIRST_PAGE if page_num == 1 else BASE_PAGE_FMT.format(page_num)
            print(f"[{page_num}/{TOTAL_PAGES}] Đang lấy {url}")

            html = fetch_page(url)
            if html is None:
                print(f"  [X] Bỏ qua trang {page_num} sau {MAX_RETRIES} lần thử. "
                      f"Chạy lại script sau để tiếp tục từ trang này.")
                break  # dừng lại, giữ checkpoint ở trang trước đó để lần sau thử lại

            headers, rows = parse_table(html)
            if not rows:
                print(f"  [!] Không tìm thấy dữ liệu bảng ở trang {page_num}")
            else:
                for row in rows:
                    record = {"page": page_num}
                    if headers and len(headers) == len(row):
                        record.update(dict(zip(headers, row)))
                    else:
                        record["cols"] = row
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()
                print(f"  [OK] {len(rows)} dòng")

            save_checkpoint(page_num)
            time.sleep(random.uniform(*DELAY_SECONDS))

    build_final_csv_gz()


def build_final_csv_gz():
    """Đọc file jsonl thô, gộp thành 1 file CSV rồi nén gzip cho gọn."""
    if not os.path.exists(RAW_JSONL_FILE):
        print("Chưa có dữ liệu thô để tổng hợp.")
        return

    records = []
    all_keys = []
    seen_keys = set()

    with open(RAW_JSONL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            records.append(rec)
            for k in rec.keys():
                if k not in seen_keys:
                    seen_keys.add(k)
                    all_keys.append(k)

    if not records:
        print("Không có bản ghi nào.")
        return

    with gzip.open(FINAL_CSV_GZ, "wt", encoding="utf-8-sig", newline="") as gz_f:
        writer = csv.DictWriter(gz_f, fieldnames=all_keys)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)

    size_kb = os.path.getsize(FINAL_CSV_GZ) / 1024
    print(f"\nHoàn tất! Tổng {len(records)} dòng dữ liệu.")
    print(f"File nén cuối cùng: {FINAL_CSV_GZ} ({size_kb:.1f} KB)")
    print("Mở bằng: pandas.read_csv('thuoc_data.csv.gz', compression='gzip')")
    print("Hoặc giải nén thủ công (gunzip / 7-Zip / WinRAR) rồi mở bằng Excel.")


if __name__ == "__main__":
    main()