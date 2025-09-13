import re
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import requests
import os
import json
from langchain_core.tools import tool
from apify_client import ApifyClient
from typing import List, Dict, Optional

# ==================== ICS 生成函数 ====================
def generate_ics_content(plan_text: str, start_date: datetime = None) -> bytes:
    """
    根据行程文本生成 iCalendar (.ics) 文件内容。
    """
    cal = Calendar()
    cal.add('prodid', '-//AI 旅行计划器//github.com//')
    cal.add('version', '2.0')

    if start_date is None:
        start_date = datetime.today()

    # 匹配 Day X
    day_pattern = re.compile(r'Day (\d+)[:\s]+(.*?)(?=Day \d+|$)', re.DOTALL)
    days = day_pattern.findall(plan_text)

    if not days:
        # 如果没有 Day X 格式，则将整个文本作为单个事件
        event = Event()
        event.add('summary', "旅行行程")
        event.add('description', plan_text)
        event.add('dtstart', start_date.date())
        event.add('dtend', start_date.date())
        event.add("dtstamp", datetime.now())
        cal.add_component(event)
    else:
        for day_num, day_content in days:
            day_num = int(day_num)
            current_date = start_date + timedelta(days=day_num - 1)
            
            event = Event()
            event.add('summary', f"第 {day_num} 天行程")
            event.add('description', day_content.strip())
            event.add('dtstart', current_date.date())
            event.add('dtend', current_date.date())
            event.add("dtstamp", datetime.now())
            cal.add_component(event)

    return cal.to_ical()

# ==================== 搜索工具 ====================
@tool
def search_web(query: str) -> str:
    """
    当你需要回答关于实时事件、地点、活动或任何需要最新信息的问题时，使用此工具进行网络搜索。
    它会返回一个包含搜索结果的字符串。
    """
    api_key = os.environ.get("SERP_API_KEY")
    if not api_key:
        return "错误: SerpAPI Key 未设置。"

    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google",
    }
    url = "https://serpapi.com/search"
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()
        
        snippets = []
        if "organic_results" in results:
            for result in results.get("organic_results", [])[:5]:
                snippet = result.get("snippet", "No snippet available.")
                title = result.get("title", "No title")
                link = result.get("link", "#")
                snippets.append(f"标题: {title}\n链接: {link}\n摘要: {snippet}\n---")
        
        if not snippets:
            return "未找到相关信息。"
            
        return "\n".join(snippets)

    except requests.exceptions.RequestException as e:
        return f"搜索请求失败: {e}"
    except Exception as e:
        return f"处理搜索结果时出错: {e}"

@tool
def search_google_maps(query: str, location: str = None, max_results: int = 5) -> str:
    """
    使用 Apify Google Maps Scraper 搜索特定地点附近的场所，如餐厅、酒店、景点等,搜索次数不要超过15次，搜索到足够信息就停止。
    
    Args:
        query: 搜索查询，如 "restaurant", "hotel", "tourist attraction"
        location: 位置描述，如 "Tokyo, Japan"
        max_results: 返回的最大结果数量
    """
    # 检查 ApifyClient 是否可用
    if ApifyClient is None:
        return "错误: 未安装 apify-client 库。请运行: pip install apify-client"
    
    # 获取 Apify API token
    try:
        # 初始化 ApifyClient
        client = ApifyClient("apify_api_ygFVwzfxBG8h4oUptQtQfi27bihbpi31nJb8")
        
        # 准备 Actor 输入
        run_input = {
            "searchStringsArray": [query],
            "maxCrawledPlacesPerSearch": max_results,
            "language": "zh-CN",
            "searchMatching": "all",
            "website": "allPlaces",
            "skipClosedPlaces": False,
            "scrapePlaceDetailPage": False,
            "includeWebResults": False,
            "maxReviews": 0,
        }
        
        # 添加位置参数（如果提供）
        if location:
            run_input["locationQuery"] = location
        
        # 运行 Actor 并等待完成
        run = client.actor("nwua9Gu5YrADL7ZDj").call(run_input=run_input)
        
        # 获取结果
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            # 格式化每个地点的信息
            place_info = f"名称: {item.get('title', 'N/A')}\n"
            
            if item.get("address"):
                place_info += f"地址: {item['address']}\n"
            
            if item.get("rating"):
                place_info += f"评分: {item['rating']}"
                if item.get("reviewsCount"):
                    place_info += f" ({item['reviewsCount']}条评价)\n"
                else:
                    place_info += "\n"
            
            if item.get("category"):
                place_info += f"类别: {item['category']}\n"
            
            if item.get("phone"):
                place_info += f"电话: {item['phone']}\n"
            
            if item.get("website"):
                place_info += f"网站: {item['website']}\n"
            
            results.append(place_info)
            
            # 如果达到最大结果数，停止迭代
            if len(results) >= max_results:
                break
        
        if results:
            return "\n\n".join(results)
        else:
            return f"未找到与 '{query}' 相关的地点。"
            
    except Exception as e:
        return f"使用 Apify Google Maps 搜索时出错: {e}"
