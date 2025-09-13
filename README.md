# 2025ShortSemesterProject
# AI 旅行计划 Agent ✈️

这是一个基于大语言模型（LLM）的智能旅行计划 Agent。它可以根据用户的个性化需求，自动生成一份详尽、合理、图文并茂的旅行计划。

本项目是 2025 短学期课程《人工智能工程实践》的大作业。

## 核心功能

- **个性化输入**: 用户可以提供目的地、旅行天数以及兴趣偏好（如“喜欢动漫和美食”）。
- **智能行程规划**: Agent 能理解用户需求，并调用外部工具（如地图API）来获取真实的景点和餐厅信息。
- **优化路线**: 自动将地理位置相近的地点规划在同一天，避免行程奔波。
- **结构化输出**: 生成一份清晰的每日行程单（Day-by-Day Itinerary），包含活动、餐饮和交通建议。

## 技术架构

本项目采用以 LLM 为核心的 Agent 架构，主要技术栈如下：

- **语言模型 (LLM)**: 支持工具调用（Tool Calling）功能的大模型。
- **Agent 框架**: [LangChain](https://www.langchain.com/)，用于实现 Agent 的核心逻辑（思考、调用工具、整合信息）。
- **外部工具 (APIs)**:
  - **地点搜索**: 高德地图或 Google Maps API，用于查询景点、餐厅等信息。
  - **天气查询**: OpenWeatherMap API（可选），用于提供天气提醒。
- **应用界面 (UI)**: [Streamlit](https://streamlit.io/)，用于快速搭建交互式 Web 界面。
- **编程语言**: Python

## 文件结构

当前仓库包含项目规划文档。根据 [`recommendation.md`](recommendation.md) 中的规划，未来的项目代码结构建议如下：

```
.
├── README.md               # 项目说明
├── recommendation.md       # 初期规划文档
├── requirements.txt        # Python 依赖包
├── app.py                  # Streamlit 应用主程序
├── agent_logic.py          # Agent 核心逻辑
├── tools.py                # 外部 API 工具函数
└── report.pdf              # 项目报告
```

## 如何运行
1.  **实现查车票功能**
   下载node.js:https://nodejs.org/zh-cn
    ```bash
    git clone https://github.com/Joooook/12306-mcp.git
    cd 12306-mcp
    npm i
    ```
2. **实现bilibili搜索功能**
   搭建uv环境：
   ```bash
   pip install uv
   ```
   ```bash
      git clone https://github.com/huccihuang/bilibili-mcp-server.git
      cd bilibili-mcp-server
      uv sync
   ```
   修改agent_logic中的servers_config["flight-ticket-server"]：
   把args的第二个改为你的bilibili-mcp-server文件夹的路径
3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **配置 API Keys**:
    在项目中创建 `.env` 文件或配置环境变量，填入所需的大模型 API Key 和地图 API Key。
5.  **启动应用**:
    ```bash
    streamlit run app.py
    ```

之后在浏览器中打开相应地址即可与旅行 Agent 进行交互。
qwen api: sk-b18d810ab2014f8ebfcd0baff4081540
srap api: 8493d3384132da278652a23b7ffdf1046fcaa4efa682be436bd0af8050bfbb0f
