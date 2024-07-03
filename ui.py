import streamlit as st
import mysql.connector
from mysql.connector import Error
from PyPDF2 import PdfReader
import hashlib
from dotenv import load_dotenv
import os
import streamlit_ace as ace
import io
import contextlib
import matplotlib.pyplot as plt
from openai import OpenAI
from PIL import Image

# 加载环境变量
load_dotenv()

# 获取环境变量
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")  # 管理员用户名
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")  # 管理员密码哈希值

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE
)


def ask(a):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "总结.给出主要财务数据的表格，如果有许多期，则给出和本期的变动浮动"
            },
            {
                "role": "user",
                "content": a
            }
        ],
        temperature=0.8,
    )
    for item in response.choices[0].message:
        if item[0] == 'content':
            st.write(item[1])


def ask3(a):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "给出主要财务数据的图的python代码，并在代码中加入plt.rcParams['font.sans-serif'] = ['Arial Unicode MS'] plt.rcParams['axes.unicode_minus'] = False,只回答代码"
            },
            {
                "role": "user",
                "content": a
            }
        ],
        temperature=0.8,
    )
    for item in response.choices[0].message:
        if item[0] == 'content':
            st.write(item[1])
def ask2(a):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "对该报告进行总结"
            },
            {
                "role": "user",
                "content": a
            }
        ],
        temperature=0.8,
    )
    for item in response.choices[0].message:
        if item[0] == 'content':
            st.write(item[1])

# MySQL数据库连接配置
def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
    except Error as e:
        st.error(f"Error: '{e}'")
    return connection


# 创建数据库连接
conn = create_connection()


# 密码哈希处理函数
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# 用户注册函数
def register_user(username, password):
    hashed_password = hash_password(password)
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        cursor.close()
        return True
    except Error as e:
        st.error(f"Error: '{e}'")
        return False


# 用户登录函数
def login_user(username, password):
    hashed_password = hash_password(password)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed_password))
        result = cursor.fetchone()
        cursor.close()
        return result is not None
    except Error as e:
        st.error(f"Error: '{e}'")
        return False


# 设置页面标题
st.set_page_config(page_title="O.O", page_icon=":smile:", layout="wide")
st.title("报表分析系统")

# 检查用户是否已经登录
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# 检查是否为管理员登录
def is_admin(username, password):
    return username == ADMIN_USERNAME and hash_password(password) == ADMIN_PASSWORD_HASH


# 使用sidebar进行布局
with st.sidebar:
    st.header("   ")
    if not st.session_state.logged_in:
        option = st.selectbox("选择操作", ("登录", "注册"))

        if option == "注册":
            new_user = st.text_input("用户名")
            new_password = st.text_input("密码", type="password")
            if st.button("注册"):
                if register_user(new_user, new_password):
                    st.success("注册成功，请登录")
                else:
                    st.error("注册失败，请重试")

        if option == "登录":
            user = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            login_button = st.button("登录")
            if login_button:
                if login_user(user, password):
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.session_state.is_admin = is_admin(user, password)
                    st.session_state.uploaded_files = []
                    st.experimental_rerun()  # 重新运行以刷新页面显示

                else:
                    st.error("用户名或密码错误")
    else:
        st.success(f"欢迎，{st.session_state.user}")
        # if st.session_state.is_admin:
        #     image = Image.open('1.png')
        #     st.image(image, use_column_width=True)
        if st.button("登出"):
            st.session_state.logged_in = False
            st.experimental_rerun()

