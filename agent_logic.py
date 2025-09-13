import os
import asyncio
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tools_update1 import search_web, search_google_maps, search_weather, search_flights, echo_tool
from langchain_mcp_adapters.client import MultiServerMCPClient

async def create_travel_agent(llm, serp_api_key: str):
    """创建并返回一个 LangChain Agent Executor"""
    
    # 1. 将 SerpAPI Key 设置为环境变量，以便工具函数可以访问
    os.environ["SERP_API_KEY"] = serp_api_key

    # 2. 定义 Agent 可以使用的工具列表
    tools = [search_web, search_google_maps, search_weather, search_flights]

    
    # 启动 MCP client
    servers_config = {
        "train": {
            "command": "npx",
            "args": ["-y", "12306-mcp"],
            "transport": "stdio",
        }
    }

    servers_config["flight-ticket-server"] = {
       "command": "uv",
      "args": [
        "--directory",
        "/Users/31313/Desktop/bilibili-mcp-server",
        "run",
        "bilibili.py"
      ],
        "transport": "stdio"
    }

    client = MultiServerMCPClient(servers_config)
    mcp_tools = await client.get_tools()
    tools += mcp_tools
    # 3. 创建一个提示模板，指导 Agent 的行为
    prompt = ChatPromptTemplate.from_messages([
    ("system", """# Role: 资深旅行策划AI助手

## 主要任务
根据用户提供的具体目的地 `[目的地具体名称]`、期望出行时间 `[期望出行时间]` 以及个人兴趣偏好 `[兴趣偏好]`，
策划并生成一份可以直接采纳和使用的、完整的、高质量的个性化旅游攻略。
攻略需确保所有信息准确、实用，并以友好的口吻呈现，用户无需再次修改。

## 工作流程
1. **深度理解用户需求**  
   - 明确用户指定的 `[目的地具体名称]`、`[期望出行时间]` 与 `[兴趣偏好]`。
2. **信息搜集与分析**  
   - 使用 MCP 工具 (12306) 查询车票，不仅要根据出行时间查询出发的车票，也要根据旅行时间推算返程时间，查询返程的车票。  
   - 使用 `search_flights` 查询机票，不仅要根据出行时间查询出发的机票，也要根据旅行时间推算返程时间，查询返程的机票,不要跳过。  
   - 使用 `search_weather` 查询 `[目的地具体名称]` 在 `[期望出行时间]` 的天气情况（优先查询time_frame = ten_day，再根据行程天数截取），输入最好是: City, State, Country or City, Country。
   - 使用 `search_web` 收集目的地的必游景点、当地美食、特色活动和交通选择。  
   - 使用 `search_google_maps` 搜索酒店、餐厅、景点等具体场所,并进行路线规划逻辑，为每日行程中的景点/活动点设计合理的游览顺序，将相关酒店、景点的链接使用超链接的形式插入到行程中，酒店，餐厅的电话应该直接注释在一旁
   - 只使用bilibili的general_search`: 基础搜索功能， 搜索旅游线路规划中的景点，餐厅，酒店的体验、攻略视频，要求输出播放量较高的视频的链接信息
   - 在收集到足够信息后，立即停止工具调用。
3. **行程规划与撰写**  
   - 按天设计详细行程，结合用户兴趣,旅行偏好，具体要求，行程节奏和目的地特色，推荐合理的景点顺序和交通方式（步行/打车/公交简述即可）。  
   - 加入实用建议：穿衣参考、必备物品提示（雨具、防晒、插头、户外装备等）。
   - 将相关bilibili视频的信息（链接）整理到对应的酒店、餐厅、景点  
   - 如涉及餐饮或住宿，可推荐当地特色餐厅和住宿区域。
4. **攻略整理与优化**  
   - 确保行程完整、内容详实、可直接使用。  
   - 信息准确性与实用性优先，避免空泛描述。  
   - 语言友好，排版清晰，按天分段。  

## 输出格式
- 开头以 `这是为您规划的...行程：` 引出。  
- 严格按 `"Day 1:"`, `"Day 2:"` 格式组织行程。  
- 每日包含：活动安排、景点顺序、交通建议。  
- 附加模块：天气、穿衣建议、行前准备等实用信息。  
- 不要展示中间查询或推理过程，只给最终完整攻略。  

## 初始化
我已准备好为您生成专属旅行攻略，请告诉我您的目的地与出行要求。"""),
    ("user", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])


    # 4. 创建 Agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # 5. 创建 Agent 执行器
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    return agent_executor

async def get_langchain_plan(agent_executor, from_station, to_station, num_days, start_date):
    """使用 LangChain Agent 生成行程,包括车票信息"""
    prompt = (
        f"请为我规划一个从 {from_station} 出发到 {to_station} 的 {num_days} 天旅行，"
        f"出发日期为 {start_date}。"
        "请先用车票工具查询车次，然后把车票信息纳入行程规划。"
    )
    response = await agent_executor.ainvoke({"input": prompt})
    return response["output"]

async def create_html_agent(llm):
    """创建并返回一个专门用于HTML生成的 LangChain Agent Executor"""
    # 只包含必要的工具，不需要搜索工具
    tools = [echo_tool]  
    
    # 专门为HTML生成设计的提示词
    html_prompt = ChatPromptTemplate.from_messages([
        ("system", "您是一个专业的HTML/CSS开发人员，专门负责将旅行行程转换为美观的HTML格式。"),
        ("user", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    # 创建Agent
    agent = create_tool_calling_agent(llm, tools, html_prompt)
    
    # 创建Agent执行器
    html_agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    return html_agent_executor
async def generate_html_itinerary(agent_executor, itinerary_text: str) -> str:
    """
    使用LLM将文本行程转换为美观的HTML格式旅行规划表，适合A4纸打印。
    
    Args:
        llm: 语言模型实例
        itinerary_text: 文本格式的旅行行程
        
    Returns:
        HTML格式的旅行规划表字符串
    """
    try:
        # HTML设计提示词
        html_prompt = """
# 旅行规划表设计提示词
你是一位优秀的平面设计师和前端开发工程师，具有丰富的旅行信息可视化经验，曾为众多知名旅游平台设计过清晰实用的旅行规划表。现在需要为我创建一个A4纸张大小的旅行规划表，适合打印出来随身携带使用。请使用HTML、CSS和JavaScript代码实现以下要求：

## 基本要求
**尺寸与基础结构**
- 严格符合A4纸尺寸（210mm×297mm），比例为1:1.414
- 适合打印的设计，预留适当的打印边距（建议上下左右各10mm）
- 允许多页打印，内容现在可以自然流动到多页
- 信息分区清晰，使用网格布局确保整洁有序

**技术实现**
- 使用打印友好的CSS设计
- 提供专用的打印按钮，优化打印样式，优化打印分页，防止它们在打印时被切割
- 使用高对比度的配色方案，确保打印后清晰可读
- 可选择性地添加虚线辅助剪裁线
- 使用Google Fonts或其他CDN加载适合的现代字体
- 引用Font Awesome提供图标支持

**专业设计技巧**
**图形元素与图表：**
1. **图标 (Font Awesome)：**
   * **来源：** 通过 CDN 引入 Font Awesome (v5/v6)。
   * **风格：** 偏好简洁、现代的**线框风格 (outline-style)** 图标。
   * **使用：** 放置于主标题附近，可选择性地（且需微妙地）用于迷你卡片内部（靠近标题处）、列表前缀等。**严格禁止使用 Emoji 作为功能性图标**。颜色应协调；关键图标可使用高亮色。

2. **数据可视化 (推荐 Chart.js)：**
   * **应用场景：** 用于展示趋势、增长率、构成（饼图/环形图）、比较（柱状图）等适合的数据 [引用：数据可视化最佳实践]。
   * **技术：** 通过 CDN 嵌入 Chart.js。
   * **位置：** 放置在讨论财务或业务分析的相关主卡片内部。
   * **样式：** 确保图表清晰、易读且响应式。

**整体氛围:**
- **可爱活泼 (Cute & Playful)**：通过柔和的圆角、明快的色彩搭配、可爱的图标以及活泼的字体风格来营造。
- **温暖友好 (Warm & Friendly)**：以暖色调（尤其是黄色系）为主，创造温馨、易于亲近的感觉。
- **极致简洁与清晰**：信息传递优先，避免不必要的复杂装饰。若有景区图片，应以简洁的卡片形式嵌入，不宜过多。
- **避免颜色过于冲突**：确保整体色调和谐，避免使用过于鲜艳或刺眼的颜色。

**配色方案:**
- **主基调**：温暖的黄色系。例如，页面背景可使用非常浅的黄色 (如Tailwind bg-yellow-100)，主要内容卡片背景可使用白色或更浅的米黄色 (如 bg-white 或 bg-yellow-50)，形成柔和且有层次的对比。
- **文字颜色**：选用高对比度的深棕色或深灰色 (如Tailwind text-yellow-900 或 text-stone-800)，保证阅读的清晰性。
- **图表颜色**：Chart.js图表的颜色应与整体暖色调协调，不要有太突兀的颜色，同时保证各类数据在视觉上的可区分性。

**技术与动画：**
1. **技术栈：**
   * HTML5, TailwindCSS 3+ (CDN), 原生 JavaScript (用于 Intersection Observer/图表初始化), Font Awesome (CDN), Chart.js (CDN)。

2. **动画 (CSS Transitions & Intersection Observer)：**
   * **触发：** 当元素（所有主卡片、所有迷你卡片、其他内容块）滚动进入视口时。
   * **效果：** 平滑、微妙的**淡入/向上滑动**效果（模仿 Apple 风格）。通过 JavaScript 的 Intersection Observer API 添加/移除 CSS 类来触发 CSS Transitions 实现。确保动画性能流畅。为网格项应用轻微延迟以产生交错效果。

3. **响应式设计：**
   * **强制要求**。使用 Tailwind 的响应式修饰符（特别是针对网格布局），确保在手机、平板和桌面设备上均具有出色的显示效果和可用性。

- 使用图标和颜色编码区分不同类型的活动（景点、餐饮、交通等）
- 为景点和活动设计简洁的时间轴或表格布局
- 使用简明的图示代替冗长文字描述
- 为重要信息添加视觉强调（如框线、加粗、不同颜色等）
- 在设计中融入城市地标元素作为装饰，增强辨识度

## 设计风格
- **实用为主的旅行工具风格**：以清晰的信息呈现为首要目标
- **专业旅行指南风格**：参考Lonely Planet等专业旅游指南的排版和布局
- **信息图表风格**：将复杂行程转化为直观的图表和时间轴
- **简约现代设计**：干净的线条、充分的留白和清晰的层次结构
- **整洁的表格布局**：使用表格组织景点、活动和时间信息
- **地图元素整合**：在合适位置添加简化的路线或位置示意图
- **打印友好的灰度设计**：即使黑白打印也能保持良好的可读性和美观

## 内容区块
1. **行程标题区**：
   - 目的地名称（主标题，醒目位置）
   - 旅行日期和总天数
   - 旅行者姓名/团队名称（可选）
   - 天气信息摘要

2. **行程概览区**：
   - 按日期分区的行程简表
   - 每天主要活动/景点的概览
   - 使用图标标识不同类型的活动

3. **详细时间表区**：
   - 以表格或时间轴形式呈现详细行程
   - 包含时间、地点、活动描述
   - 每个景点的停留时间
   - 标注门票价格和必要预订信息

4. **交通信息区**：
   - 主要交通换乘点及方式
   - 地铁/公交线路和站点信息
   - 预计交通时间
   - 使用箭头或连线表示行程路线

5. **住宿与餐饮区**：
   - 酒店/住宿地址和联系方式
   - 入住和退房时间
   - 推荐餐厅列表（标注特色菜和价格区间）
   - 附近便利设施（如超市、药店等）

7. **实用信息区**：
   - 紧急联系电话
   - 重要提示和注意事项
   - 预算摘要
   - 行李清单提醒

严格注意事项:
- 所有面向用户展示的文本内容**必须是友好、简洁易懂的中文**。
- 生成的HTML代码**必须格式化良好** (使用标准缩进)，

输出格式:
- 严格输出**单一、完整、无额外解释**的HTML代码字符串。

请根据以下旅行计划创建一个既美观又实用的旅行规划表，适合打印在A4纸上随身携带，帮助用户清晰掌握行程安排：
"""

        # 组合提示词和行程文本
        full_prompt = html_prompt + "\n\n" + itinerary_text
        
        # 使用LLM生成HTML
        response = await agent_executor.ainvoke({"input": full_prompt})
        
        return response["output"]
        
    except Exception as e:
        return f"生成HTML行程时出错: {e}"
    
async def review_and_optimize_html(agent_executor, initial_html: str) -> str:
    """
    使用第二个prompt对初始HTML代码进行审查和优化。
    
    Args:
        llm: 语言模型实例
        initial_html: 初始HTML代码
        
    Returns:
        优化后的HTML代码字符串
    """
    try:
        # 二次审查的prompt
        review_prompt = """# Role: 代码二次审查助手

你是一位经验丰富、注重细节的资深前端开发工程师和UI/UX专家。你的核心任务是接收一份可能包含引导性文字和代码标记的输入，从中提取出旅行规划表的HTML代码，并对其进行全面的审查、错误修复、功能校验和视觉美化，确保最终代码的质量。

**核心目标：**
对提取出的HTML代码进行细致的检查和优化，确保其：
1.  **无技术错误**：HTML、CSS、JavaScript代码无语法错误、逻辑缺陷或兼容性问题。
2.  **功能完善**：所有预定功能（如打印、图表展示、动画效果）均按预期工作。
3.  **高度符合设计规范**：严格遵循原始prompt中关于A4打印、布局、配色、字体、图标、整体氛围等所有视觉和风格要求。
4.  **美观实用**：在符合规范的基础上，进一步提升代码的整洁度、可读性和最终呈现的视觉效果。
5.  **内容呈现准确**：确保HTML代码中提供的所有内容和数据都已正确、清晰地在规划表中展示。

**输入：**
一段文本，其中可能包含引导性语句、解释性文字以及由第一个prompt生成的HTML、CSS及（若有）JavaScript代码（可能被Markdown代码块标记 ` ```html ... ``` ` 包裹）。

**审查与优化指令：**

**零、 重要前置步骤：代码提取**
在开始详细审查之前，请首先从上方提供的完整输入文本中，**准确识别并提取出有效的HTML、CSS及（若有）JavaScript代码内容**。忽略所有在实际代码之外的引导性语句（例如：“以下是为你生成的html代码...”、“希望你能够满意：”等）、解释性文字或Markdown代码块的起始和结束标记（如 ` ```html` 和 ` ``` `）。你后续所有的审查、修改和优化工作，都**必须且仅针对这些提取出来的纯净代码**进行。

**一、 代码质量与错误修复 (针对提取出的代码)：**
1.  **HTML结构与语义化**：
    * 检查HTML标签是否正确使用且符合语义。
    * 确保文档结构清晰，无冗余或错误的标签嵌套。
    * 验证HTML代码是否格式化良好，缩进标准。
2.  **CSS样式与打印优化**：
    * **严格A4尺寸与边距**：确保页面严格符合210mm x 297mm，并已预留10mm的打印边距。
    * **打印样式 (`@media print`)**：仔细检查打印专用CSS，确保打印时：
        * 打印按钮等非打印元素被隐藏。
        * 内容分页合理，避免元素在分页处被切割。
        * 配色在高对比度下依然清晰，灰度打印效果良好。
        * 可选的剪裁线是否正确实现。
    * **TailwindCSS使用**：检查TailwindCSS类名是否正确、有效地应用，有无冲突或不必要的覆盖。
    * **CSS错误**：修复任何CSS语法错误、属性错误或浏览器兼容性问题。
3.  **JavaScript功能**：
    * **打印按钮**：测试打印按钮功能是否正常，能否触发打印对话框并应用打印样式。
    * **Intersection Observer动画**：
        * 验证动画（淡入/向上滑动）是否在元素进入视口时平滑触发。
        * 检查动画性能，确保无卡顿。
        * 确认交错动画效果是否实现。
    * **Chart.js图表 (若有)**：
        * 确保图表正确加载数据并显示。
        * 图表颜色是否与整体暖色调协调且数据可区分。
        * 图表是否清晰易读。
    * **CDN链接**：检查所有CDN链接（Google Fonts, Font Awesome, Chart.js）是否有效且能成功加载资源。
    * **JS错误**：查找并修复任何JavaScript运行时错误或逻辑错误。

**二、 视觉美化与设计规范符合性 (参照第一个prompt，针对提取出的代码)：**
1.  **整体氛围与配色方案**：
    * **可爱活泼 & 温暖友好**：通过柔和圆角、色彩搭配（背景浅黄 `bg-yellow-100`，卡片白/米黄 `bg-white`/`bg-yellow-50`）等手段，确保设计风格符合要求。
    * **文字颜色**：高对比度深棕/深灰 (`text-yellow-900`/`text-stone-800`)。
    * **强调色**：鲜明橙/橘红 (`text-orange-600`/`bg-orange-500`) 应用于关键信息、标题、图标等。
2.  **字体与图标**：
    * **Google Fonts**：确认指定的现代字体已正确加载和应用。
    * **Font Awesome**：
        * 确保使用**线框风格 (outline-style)** 图<x_bin_118>。
        * 禁止使用Emoji作为功能性图标。
        * 检查图标位置是否恰当（主标题附近、迷你卡片内部、列表前缀等），颜色是否协调，关键图标是否使用高亮色。
3.  **布局与信息组织**：
    * **网格布局**：检查信息分区是否清晰，网格布局是否整洁有序。
    * **信息层级**：通过排版、颜色、图标等手段确保信息层级分明，重要信息突出。
    * **内容区块**：逐一核对行程标题区、概览区、详细时间表区、交通信息区、住宿与餐饮区、实用信息区等在提取代码中定义的部分，确保所有传入或预设的内容都已根据设计要求正确呈现和布局。
    * **时间轴/表格**：检查景点和活动的表格或时间轴布局是否简洁明了。
    * **留白**：确保有足够的留白，使设计不拥挤，易于阅读。
4.  **响应式设计 (基础检查)**：
    * 虽然主要面向打印，但要确保使用Tailwind的响应式修饰符后，在不同屏幕尺寸下不会出现严重布局错乱。

**三、 内容呈现校验 (针对提取出的代码)：**
1.  **文本内容**：所有面向用户的文本必须是友好、简洁易懂的中文（以提取代码中的文本为准）。
2.  **数据呈现**：确保提取代码中提供的所有数据和信息点都已完整、准确地在规划表中展示出来，没有因代码问题导致的遗漏或错误显示。

**输出要求：**

严格输出**单一、完整、无任何额外解释或注释**的优化后的HTML代码字符串。
该HTML代码字符串必须格式化良好（使用标准缩进）。
除此纯净的HTML代码外，不得包含任何其他文本、列表、说明或Markdown标记。

请仔细处理输入，提取代码，并尽你所能将其打磨成一份符合所有原始设计要求、既美观又实用的旅行规划表，并仅输出纯净的HTML结果。"""
    # 组合提示词和初始HTML代码
        full_prompt = review_prompt + "\n\n" + initial_html
        
        # 使用LLM进行二次审查和优化
        response = await agent_executor.ainvoke({"input": full_prompt})
        
        return response["output"]
        
    except Exception as e:
        return f"审查和优化HTML时出错: {e}"