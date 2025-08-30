import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import time as time_module
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wp_crawler.log'),
        logging.StreamHandler()
    ]
)

# ASCII 头图
ASCII_ART = r"""
      /\___/\
     (  ・ω・)   _____ _     _      ____      _
     (  つ  )   |  ___(_)___| |__  / ___|__ _| |_
    (つ/￣)つ   | |_  | / __| '_ \| |   / _` | __|
     U￣U      |  _| | \__ \ | | | |__| (_| | |_
               |_|   |_|___/_| |_|\____\__,_|\__|

     FishCat v1.0 by tniay
     启动     文章爬取...
     反馈QQ：3581738884
"""

def get_user_input():
    print("请选择要爬取的博客平台：")
    print("1. WordPress")
    print("2. Typecho")
    platform_choice = input("请输入选项(1-2): ")
    
    if platform_choice == '1':
        url = input("请输入要爬取的WordPress站点地址: ")
    else:
        url = input("请输入要爬取的Typecho站点地址: ")
        
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url.rstrip('/'), platform_choice

def export_articles(articles, filename):
    """导出文章到CSV或HTML文件"""
    if filename.endswith('.csv'):
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'title', 'time', 'category', 'category_link',
                'content', 'tags', 'thumbnail', 'article_url'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for article in articles:
                writer.writerow(article)
        logging.info(f"成功导出 {len(articles)} 篇文章到 CSV 文件: {filename}")
    elif filename.endswith('.html'):
        with open(filename, 'w', encoding='utf-8') as htmlfile:
            htmlfile.write('<!DOCTYPE html>\n<html>\n<head>\n')
            htmlfile.write('<meta charset="UTF-8">\n')
            htmlfile.write('<title>文章导出</title>\n')
            htmlfile.write('<style>\n')
            htmlfile.write('body { font-family: Arial, sans-serif; }\n')
            htmlfile.write('.article { margin-bottom: 2em; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }\n')
            htmlfile.write('h2 { color: #333; margin-top: 0; }\n')
            htmlfile.write('img { max-width: 100%; height: auto; margin: 10px 0; }\n')
            htmlfile.write('.meta { color: #666; margin: 5px 0; }\n')
            htmlfile.write('.content { line-height: 1.6; }\n')
            htmlfile.write('</style>\n</head>\n<body>\n')
            
            for article in articles:
                htmlfile.write('<div class="article">\n')
                htmlfile.write(f'<h2>{article["title"]}</h2>\n')
                if article['thumbnail']:
                    htmlfile.write(f'<div class="thumbnail">\n')
                    htmlfile.write(f'<img src="{article["thumbnail"]}" alt="缩略图" referrerpolicy="no-referrer">\n')
                    htmlfile.write('</div>\n')
                htmlfile.write(f'<div class="meta"><strong>发布时间:</strong> {article["time"]}</div>\n')
                htmlfile.write(f'<div class="meta"><strong>分类:</strong> {article["category"]}</div>\n')
                htmlfile.write(f'<div class="meta"><strong>标签:</strong> {article["tags"]}</div>\n')
                htmlfile.write(f'<div class="content"><strong>内容:</strong></div>\n')
                htmlfile.write(f'<div class="content">{article["content"].replace("\n", "<br>")}</div>\n')
                htmlfile.write(f'<div class="meta"><a href="{article["article_url"]}" target="_blank" rel="noopener noreferrer">查看原文</a></div>\n')
                htmlfile.write('</div>\n')
            
            htmlfile.write('</body>\n</html>')
        logging.info(f"成功导出 {len(articles)} 篇文章到 HTML 文件: {filename}")
    else:
        logging.error("不支持的导出格式，请使用 .csv 或 .html 扩展名")

def get_article_details(article_url, is_typecho=False):
    try:
        article_resp = requests.get(article_url)
        article_soup = BeautifulSoup(article_resp.text, 'html.parser')
        
        # 获取正文内容 - 扩展Typecho选择器
        content_div = None
        if is_typecho:
            content_div = article_soup.find('div', class_=['post-content', 'entry-content', 'post-body', 'entry-body'])
        else:
            content_div = article_soup.find('div', class_=['entry-content', 'post-content'])
        content = content_div.get_text(separator='\n').strip() if content_div else ''
        
        # 获取标签
        tags_div = article_soup.find('div', class_=['post-tags', 'entry-tags'])
        tags = [a.text.strip() for a in tags_div.find_all('a')] if tags_div else []
        
        # 获取特色图片
        thumbnail_img = article_soup.find('img', class_='wp-post-image')
        thumbnail = thumbnail_img['src'] if thumbnail_img else ''
        
        return {
            'content': content,
            'tags': ', '.join(tags),
            'thumbnail': thumbnail
        }
        
    except Exception as e:
        print(f"获取文章详情失败: {e}")
        return {
            'content': '',
            'tags': '',
            'thumbnail': ''
        }

def detect_platform(soup):
    """检测博客平台类型"""
    # 检查WordPress特征
    if soup.find('meta', {'name': 'generator', 'content': lambda x: 'wordpress' in x.lower()}):
        return 'wordpress'
    
    # 检查Typecho特征
    if soup.find('meta', {'name': 'generator', 'content': lambda x: 'typecho' in x.lower()}):
        return 'typecho'
    
    # 默认返回WordPress
    return 'wordpress'

