### **第一部分：产品设计 (要做成什么样)**

为了在一周内完成，我们需要聚焦于一个**最小可行产品 (MVP)**。

#### **1. Agent核心功能**

用户输入**目的地、天数、兴趣标签**，Agent输出一份图文并茂、结构清晰的**每日行程单**。

  * **输入 (Input):**

      * `目的地`: 例如 "日本东京"
      * `天数`: 例如 "3天"
      * `兴趣标签`: 例如 "动漫, 美食, 购物, 寺庙" (可以是自然语言描述，如 "我喜欢动漫和吃好吃的")

  * **输出 (Output):**

      * **每日行程 (Day-by-Day Itinerary):**
          * **Day 1:**
              * 上午: [景点A] - [简要介绍]
              * 午餐: [餐厅B] - [特色菜推荐]
              * 下午: [景点C] - [简要介绍]
              * 晚餐: [餐厅D] - [特色]
              * 交通建议: [例如：乘坐JR山手线]
          * **Day 2:** ...
      * **亮点:** 输出的计划应该在地理位置上是合理的，避免用户在一天内东西奔波。

#### **2. Agent的“智能”体现在哪里？**

  * **工具使用 (Tool Use):** Agent不是凭空生成计划，而是能调用外部API来获取真实、最新的信息。
  * **推理与规划 (Reasoning & Planning):**
    1.  **理解需求:** 能从用户的自然语言中解析出核心需求。
    2.  **信息整合:** 将从API获取的多个景点、餐厅信息，根据用户兴趣进行筛选和排序。
    3.  **路线优化:** 将地理位置相近的地点规划在同一天，让行程更合理。

-----

### **第二部分：技术实现与分工 (要怎么做)**

这是你们四人小组需要动手实践的部分。

#### **1. 技术选型 (Tools)**

  * **LLM API:** 任何支持**工具调用 (Tool Calling / Function Calling)** 的大模型API。如果使用百炼平台，就用其提供的模型。
  * **外部工具API (关键):**
      * **地点搜索API (必须):** 这是Agent的眼睛和耳朵。推荐使用 **Google Maps Platform (Places API)** 或国内的 **高德地图开放平台 (Web服务API)**。它可以用来搜索特定地点的“景点”、“餐厅”等。
      * **天气API (可选，但加分):** OpenWeatherMap API。可以在行程中加入天气提醒，例如“第二天可能下雨，建议优先安排室内活动”。
  * **开发框架:**
      * **百炼平台:** 如果平台提供了Agent搭建框架，优先使用，这会大大降低开发难度。
      * **开源框架 (备选):** **LangChain** 或 **LlamaIndex**。这些Python库是专门用来构建LLM应用的，能帮你轻松实现“LLM调用工具”的逻辑。
  * **应用界面 (UI):**
      * **Streamlit** 或 **Gradio**: 这两个都是Python库，可以用几十行代码快速搭建一个Web演示界面，非常适合本次项目。

#### **2. Agent工作流程 (核心逻辑)**

1.  **用户输入:** 用户在Streamlit界面提交旅行需求。
2.  **LLM思考与决策:** LLM接收到需求后，开始思考。
      * *(内心活动)*: “用户想去东京玩3天，喜欢动漫和美食。我需要先找一些东京的动漫圣地和美食地点。”
3.  **调用工具:** LLM决定调用`地点搜索API`，生成调用参数，例如 `search_poi(query="东京 动漫圣地")`。
4.  **执行工具:** 系统执行这个函数，去请求高德或Google地图的API，然后返回一个包含地点列表（如：秋叶原、三鹰之森吉卜力美术馆）的JSON数据。
5.  **LLM整合信息:** LLM接收到工具返回的信息，继续思考。
      * *(内心活动)*: “很好，我找到了一些动漫地点。现在我需要找美食。秋叶原附近有什么好吃的？”
6.  **再次调用工具:** LLM再次决定调用`地点搜索API`，参数为 `search_poi(query="秋叶原附近 美食")`。
7.  **最终生成:** 当LLM认为信息足够时，它会停止调用工具，开始整合所有信息，并根据地理位置的邻近性进行排序，最终生成一份结构化的行程单返回给用户。

#### **3. 具体分工与实现**

