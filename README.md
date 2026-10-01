# 统一 AI 生图工具 (Image Generation Tool)

这是一个轻量、独立、多后端的统一 AI 图像生成工具。它屏蔽了各大模型供应商的 API 差异，提供统一的命令行接口，支持文生图、图生图（局部编辑）、批量清单并发调度，以及 API Key 的 Base64 密文加密存储。

---

## 一、目录结构

```text
image_gen/
├── README.md               # 本文档说明
├── image_gen.py            # 主程序（统一生图调度入口）
├── .env.example            # 环境配置模板
├── test_image_gen.py       # 自动化测试套件
└── image_backends/         # 模型后端调用实现（OpenAI、通义、智谱、Gemini 等）
```

---

## 二、环境与依赖安装

工具基于 Python 3 编写，仅需以下基础库：

```bash
pip install requests pillow
```

*(可选依赖：使用 Gemini 原生 SDK 需 `pip install google-genai`，使用 OpenAI 官方 SDK 需 `pip install openai`，一般情况下 requests 模式即可满足日常生图)*

---

## 三、快速开始与配置

### 1. 复制配置文件

在当前目录或项目根目录下创建环境配置文件：

```bash
cp .env.example .env
```

### 2. Base64 密文保存 API Key（避免明文泄露）

为了防止 API Key 明文保存在版本库或本地文件中，工具内置了 Base64 密钥编码与自动解析功能。

通过命令行一键生成 Base64 密文字符串：
```bash
python3 image_gen.py --encode-key "sk-你的真实APIKey"
```

输出示例：
```text
[Base64 Key Encoder]
Original key:  sk-abc***
Encoded value: base64:c2stYWJjZGVmMTIzNDU2

Use in .env without plain text:
  QWEN_API_KEY=base64:c2stYWJjZGVmMTIzNDU2
  # Or: QWEN_API_KEY_B64=c2stYWJjZGVmMTIzNDU2
```

将生成的密文填入 `.env` 即可（程序读取时会自动还原解密，亦向下兼容普通明文 Key）。

---

## 四、常见服务商配置示例（.env）

#### 1. 阿里通义千问 / 万相（DashScope）
```env
IMAGE_BACKEND=qwen
QWEN_API_KEY=base64:c2steHh4eHh4eHh4...
QWEN_MODEL=qwen-image-2.0-pro
# 可选自定义端点：
# QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
```

#### 2. OpenAI 或兼容第三方转发 API（OneAPI / 中转平台）
```env
IMAGE_BACKEND=openai
OPENAI_API_KEY=base64:c2steHh4eHh4eHh4...
OPENAI_MODEL=gpt-image-2
# 若使用第三方转发端点：
# OPENAI_BASE_URL=https://api.your-proxy-domain.com/v1
```

#### 3. 智谱 AI（GLM-Image / BigModel）
```env
IMAGE_BACKEND=zhipu
ZHIPU_API_KEY=base64:xxxxxxxxxxxxxxxx...
ZHIPU_MODEL=glm-image
```

#### 4. Google Gemini
```env
IMAGE_BACKEND=gemini
GEMINI_API_KEY=base64:xxxxxxxxxxxxxxxx...
GEMINI_MODEL=gemini-3.1-flash-image
```

#### 5. 火山引擎即梦（Seedream）
```env
IMAGE_BACKEND=volcengine
LAS_API_KEY=base64:xxxxxxxxxxxxxxxx...
VOLCENGINE_MODEL=doubao-seedream-4-5-251128
```

---

## 五、常用命令行使用指南

### 1. 查看受支持的后端列表
```bash
python3 image_gen.py --list-backends
```

### 2. 单张文生图
```bash
python3 image_gen.py "修仙宗门大殿，云雾缭绕，仙鹤飞过，国风厚涂仙侠风格" \
  --aspect_ratio 16:9 \
  --image_size 2K \
  -o ./images \
  -f zongmen_hall
```

**参数说明**：
- `--aspect_ratio`：画面比例，支持 `1:1`, `16:9`, `4:3`, `3:2`, `9:16`, `21:9` 等（依后端支持）。
- `--image_size`：分辨率档位，支持 `512px`, `1K`, `2K`, `4K`。
- `-o, --output`：指定图片输出目录（若目录不存在会自动创建）。
- `-f, --filename`：指定生成文件的文件名主名（无需扩展名，脚本会自动补充 `.png` 或 `.jpg`）。
- `-b, --backend`：临时覆盖配置文件中指定的后端平台（例如 `-b qwen`）。
- `-m, --model`：临时指定模型名称。

### 3. 参考图编辑（图生图 / 局部重绘）
*(需后端支持图生图能力，例如 openai、gemini)*
```bash
python3 image_gen.py "调整为夜晚月光笼罩，主殿亮起长明灯" \
  --reference-image ./images/zongmen_hall.png \
  -o ./images \
  -f zongmen_hall_night
```

### 4. 批量清单并发模式（Manifest）
可将多张图片任务统一写在一个 JSON 清单中：
```json
{
  "items": [
    {
      "filename": "shot_01.png",
      "aspect_ratio": "16:9",
      "image_size": "2K",
      "prompt": "飞剑破空，剑芒划过天际...",
      "status": "Pending"
    },
    {
      "filename": "shot_02.png",
      "aspect_ratio": "16:9",
      "image_size": "2K",
      "prompt": "护宗大阵受击，金色波纹扩散...",
      "status": "Pending"
    }
  ]
}
```

执行批量生成：
```bash
python3 image_gen.py --manifest prompts.json --concurrency 3
```
- 自动多线程并发请求（默认并发数 3）。
- 遇平台频率限制（Rate Limit）自动退避减速重试。
- 生成成功的条目自动将状态原子写回为 `Generated`，支持断点续跑。

---

## 六、运行自动化测试

在当前目录下执行：

```bash
python3 test_image_gen.py
```

测试套件将自动验证：
- Base64 多种前缀与后缀语法解密正确性
- `.env` 变量安全解析与注入
- CLI 命令行参数验证与拦截
- 生成流程数据落地与图像校验
