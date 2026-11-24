# 涨潮断面通行簿

内河调度员用潮尺、站点基准和船期表核对放行时间。工作台默认打开断测场次，左侧可依次查看采信、测站归一、阈值交点、全程潮窗、船期覆盖、运行留档和证据签发。

## 启动

```sh
docker compose up --build
```

访问 `http://localhost:18472`。本机也可安装 `requirements.txt` 后执行 `python -m app.main`。留档存入 `TIDE_DB` 指定的 SQLite 库，默认 `var/tide.sqlite3`。清空演示归档时先停止应用，再移除该库或 Compose 命名卷。

## 复核

1. 首页选海棠17，核对 3000 秒窗口中的 1500 秒可行、900 秒不可行、600 秒缺证。
2. 打开全程可行潮窗，查看放行起止、临界点和断面潮尺行。
3. 打开运行留档，复算并保留原归档号，再到潮窗证据签发下载 JSON 或打印。
4. 切换连续测站样例，海棠17的全部 3000 秒均可行。

`GET /api/stage/{readings,datum,crossings,windows,coverage}` 可查看样例阶段结果。对同路径执行 POST 可提交 `{"sources":{"observations":"...","stations":"...","vessels":"..."}}`。`POST /api/journal` 接受同一输入或 `{"sample":"dirty"}`。`GET /api/journal/<id>` 查归档，`POST /api/journal/<id>/rerun` 复算，`GET /api/export/<id>` 下载证据。

## 清淤安排

左侧“清淤安排”（样例 `tide2` 两潮连续、`tide2_dirty` 两潮断测）先列现状两潮各放几条船，再对 `dredging.csv` 的每个候选报断面、开工时刻、工时、增深量及两潮放行数。施工区间过施工断面按封航计，完工才计增深，缺测照旧缺证。`POST /api/dredging/trials` 接受 `{"sample":"tide2"}` 或含 `dredging` 的四原件 `sources`；同源重试沿用原试算号，试算失败不写库、不动运行留档。`GET /api/dredging/trials` 列目录，`GET /api/dredging/trials/<id>` 查单档，`GET /api/stage/dredging?sample=tide2` 看试算阶段结果。

字段见 [数据字典](docs/DATA-DICTIONARY.md)，规则与回归见 [深度登记](docs/DEPTH.md)。本机运行 `python -m pytest -q`。