@tool
def search_weather(location: str, time_frame: str = "today", units: str = "metric") -> str:
    """
    使用 Apify Weather Scraper 查询指定地点的天气信息。
    
    Args:
        location: 地点描述，如 "Tokyo, Japan"
        time_frame: 时间范围，可选 ["today", "tomorrow", "ten_day", "weekend", "month"]
        units: 单位，可选 ["metric", "imperial"]
    """
    # 检查 ApifyClient 是否可用
    if ApifyClient is None:
        return "错误: 未安装 apify-client 库。请运行: pip install apify-client"
    
    try:
        # 初始化 ApifyClient
        client = ApifyClient("apify_api_Afc2wYmECLAAY7q1cDq5pNUUtR7zUA3vS1hz")

        # 准备 Actor 输入
        run_input = {
            "locations": [location],
            "timeFrame": time_frame,
            "units": units,
            "maxItems": 5,
            "proxyConfiguration": {"useApifyProxy": True},
        }

        # 运行 Weather Actor
        run = client.actor("utztKy0FeZBtJyhx8").call(run_input=run_input)

        # 获取结果
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            weather_info = f"地点: {location}\n"
            
            if "temperature" in item:
                weather_info += f"温度: {item['temperature']}°{'C' if units=='metric' else 'F'}\n"
            
            if "condition" in item:
                weather_info += f"天气: {item['condition']}\n"
            
            if "humidity" in item:
                weather_info += f"湿度: {item['humidity']}%\n"
            
            if "windSpeed" in item:
                weather_info += f"风速: {item['windSpeed']} {'km/h' if units=='metric' else 'mph'}\n"
            
            if "precipitation" in item:
                weather_info += f"降水概率: {item['precipitation']}%\n"
            
            results.append(weather_info)

        if results:
            return "\n\n".join(results)
        else:
            return f"未找到 {location} 的天气数据。"

    except Exception as e:
        return f"使用 Apify Weather Scraper 搜索时出错: {e}"
@tool
def search_flights(
    origin: str,
    target: str,
    depart: str,
    market: str = "CN",
    currency: str = "CNY",
    max_results: int = 6
) -> str:
    """
    使用 Apify Flight Search 查询单程航班信息。
    """

    try:
        client = ApifyClient("apify_api_ySs6ZKWEBaQ4WdvOv9C4uCjmV00iAM19nX9s")

        run_input = {
            "market": market,
            "currency": currency,
            "origin.0": origin,
            "target.0": target,
            "depart.0": depart,
        }

        run = client.actor("tiveIS4hgXOMtu3Hf").call(run_input=run_input)

        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            legs = item.get("legs", [])
            carriers = item.get("_carriers", {})
            segments = item.get("_segments", {})
            prices = item.get("pricing_options", [])

            for leg in legs:
                seg_ids = leg.get("segment_ids", [])
                for seg_id in seg_ids:
                    seg = segments.get(seg_id, {})
                    carrier_id = str(seg.get("marketing_carrier_id"))
                    carrier_name = carriers.get(carrier_id, {}).get("name", "未知")
                    flight_number = seg.get("marketing_flight_number", "未知")
                    depart_time = seg.get("departure", "未知")
                    arrival_time = seg.get("arrival", "未知")

                    # 取最低票价
                    price = None
                    if prices:
                        amounts = [p["price"].get("amount") for p in prices if "price" in p and "amount" in p["price"]]
                        if amounts:
                            price = min(amounts)

                    flight_info = (
                        f"航空公司: {carrier_name}\n"
                        f"航班号: {flight_number}\n"
                        f"出发时间: {depart_time}\n"
                        f"到达时间: {arrival_time}\n"
                        f"票价: {price} {currency if price else ''}\n"
                    )
                    results.append(flight_info)

                    if len(results) >= max_results:
                        break

            if len(results) >= max_results:
                break

        if results:
            return "\n\n".join(results)
        else:
            return f"未找到从 {origin} 到 {target} 的航班信息。"

    except Exception as e:
        return f"使用 Apify Flight Search 搜索时出错: {e}"

@tool
def echo_tool(x: str) -> str:
    """一个占位工具，不会被调用"""
    return x