def crawl_site(base_url, platform=None):
    try:
        articles = []
        page_url = base_url
        page_num = 1
        max_pages = 10  # 最大爬取页数限制
        
        while page_url and page_num <= max_pages:
            logging.info(f"正在处理第 {page_num} 页: {page_url}")
            response = requests.get(page_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取站点标题
            if page_num == 1:
                site_title = soup.find('title')
                if site_title:
                    logging.info(f"站点标题: {site_title.text.strip()}")
                
                # 检测博客平台
                platform = detect_platform(soup)
                logging.info(f"检测到博客平台: {platform.capitalize()}")
            
            # 根据平台选择解析方式
            if platform == 'wordpress':
                # WordPress 特定选择器
                posts = soup.find_all('article', class_='post')
                if not posts:
                    posts = soup.find_all('article', class_=lambda x: x and 'post' in x)
            else:  # typecho
                # Typecho 特定选择器
                posts = soup.find_all(['article', 'div'], class_=[
                    'post', 'type-post', 'post-type-post', 
                    'post-item', 'entry', 'post-list-item',
                    'blog-post', 'article-item', 'content-item'
                ])
                # Typecho 特定元数据位置
                if not posts:
                    # 尝试匹配 Typecho 常见结构
                    posts = soup.select('div.post, div.entry, article.post, article.entry')
            
            post_count = len(posts)
            logging.info(f"找到 {post_count} 篇文章")
            logging.info(f"正在爬取，预计需要 {post_count} 秒...")

            for article in posts:
                # 获取基本信息 - 扩展Typecho选择器
                title = article.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], class_=[
                    'post-title', 'entry-title', 'article-title',
                    'title', 'post-heading', 'entry-heading'
                ])
                if not title:
                    title = article.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    
                post_time = article.find(['time', 'div', 'span'], class_=[
                    'post-date', 'date', 'entry-date', 
                    'post-meta-date', 'meta-date', 'time'
                ])
                
                # 处理分类信息
                category = None
                meta = article.find(['div', 'span'], class_=[
                    'post-meta', 'entry-meta', 
                    'post-category', 'entry-category',
                    'meta', 'post-info'
                ])
                if meta:
                    category = meta.find('a', href=True)
                    if not category:
                        category = meta.find(['span', 'div'], class_=['category', 'cat'])
                
                # 获取文章链接 - 扩展Typecho选择器
                article_link = article.find('a', class_=['post-title-link', 'entry-title-link', 'post-link', 'entry-link'])
                if not article_link:
                    article_link = article.find('a', href=True)
                full_url = urljoin(base_url, article_link['href']) if article_link else ''
                
                # 获取文章详情 - 添加Typecho特定解析
                details = {}
                if full_url:
                    if platform == 'typecho':
                        details = get_article_details(full_url, is_typecho=True)
                    else:
                        details = get_article_details(full_url)
                
                article_data = {
                    'title': title.text.strip() if title else '无标题',
                    'time': post_time.text.strip() if post_time else '无日期',
                    'category': category.text.strip() if category else '无分类',
                    'category_link': category['href'] if category else '',
                    'article_url': full_url,
                    **details
                }
                articles.append(article_data)
                
                # 立即显示爬取到的文章信息
                print(f"\n文章 {len(articles)}:")
                print(f"标题: {article_data['title']}")
                print(f"发布时间: {article_data['time']}")
                print(f"分类: {article_data['category']}")
                
                # 礼貌爬取，避免过快请求
                time_module.sleep(1)
        
            # 查找下一页链接
            next_page = None
            if platform == 'wordpress':
                next_page = soup.find('a', class_='next page-numbers')
            else:  # typecho
                # 尝试多种方式查找下一页链接
                next_page = soup.find('a', class_=['next', 'page-next', 'nav-next', 'pagination-next'])
                if not next_page:
                    next_page = soup.find('a', text=lambda x: x and any(
                        t in x.lower() for t in ['next', '下一页', '下页', '>', '»']
                    ))
                if not next_page:
                    # 查找包含页码的链接
                    page_links = soup.find_all('a', href=True)
                    current_page_num = page_num
                    for link in page_links:
                        try:
                            link_num = int(link.text.strip())
                            if link_num == current_page_num + 1:
                                next_page = link
                                break
                        except ValueError:
                            continue
            
            if next_page:
                page_url = urljoin(base_url, next_page['href'])
                page_num += 1
            else:
                page_url = None
                
        logging.info(f"成功爬取 {len(articles)} 篇文章")
        return articles
            
    except requests.exceptions.RequestException as e:
        print(f"爬取失败: {e}")
        return []

if __name__ == "__main__":
    print(ASCII_ART)
    logging.info("博客爬虫 v1.0 启动")
    site_url, platform_choice = get_user_input()
    print(f"\n开始爬取: {site_url}")
    articles = crawl_site(site_url, platform_choice)
    
    if articles:
        print("\n请选择导出格式：")
        print("1. 保存为CSV")
        print("2. 保存为HTML") 
        print("3. 保存为TXT")
        print("4. 同时保存为CSV和HTML")
        print("5. 同时保存为CSV和TXT")
        print("6. 同时保存为HTML和TXT")
        print("7. 不保存")
        
        choice = input("请输入选项(1-7): ")
        base_name = input("请输入导出文件名前缀（默认：articles）：") or "articles"
        
        if choice in ['1', '4', '5']:
            export_articles(articles, f"{base_name}.csv")
        if choice in ['2', '4', '6']:
            export_articles(articles, f"{base_name}.html")
        if choice in ['3', '5', '6']:
            with open(f"{base_name}.txt", 'w', encoding='utf-8') as f:
                for article in articles:
                    f.write(f"标题: {article['title']}\n")
                    f.write(f"发布时间: {article['time']}\n")
                    f.write(f"分类: {article['category']}\n")
                    f.write(f"内容:\n{article['content']}\n")
                    f.write("\n" + "="*50 + "\n")
            logging.info(f"成功导出 {len(articles)} 篇文章到 TXT 文件: {base_name}.txt")
