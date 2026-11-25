# AI 询盘助手 · Inquiry Agent

把杂乱的询盘（邮件、微信聊天、采购需求）一键变成**结构化数据 + 可直接改用的回复草稿**。

> 零配置即可运行：**不填任何 API Key 也能跑**（内置规则解析），填上大模型 Key 后质量和覆盖面更强。

---

## 为什么做这个

外贸和销售团队每天要处理大量询盘，但它们散落在邮件、微信、PDF 里，格式混乱：

- 靠人一条条读、一条条抄进表格，**重复、易漏、慢**；
- 关键信息（数量、目标价、交期、贸易条款）常常埋在长文本中间，**容易看漏**；
- 回一封邮件要来回找信息，**响应速度直接影响成单**。

这个项目解决的就是这条链路：**读进来 → 抽成结构 → 存下来 → 顺手把回复也草拟好。**

它不是"再做一个聊天机器人"，而是把"重复性信息搬运"这件事自动化掉——这正是业务数字化里最典型、最容易见效的一类问题。

## 它会做什么

```text
粘贴询盘（邮件 / 微信 / 采购单）
        ↓
① 抽取 12 个字段（公司、联系人、国家、产品、数量、目标价、交期、贸易条款、紧急度、意图、摘要、缺失信息）
        ↓
② 落库，形成可筛选的询盘台账
        ↓
③ 基于缺失信息，自动草拟一封中/英回复
        ↓
④ 一键复制，直接发给客户
```

## 界面

> `docs/screenshot.png` 放一张截图即可（自行添加）。左侧粘贴、右侧台账与详情，实时解析。

## 快速开始

需要 Python 3.9+。

### 方式 1：Windows 双击

双击 `start.bat`，自动装依赖并启动。

### 方式 2：命令行

```bash
pip install -r requirements.txt
python run.py
```

打开浏览器访问 **http://127.0.0.1:8000**。

### 方式 3：Docker

```bash
docker build -t inquiry-agent .
docker run -p 8000:8000 inquiry-agent
```

启动后，点页面上的**样例按钮**（英文询价 / 微信群询价 / 中文采购需求）即可立即体验，无需准备数据。

## 可选：接入大模型

不配置也能用。想获得更好的抽取和草拟质量，复制 `.env.example` 为 `.env`，填入任意 OpenAI 兼容接口：

```bash
cp .env.example .env
```

```ini
# DeepSeek 示例
LLM_API_KEY=sk-xxxxxxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

支持 OpenAI / DeepSeek / Kimi / 通义等任何 OpenAI 兼容服务。

## 工作原理

```text
┌──────────────┐     POST /api/inquiries      ┌────────────────┐
│  浏览器前端   │ ───────────────────────────► │   FastAPI 后端  │
│  (原生 JS)    │ ◄─────────────────────────── │                │
└──────────────┘     JSON（询盘 + 草稿）        └───────┬────────┘
                                                       │
                              ┌────────────────────────┼─────────────────────┐
                              ▼                        ▼                     ▼
                     ┌─────────────────┐      ┌─────────────────┐   ┌──────────────┐
                     │  extractor.py   │      │  drafter.py     │   │   db.py      │
                     │ 大模型 or 规则   │      │ 大模型 or 模板   │   │  SQLite 自动建库│
                     └─────────────────┘      └─────────────────┘   └──────────────┘
```

**关键设计：双层降级。**
每个 AI 环节都有"大模型 → 规则/模板"的兜底路径。这样任何人 clone 下来，**不配 Key 也能 100% 跑通全流程**，不会卡在第一步。

## 抽取字段

| 字段 | 含义 | 示例 |
|---|---|---|
| company | 客户公司 | Brightline Trading Co., Ltd |
| contact | 联系人 | Michael Chen |
| country | 国家/地区 | 美国 |
| product | 产品/型号 | LED Panel Light PL-6060 |
| quantity | 数量 | 5,000 pcs |
| target_price | 目标价 | USD 8.5 |
| delivery | 交期 | 30 days |
| incoterm | 贸易条款 | FOB |
| urgency | 紧急度 | high / medium / low |
| intent | 意图 | 询价 / 样品 / 售后 / 合作 / 其他 |
| summary | 一句话摘要 | — |
| missing_info | 缺失信息 | ["联系人", "交期"] |
| confidence | 置信度 | 0–1 |

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查，返回是否已接入大模型 |
| GET | `/api/samples` | 内置样例 |
| POST | `/api/inquiries` | 解析并入库，body：`{"text": "...", "source": "email"}` |
| GET | `/api/inquiries` | 询盘列表 |
| GET | `/api/inquiries/{id}` | 单条详情 |
| POST | `/api/inquiries/{id}/draft` | 生成回复草稿 |
| GET | `/api/stats` | 统计（全部 / 已草拟 / 高优先） |

## 目录结构

```text
inquiry-agent/
├── run.py                  # 一键启动
├── start.bat               # Windows 双击启动
├── requirements.txt
├── .env.example            # 大模型配置模板
├── Dockerfile
├── samples/                # 样例询盘（可直接体验）
├── data/                   # SQLite 数据库（自动生成，已 gitignore）
└── app/
    ├── main.py             # FastAPI 路由与页面
    ├── config.py           # 环境配置
    ├── db.py               # SQLite 存储层
    ├── extractor.py        # 字段抽取（大模型 / 规则）
    ├── drafter.py          # 回复草拟（大模型 / 模板）
    ├── models.py
    └── static/             # 前端页面
```

## 设计取舍

- **为什么用 SQLite 而不是 MySQL**：这是一个"开箱即用"的工具，目标是任何人 clone 就能跑。SQLite 零安装、单文件，后续要换 Postgres 只需改 `db.py` 一处。
- **为什么做双层降级**：演示和开源项目最大的失败原因是"跑不起来"。规则兜底保证了最低体验。
- **为什么前端用原生 JS**：不引入构建链，减少"npm install 失败"的风险，别人打开就能用。
- **为什么字段要标 confidence**：让使用者知道哪些是"高把握"，哪些需要人工复核——AI 落地必须留人工兜底。

## 路线图

- [ ] 批量导入（拖拽多个文件 / 文件夹）
- [ ] 写入飞书多维表格 / 钉钉 AI 表格
- [ ] 回复模板可配置（按产品线 / 客户类型）
- [ ] 询盘去重与客户合并
- [ ] 导出 Excel

## License

MIT，见 [LICENSE](LICENSE)。
