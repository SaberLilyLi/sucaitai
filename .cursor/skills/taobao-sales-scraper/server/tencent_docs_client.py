# -*- coding: utf-8 -*-
"""Tencent Docs Open API client used by the local FastAPI service."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from runtime_paths import env_path

CREATE_FILE_URL = "https://docs.qq.com/openapi/drive/v2/files"
SPREADSHEET_URL = "https://docs.qq.com/openapi/spreadsheet/v3/files/{file_id}"
SPREADSHEET_BATCH_UPDATE_URL = (
    "https://docs.qq.com/openapi/spreadsheet/v3/files/{file_id}/batchUpdate"
)


def _load_dotenv() -> None:
    """Load local credentials without ever exposing them to the frontend."""
    path = env_path()
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip():
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


_load_dotenv()


def _credentials() -> tuple[str, str, str]:
    client_id = (os.environ.get("TENCENT_DOCS_CLIENT_ID") or "").strip()
    access_token = (os.environ.get("TENCENT_DOCS_ACCESS_TOKEN") or "").strip()
    open_id = (os.environ.get("TENCENT_DOCS_OPEN_ID") or "").strip()
    if not client_id or not access_token or not open_id:
        raise RuntimeError(
            "腾讯文档凭证未配置完整。请检查 server/.env 中的 "
            "TENCENT_DOCS_CLIENT_ID、TENCENT_DOCS_ACCESS_TOKEN、TENCENT_DOCS_OPEN_ID。"
        )
    return client_id, access_token, open_id


def _request(
    url: str,
    *,
    method: str,
    body: bytes | None = None,
    content_type: str = "application/json",
) -> dict[str, Any]:
    client_id, access_token, open_id = _credentials()
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Access-Token": access_token,
            "Client-Id": client_id,
            "Open-Id": open_id,
            "Content-Type": content_type,
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"腾讯文档接口请求失败（HTTP {error.code}）：{body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"无法连接腾讯文档：{error.reason}") from error

    try:
        result = json.loads(body)
    except json.JSONDecodeError as error:
        raise RuntimeError("腾讯文档返回了无法识别的响应。") from error

    return result


def create_spreadsheet(title: str) -> dict[str, Any]:
    """Create an online spreadsheet and return Tencent's response."""
    payload = urllib.parse.urlencode({"title": title, "type": "sheet"}).encode("utf-8")
    result = _request(
        CREATE_FILE_URL,
        method="POST",
        body=payload,
        content_type="application/x-www-form-urlencoded",
    )
    if result.get("ret") not in (0, "0", None):
        raise RuntimeError(result.get("msg") or "腾讯文档创建在线表格失败。")
    return result


def _ensure_success(result: dict[str, Any], action: str) -> None:
    """Tencent APIs use either `ret` or `code`; never treat an error as success."""
    code = result.get("code")
    if code is not None and str(code) != "0":
        raise RuntimeError(result.get("message") or f"腾讯文档{action}失败（code={code}）。")
    ret = result.get("ret")
    if ret is not None and str(ret) != "0":
        raise RuntimeError(result.get("msg") or f"腾讯文档{action}失败（ret={ret}）。")


def create_and_fill_spreadsheet(title: str, rows: list[list[str]]) -> dict[str, Any]:
    """Create a sheet, discover its first worksheet ID, then write one range."""
    created = create_spreadsheet(title)
    data = created.get("data") or {}
    file_id = str(data.get("ID") or data.get("id") or "")
    if not file_id:
        raise RuntimeError("腾讯文档没有返回新建表格的 ID。")

    metadata = _request(SPREADSHEET_URL.format(file_id=urllib.parse.quote(file_id, safe="")), method="GET")
    _ensure_success(metadata, "读取工作表信息")
    sheets = metadata.get("properties") or (metadata.get("data") or {}).get("properties") or []
    if not sheets or not sheets[0].get("sheetId"):
        raise RuntimeError("新建表格中未找到可写入的工作表。")
    sheet_id = str(sheets[0]["sheetId"])

    row_count = len(rows)
    if not row_count or not max((len(row) for row in rows), default=0):
        raise ValueError("没有可导出的商品数据。")
    grid_rows = [
        {"values": [{"cellValue": {"text": str(value)}} for value in row]}
        for row in rows
    ]
    response = _request(
        SPREADSHEET_BATCH_UPDATE_URL.format(file_id=urllib.parse.quote(file_id, safe="")),
        method="POST",
        body=json.dumps({
            "requests": [{
                "updateRangeRequest": {
                    "sheetId": sheet_id,
                    "gridData": {"startRow": 1, "startColumn": 1, "rows": grid_rows},
                }
            }]
        }, ensure_ascii=False).encode("utf-8"),
    )
    _ensure_success(response, "写入表格")
    return {"id": file_id, "title": data.get("title") or title, "url": data.get("url"), "rows": row_count - 1}
