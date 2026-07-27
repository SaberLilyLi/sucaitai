# -*- coding: utf-8 -*-
"""桌面入口：启动本地 API+前端，并打开系统浏览器。"""
from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# 保证从任意 cwd 启动都能找到同目录模块
SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from runtime_paths import app_root, data_dir, env_path, is_frozen  # noqa: E402

HOST = "127.0.0.1"
PORT = 8787
URL = f"http://{HOST}:{PORT}"


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def _open_browser_when_ready() -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.5):
                webbrowser.open(URL)
                return
        except OSError:
            time.sleep(0.2)
    print(f"[素材台] 服务未在 30s 内就绪，请手动打开 {URL}")


def main() -> None:
    root = app_root()
    data = data_dir()
    data.mkdir(parents=True, exist_ok=True)
    (data / "product_media").mkdir(parents=True, exist_ok=True)

    print(f"[素材台] 工作目录: {root}")
    print(f"[素材台] 数据目录: {data}")
    print(f"[素材台] 配置文件: {env_path()}")
    if is_frozen():
        print("[素材台] 运行模式: 桌面包")
    else:
        print("[素材台] 运行模式: 开发")

    if not _port_free(HOST, PORT):
        print(f"[素材台] 端口 {PORT} 已被占用。")
        print(f"请关闭占用该端口的程序后重试，或直接打开已有服务：{URL}")
        try:
            webbrowser.open(URL)
        except Exception:
            pass
        input("按回车键退出…")
        sys.exit(1)

    # 导入 app 会加载 .env（onebound_client / intent_parser）
    from app import app  # noqa: E402
    import uvicorn

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()
    print(f"[素材台] 正在启动 {URL}")
    print("关闭本窗口即可退出。")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
