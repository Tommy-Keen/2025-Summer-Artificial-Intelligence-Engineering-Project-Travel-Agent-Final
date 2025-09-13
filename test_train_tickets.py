# test_train_tickets.py
# test_train_tickets.py
import requests

def search_train_tickets(from_city: str, to_city: str, date: str) -> str:
    url = "http://127.0.0.1:8080/mcp"  # MCP 服务地址
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json,text/event-stream"
    }

    # 1. 获取车站编码
    payload_station = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "get-station-code-of-citys",
        "params": {"cities": f"{from_city}|{to_city}"}
    }
    res_station = requests.post(url, json=payload_station, headers=headers, timeout=10).json()
    print("车站编码返回:", res_station)

    if "error" in res_station:
        return f"获取车站编码失败: {res_station['error']}"

    from_code = res_station["result"].get(from_city, {}).get("station_code")
    to_code = res_station["result"].get(to_city, {}).get("station_code")

    if not from_code or not to_code:
        return f"无法找到 {from_city} 或 {to_city} 的车站编码"

    # 2. 查询余票
    payload_ticket = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "get-tickets",
        "params": {"from_station": from_code, "to_station": to_code, "date": date}
    }
    res_ticket = requests.post(url, json=payload_ticket, headers=headers, timeout=15).json()
    print("车票信息返回:", res_ticket)

    trains = res_ticket.get("result", [])
    if not trains:
        return f"{date} 从 {from_city} 到 {to_city} 没有车票信息。"

    formatted = []
    for train in trains:
        seats_info = ', '.join([f"{k}:{v}" for k, v in train.get("seats", {}).items()])
        formatted.append(
            f"🚆 {train['train_no']} | {train['from_station']} → {train['to_station']} | "
            f"{train['start_time']} - {train['arrive_time']} | 历时 {train['duration']} | 座位: {seats_info}"
        )
    return "\n".join(formatted)


if __name__ == "__main__":
    from_city = "北京"
    to_city = "上海"
    date = "2025-04-15"

    print("======= 开始测试查询 12306 车票 =======")
    result = search_train_tickets(from_city, to_city, date)
    print(result)