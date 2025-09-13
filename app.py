import streamlit as st
import asyncio
import threading
from langchain_openai import ChatOpenAI
from agent_logic import create_travel_agent, create_html_agent, get_langchain_plan, generate_html_itinerary, review_and_optimize_html
from tools_update1 import generate_ics_content
from datetime import datetime

# ==================== 异步事件循环管理 ====================
# 在一个后台线程中运行独立的事件循环，避免与Streamlit冲突
def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()

# 运行异步函数的辅助工具
def run_async(coro):
    loop = get_or_create_eventloop()
    return loop.run_until_complete(coro)

# ==================== Streamlit UI 设置 ====================
st.set_page_config(page_title="GGGroup AI 旅行计划器", page_icon="✈️", layout="wide")

# 在现有的CSS样式中添加或更新main-title-container的样式
st.markdown("""
    <style>
        /* 背景图片设置 */
        .stApp {
            background-image: url("https://images.unsplash.com/photo-1488646953014-85cb44e25828");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }
        
        /* 主标题容器样式 - 添加动画效果 */
        .main-title-container {
            background: linear-gradient(
                270deg,
                rgba(255, 255, 255, 0.95),
                rgba(255, 255, 255, 0.8),
                rgba(173, 216, 230, 0.8),
                rgba(255, 255, 255, 0.95)
            );
            background-size: 300% 100%;
            animation: gradient-animation 8s ease infinite;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }
        
        .main-title-container:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        }
        
        @keyframes gradient-animation {
            0% {
                background-position: 0% 50%;
            }
            50% {
                background-position: 100% 50%;
            }
            100% {
                background-position: 0% 50%;
            }
        }
        
        /* 其他容器样式保持不变 */
        .element-container, .stForm, .stHeader {
            background-color: rgba(255, 255, 255, 0.85) !important;
            border-radius: 15px !important;
            padding: 20px !important;
            margin: 10px 0 !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
            backdrop-filter: blur(8px) !important;
        }
    </style>
""", unsafe_allow_html=True)
# 创建一个统一的标题容器
st.markdown("""
    <div class="main-title-container">
        <h1 style="margin:0;">GGGroup 的 AI 旅行计划器 ✈️</h1>
        <p style="margin:10px 0 0 0;font-size:1.1em;color:#666;">由大语言模型驱动，为您自动规划个性化行程。</p>
    </div>
""", unsafe_allow_html=True)



# 初始化 session state
if 'agent_executor' not in st.session_state:
    st.session_state.agent_executor = None
if 'html_agent_executor' not in st.session_state:
    st.session_state.html_agent_executor = None
if 'html_agent_executor2' not in st.session_state:
    st.session_state.html_agent_executor2 = None
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = None
if 'final_html' not in st.session_state:
    st.session_state.final_html = None

# ==================== 侧边栏配置 ====================
with st.sidebar:
    st.header("⚙️ 配置")
    with st.expander("API及模型设置", expanded=False):
        model_type = st.selectbox(
            "选择您的 AI 模型:",
            ("OpenAI GPT-4o", "阿里云 Qwen (DashScope)")
        )

        api_key = None
        base_url = None
        model_id = None

        if model_type == "阿里云 Qwen (DashScope)":
            base_url = st.text_input(
                "API 基地址 (Base URL)",
                value="https://dashscope.aliyuncs.com/compatible-mode/v1",
                help="DashScope 提供的与 OpenAI 兼容的 API 地址。"
            )
            api_key = st.text_input("阿里云 DashScope API Key", type="password")
            model_id = "qwen3-coder-plus"
        elif model_type == "OpenAI GPT-4o":
            api_key = st.text_input("输入 OpenAI API Key", type="password")
            model_id = "gpt-4o"

        serp_api_key = st.text_input("输入 Serp API Key (用于网络搜索)", type="password")

    # 初始化 Agent
    if api_key and serp_api_key and not st.session_state.agent_executor:
        try:
            with st.spinner("正在初始化AI Agent..."):
                llm = ChatOpenAI(
                    model=model_id,
                    api_key=api_key,
                    base_url=base_url,
                    temperature=0,
                    streaming=True
                )
                # 使用 run_async 运行异步初始化
                st.session_state.agent_executor = run_async(create_travel_agent(llm, serp_api_key))
                st.session_state.html_agent_executor = run_async(create_html_agent(llm))
                st.session_state.html_agent_executor2 = run_async(create_html_agent(llm))
            st.success("✅ AI Agent 初始化成功！")
        except Exception as e:
            st.error(f"初始化 AI Agent 时出错: {e}")
            st.stop()
    if not st.session_state.agent_executor:
        st.markdown("""
            <div class="config-warning">
                👈 请完成上方API配置以启动Agent
            </div>
        """, unsafe_allow_html=True)