**成员A (项目经理 & 后端主力): Agent大脑搭建**

  * **任务:**
    1.  负责定义Agent的核心Prompt，告诉LLM它的角色是“一个聪明的旅行规划师”。
    2.  使用LangChain或百炼平台，搭建Agent的主体框架，实现上面描述的“工作流程”。
    3.  将成员B写的工具函数接入到Agent中，让Agent可以调用它们。
  * **伪代码 (使用LangChain):**
    ```python
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate

    # 成员B提供的工具
    from tools import search_points_of_interest, get_weather

    # 1. 定义LLM和工具
    llm = ChatOpenAI(model="gpt-4o")
    tools = [search_points_of_interest, get_weather]

    # 2. 定义核心Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个聪明的旅行规划助手。请根据用户的需求和工具返回的信息，为用户制定一份详细、合理的旅行计划。"),
        ("user", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # 3. 创建Agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True) # verbose=True能看到Agent的思考过程

    # 4. 运行Agent (供成员C调用)
    def plan_trip(user_request):
        return agent_executor.invoke({"input": user_request})
    ```

**成员B (API技术专家): Agent的工具箱**

  * **任务:**
    1.  去高德/Google地图开放平台注册账号，获取API Key。
    2.  编写Python函数作为Agent的“工具”。每个函数负责调用一个外部API。
    3.  函数要写好类型注解 (type hints) 和文档字符串 (docstring)，这样LLM才能理解这个工具的用途和用法。
  * **伪代码 (一个工具的例子):**
    ```python
    import requests
    from langchain.tools import tool

    # 必须加@tool装饰器，并写好文档字符串
    @tool
    def search_points_of_interest(query: str) -> str:
        """
        根据查询词搜索兴趣点(POI)，如景点、餐厅等。
        例如: '东京的博物馆' 或 '新宿站附近的美食'。
        """
        # 这里是调用高德/Google地图API的代码
        # response = requests.get(f"https://api.map.com/search?query={query}&key=YOUR_API_KEY")
        # return response.json() 
        # 返回处理好的结果字符串
        print(f"---正在搜索: {query}---")
        # 实际项目中，这里会返回API的真实数据
        if "动漫" in query:
            return "找到的动漫圣地有：秋叶原、三鹰之森吉卜力美术馆、中野百老汇。"
        elif "美食" in query:
            return "找到的美食有：一兰拉面、筑地市场、各种居酒屋。"
        return "没有找到相关地点。"
    ```

**成员C (前端/应用框架专家): Agent的用户界面**

  * **任务:**
    1.  使用Streamlit或Gradio搭建一个简单的网页界面。
    2.  界面上应包含输入框（目的地、天数、兴趣）和一个“生成计划”按钮。
    3.  点击按钮后，调用成员A写好的`plan_trip`函数，并将最终生成的行程单优美地展示在页面上。
  * **伪代码 (使用Streamlit):**
    ```python
    import streamlit as st
    # 导入成员A的Agent主函数
    from agent_logic import plan_trip

    st.title("AI 旅行计划 Agent ✈️")

    destination = st.text_input("目的地:", "日本东京")
    days = st.text_input("天数:", "3")
    interests = st.text_area("兴趣和偏好:", "我喜欢动漫和美食，希望行程不要太赶。")

    if st.button("生成我的专属行程"):
        request = f"目的地:{destination}, 天数:{days}, 具体要求:{interests}"
        with st.spinner("您的专属旅行规划师正在为您服务..."):
            result = plan_trip(request)
        
        st.markdown("### ✨ 这是为您生成的旅行计划：")
        st.markdown(result['output'])
    ```

**成员D (报告与pre负责人): 项目的展示者**

  * **任务:**
    1.  从第一天起，记录团队的讨论过程、架构图、遇到的挑战和解决方案。
    2.  负责撰写最终的项目报告，内容包括：
          * **背景与目标:** 解决了什么问题。
          * **实现方式:** 详细介绍你们的技术架构、使用的API、Agent的工作流程。
          * **最终效果:** 截图展示你们的应用界面和几个成功的行程规划案例。
    3.  制作PPT，并准备5-10分钟的演讲稿，清晰地向大家展示你们的项目亮点。

通过这样的分工，你们可以并行工作，大大提高效率，在一周内完成一个令人印象深刻的AI Agent应用。祝你们项目顺利！