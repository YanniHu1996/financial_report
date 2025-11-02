import os
import time
import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup  # 引入 BeautifulSoup

# 确保你安装了:
# pip install requests
# pip install playwright
# pip install beautifulsoup4
# playwright install

# 伪装成真实浏览器
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def extract_report_urls_from_html(html_file_path):
    """
    从给定的HTML文件中解析出所有财务报告的URL。
    """
    print(f"[Parser] 正在解析HTML文件: {html_file_path}")
    if not os.path.exists(html_file_path):
        print(f"[Parser] 错误: 文件不存在 {html_file_path}")
        return [], None

    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # 提取股票名称
    stock_name = "未知股票"
    title_tag = soup.find("title")
    if title_tag and "(" in title_tag.text:
        stock_name = title_tag.text.split("(")[0].strip()

    reports = []
    # 找到财务报告的表格
    report_table = soup.find("table", class_="finance-report-table")
    if not report_table:
        print("[Parser] 错误: 在HTML中未找到 'finance-report-table'")
        return [], stock_name

    # 季度标题
    headers = [th.text.strip() for th in report_table.find("thead").find_all("th")]

    # 遍历每一行数据
    for row in report_table.find("tbody").find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        year = cells[0].text.strip()
        for i, cell in enumerate(cells[1:]):
            # 从第2个单元格开始是报告
            if i + 1 >= len(headers):
                break

            report_div = cell.find("div", attrs={"data-url": True})
            if report_div:
                shtml_url = report_div["data-url"]
                quarter_name = headers[i + 1]  # 获取对应的季度名
                reports.append(
                    {"year": year, "quarter": quarter_name, "shtml_url": shtml_url}
                )

    print(f"[Parser] 找到 {len(reports)} 份报告. 股票名称: {stock_name}")
    return reports, stock_name


def get_final_pdf_url(shtml_url):
    """
    【Playwright 任务】
    访问 .shtml 链接，并返回它最终重定向到的 URL。
    """
    print(f"[Playwright] 正在访问: {shtml_url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 设置为False可以看到浏览器窗口
        context = browser.new_context(
            user_agent=USER_AGENT, viewport={"width": 64, "height": 36}  # 设置窗口大小
        )
        page = context.new_page()

        try:
            page.goto(shtml_url, timeout=60000, wait_until="load")
            final_url = page.url
            print(f"[Playwright] 导航完成。最终URL: {final_url}")
            return final_url

        except Exception as e:
            print(f"[Playwright] 导航时出错: {e}")
            return None
        finally:
            browser.close()


def download_file_like_curl(pdf_url, output_file):
    """
    【Requests 任务】
    像 curl 一样，直接下载给定的 URL。
    """
    print(f"\n[Requests] 准备下载: {pdf_url}")

    # 确保目录存在
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[FS] 已创建目录: {output_dir}")

    try:
        response = requests.get(
            pdf_url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=60
        )

        if response.status_code == 200:
            total_size = int(response.headers.get("content-length", 0))
            print(f"[Requests] 连接成功。文件大小: {total_size / 1024:.2f} KB")

            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"[Requests] 下载成功！已保存为: {output_file}")
            return True
        else:
            print(f"[Requests] 错误：服务器返回状态码 {response.status_code}")
            return False

    except Exception as e:
        print(f"[Requests] 下载时出错: {e}")
        return False


# --- 执行 ---
if __name__ == "__main__":
    # 获取已经得财报列表
    downloaded_reports = set()
    for file_name in os.listdir("reports"):
        code, name, year, quarter_str = file_name.rstrip(".pdf").rsplit("_", 3)
        downloaded_reports.add((code, year, quarter_str))

    for code, year, quarter_str in downloaded_reports:
        print(f"已存在报告: {code} {year} {quarter_str}")

    # 拿到 html 目录下的所有文件
    html_files = set([file_name for file_name in os.listdir("html")])

    # 读取html目录下的所有文件
    for file_name in html_files:

        # 步骤 1: 指定要解析的HTML文件
        target_html_file = os.path.join("html", file_name)

        code = target_html_file.split("(")[1].split(")")[0]
        name = target_html_file.split("/")[1].split("(")[0]

        # 步骤 2: 从HTML中提取所有报告的URL
        report_infos, stock_name = extract_report_urls_from_html(target_html_file)

        if not report_infos:
            print("\n--- 任务失败：未能从HTML文件中提取到任何报告信息 ---")
            continue

        print(f"\n--- 开始为 '{stock_name}' 下载 {len(report_infos)} 份财务报告 ---")

        # 步骤 3: 遍历并下载每一份报告
        for info in report_infos:
            year = info["year"]
            quarter_str = info["quarter"]
            shtml_link = info["shtml_url"]

            print(f"\n--- 处理报告: {year} {quarter_str} ---")

            # 生成文件名，如 "600754_锦江酒店_2024_一季报.pdf"
            file_name = f"./{code}_{name}_{year}_{quarter_str}.pdf"
            output_path = os.path.join("reports", file_name)

            # 如果文件已存在，则跳过下载
            # 如果 code, year, quarter_str 相同的文件已存在，则跳过下载,
            # 不需要匹配证券名称，因为可能会变动
            print(code, year, quarter_str)
            if (code, year, quarter_str) in downloaded_reports:
                print(f"--- 跳过下载：文件已存在: {output_path} ---")
                continue

            try:
                # 获取真实的PDF下载地址
                real_pdf_url = get_final_pdf_url(shtml_link)
                if real_pdf_url and "pdf" in real_pdf_url:
                    # 延时1到2秒，避免请求过快
                    time.sleep(1 + 1 * os.urandom(1)[0] / 255)

                    # 下载文件
                    download_file_like_curl(real_pdf_url, output_path)
                elif real_pdf_url:
                    print(f"--- 跳过下载：最终URL不是一个PDF文件: {real_pdf_url} ---")
                else:
                    print(f"--- 任务失败：未能从 {shtml_link} 获取到最终的 PDF URL ---")
            except Exception as e:
                print(f"--- 任务失败：处理报告时出错: {e}, 等待20秒 ---")
                # write to error log file
                with open("error_log.txt", "a", encoding="utf-8") as log_file:
                    log_file.write(
                        f"错误处理报告: 股票代码: {code}, 股票名称: {name}, 年份: {year}, 季度: {quarter_str}, 错误: {e}\n"
                    )
                time.sleep(20)
                continue

            print(f"\n--- 处理完成: {name}  {year} {quarter_str} ---")

    print("\n--- 所有下载任务已完成 ---")