# ==================== 主界面 ====================
if not st.session_state.agent_executor:
    st.stop()

with st.form("travel_form"):
    st.header("📝 填写您的旅行需求")
    
    col1, col2 = st.columns(2)
    with col1:
        from_station = st.text_input("您的出发地", placeholder="例如：上海")
        start_date = st.date_input("出发日期", value=datetime.today())
    with col2:
        to_station = st.text_input("您想去哪里？", placeholder="例如：日本东京")
        num_days = st.number_input("您想旅行多少天？", min_value=1, max_value=30, value=7)

    st.subheader("旅行偏好")
    col3, col4 = st.columns(2)
    with col3:
        travel_style = st.multiselect(
            "旅行风格",
            ["美食", "购物", "历史古迹", "自然风光", "艺术文化", "休闲放松", "冒险运动"],
            placeholder="选择您感兴趣的活动类型"
        )
    with col4:
        trip_pace = st.select_slider(
            "行程节奏",
            options=["悠闲", "常规", "紧凑"],
            value="常规"
        )
    
    specific_requirements = st.text_area(
        "还有什么具体要求吗？",
        placeholder="例如：我带着孩子，希望安排一些亲子活动。预算大概在8000元左右。"
    )

    submit_button = st.form_submit_button("🚀 生成行程", use_container_width=True)

if submit_button:
    if not to_station or not from_station:
        st.warning("请输入出发地和目的地。")
    else:
        st.session_state.itinerary = None
        st.session_state.final_html = None
        
        prompt = (
            f"请为我规划一个从 {from_station} 出发到 {to_station} 的 {num_days} 天旅行，"
            f"出发日期为 {start_date.strftime('%Y-%m-%d')}。"
            f"我的旅行偏好是：{', '.join(travel_style) if travel_style else '无特殊风格'}。"
            f"我希望行程节奏是 '{trip_pace}'。"
            f"其他具体要求：{specific_requirements if specific_requirements else '无'}。"
            "请先用车票或机票工具查询交通信息，然后把这些信息纳入行程规划。"
        )

        with st.spinner("AI Agent 正在思考和规划中..."):
            try:
                response = run_async(st.session_state.agent_executor.ainvoke({"input": prompt}))
                itinerary_text = response["output"]
                st.session_state.itinerary = itinerary_text
            except Exception as e:
                st.error(f"Agent 执行出错: {e}")
                st.stop()
        
        with st.spinner("正在生成精美的HTML报告..."):
            try:
                initial_html = run_async(generate_html_itinerary(st.session_state.html_agent_executor, st.session_state.itinerary))
                final_html = run_async(review_and_optimize_html(st.session_state.html_agent_executor2, initial_html))
                st.session_state.final_html = final_html
            except Exception as e:
                st.error(f"生成HTML文件时出错: {e}")

if st.session_state.itinerary:
    st.header("📅 您的专属行程")
    
    tab1, tab2 = st.tabs(["行程详情 (Markdown)", "可视化报告 (HTML)"])

    with tab1:
        st.markdown(st.session_state.itinerary)
        try:
            ics_content = generate_ics_content(st.session_state.itinerary,  datetime.combine(start_date, datetime.min.time()))
            st.download_button(
                label="📥 下载为日历文件 (.ics)",
                data=ics_content,
                file_name=f"{to_station}_travel_itinerary.ics",
                mime="text/calendar",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"生成日历文件时出错: {e}")

    with tab2:
        if st.session_state.final_html:
            st.components.v1.html(st.session_state.final_html, height=800, scrolling=True)
            st.download_button(
                label="📥 下载HTML行程表 (.html)",
                data=st.session_state.final_html,
                file_name=f"{to_station}_travel_itinerary.html",
                mime="text/html",
                use_container_width=True
            )
        else:
            st.info("正在生成HTML报告，请稍候...")