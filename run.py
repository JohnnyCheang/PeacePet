# run.py
from waitress import serve
from app import app
    
# 生产环境，关闭 Debug 模式
if __name__ == '__main__':
    print("PeacePet CMS 生产环境启动中...")
    # waitress 是生产级服务器
    serve(app, host='0.0.0.0', port=5000)