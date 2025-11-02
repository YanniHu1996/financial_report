import os
import time
from playwright.sync_api import sync_playwright


def download_rendered_html_with_iframe(url, output_file="finance_page_rendered.html"):
    """
    访问页面，找到 ID 为 'ifm' 的 iframe，
    等待 iframe 内部的 'table.finance-report-table' 加载完毕，
    然后保存这个 iframe 内部的 HTML。
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print(f"正在访问主页面 (请稍候...): {url}")
            page.goto(url, timeout=60000, wait_until="load")

            # 1. 找到 iframe
            # 同花顺财经页面的核心内容都在一个ID为 'dataifm' 的iframe里
            iframe_selector = "#dataifm"
            print(f"正在定位 iframe '{iframe_selector}'...")

            # 等待 iframe 元素加载到 DOM 中
            page.wait_for_selector(iframe_selector, timeout=20000)

            # 2. 获取 iframe 的“内容框” (content_frame)
            # 这是 Playwright 操作 iframe 内部的标准方式
            frame = page.frame(name="dataifm")  # 或者 page.frame_locator("#dataifm")
            if not frame:
                print(f"错误：无法找到 ID 为 'dataifm' 的 iframe。")
                return

            print("已成功进入 iframe。")

            # 3. 在 iframe 内部等待您指定的表格加载
            table_selector = "table.finance-report-table"
            print(f"正在 iframe 内部等待 '{table_selector}' 渲染...")

            # 注意：这里我们用 frame.wait_for_selector，而不是 page.wait_for_selector
            frame.wait_for_selector(table_selector, state="visible", timeout=30000)

            print("表格已在 iframe 内渲染！正在获取 iframe 源码...")

            # 4. 获取 iframe 内部的完整 HTML
            rendered_html = frame.content()

            # 5. 保存到文件
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(rendered_html)

            print(f"成功！iframe 渲染后的HTML已保存到: {output_file}")

        except Exception as e:
            print(f"访问或等待元素时发生错误: {e}")
            print("请检查网络、URL或选择器是否正确。")

        finally:
            browser.close()


# --- 执行 ---
if __name__ == "__main__":
    import pandas as pd

    number = 0
    while number != 800:
        number = 0
        for file in ["000905.csv", "000300.csv"]:
            df = pd.read_csv(file)
            for index, row in df.iterrows():
                # fill zero if not 6 digits
                code = str(row["stock_code"])
                if len(code) < 6:
                    code = code.zfill(6)
                name = row["short_name"]
                print(f"Processing stock: {code} - {name}")
                path = f"./html/{name}({code}).html"
                if os.path.exists(path):
                    print(f"File {path} already exists. Skipping download.")
                    continue

                # 随机等待一到两秒，避免请求过快
                time.sleep(1 + 1 * os.urandom(1)[0] / 255)

                target_url = f"https://stockpage.10jqka.com.cn/{code}/finance/"
                download_rendered_html_with_iframe(target_url, output_file=path)

                number += 1