# 显示主要内容
if st.session_state.logged_in:
    st.subheader("上传多个PDF文件")
    uploaded_files = st.file_uploader("选择多个PDF文件", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        # 检查文件名，避免重复添加
        uploaded_filenames = [file.name for file in st.session_state.uploaded_files]
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in uploaded_filenames:
                st.session_state.uploaded_files.append(uploaded_file)

    if st.session_state.uploaded_files:
        with st.expander("浏览已上传的PDF文件"):
            selected_file = st.selectbox("选择一个PDF文件进行浏览", st.session_state.uploaded_files,
                                         format_func=lambda x: x.name)

            if selected_file:
                reader = PdfReader(selected_file)
                number_of_pages = len(reader.pages)
                st.write(f"{selected_file.name} 文件包含 {number_of_pages} 页")

                all_selected = st.checkbox("全选所有页", value=False)
                selected_pages = st.multiselect("选择要显示的页码", range(1, number_of_pages + 1),
                                                disabled=all_selected)

                if all_selected:
                    selected_pages = list(range(1, number_of_pages + 1))

                if len(selected_pages) > 20:
                    st.error("选择页数不能超过20页")
                else:
                    cont = [reader.pages[i - 1].extract_text() for i in selected_pages]
                    if selected_pages:
                        st.write("选择的页数：", selected_pages)
                        for page_text in cont:
                            st.text_area(label="", value=page_text, height=200, max_chars=None)

    if st.session_state.logged_in and st.session_state.uploaded_files:
        with st.expander("选择页数进行总结并绘制图表"):
            selected_summary_file = st.selectbox("选择一个PDF文件进行总结和绘表", st.session_state.uploaded_files,
                                                 format_func=lambda x: x.name)

            if selected_summary_file:
                summary_reader = PdfReader(selected_summary_file)
                summary_number_of_pages = len(summary_reader.pages)
                st.write(f"{selected_summary_file.name} 文件包含 {summary_number_of_pages} 页")

                summary_all_selected = st.checkbox("全选所有页进行总结", value=False, key="summary_all_selected")
                summary_selected_pages = st.multiselect("选择要总结的页码", range(1, summary_number_of_pages + 1),
                                                        disabled=summary_all_selected)

                if summary_all_selected:
                    summary_selected_pages = list(range(1, summary_number_of_pages + 1))

                if len(summary_selected_pages) > 20:
                    st.error("选择页数不能超过20页")
                else:
                    summary_cont = [summary_reader.pages[i - 1].extract_text() for i in summary_selected_pages]
                    if summary_selected_pages:
                        st.write("选择的页数：", summary_selected_pages)

                if st.button("总结财务数据"):
                    if len(summary_selected_pages) > 0 and len(summary_selected_pages) <= 20:
                        with st.spinner('正在处理，请稍候...'):
                            ask("\n".join(summary_cont))
                    else:
                        st.error("请先选择页码，且选择页数不能超过20页")
                if st.button("总结报告"):
                    if len(summary_selected_pages) > 0 and len(summary_selected_pages) <= 20:
                        with st.spinner('正在处理，请稍候...'):
                            ask2("\n".join(summary_cont))
                    else:
                        st.error("请先选择页码，且选择页数不能超过20页")
                if st.button("手动画图"):
                    if len(summary_selected_pages) > 0 and len(summary_selected_pages) <= 20:
                        with st.spinner('正在处理，请稍候...'):
                            ask3("\n".join(summary_cont))
                    else:
                        st.error("请先选择页码，且选择页数不能超过20页")

    if st.session_state.is_admin:
        with st.expander("输入Python代码并执行"):
            code = ace.st_ace(language='python', theme='monokai', keybinding='vscode', font_size=14, tab_size=4,
                              show_gutter=True,
                              wrap=True, show_print_margin=True, auto_update=True)

            if st.button("执行代码"):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    try:
                        exec_globals = {}
                        exec(code, exec_globals)
                        st.success("代码执行成功")
                    except Exception as e:
                        st.error(f"代码执行出错: {e}")
                st.subheader("代码输出")
                st.text(output.getvalue())

                # 如果代码中有生成图像的内容，显示图像
                if "plt" in exec_globals:
                    fig = exec_globals["plt"].gcf()  # 获取当前的Figure
                    st.pyplot(fig)


