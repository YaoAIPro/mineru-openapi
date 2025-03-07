# MinerU-OpenAPI

**基于[MinerU](https://github.com/opendatalab/MinerU)二次开发的多格式文档解析API服务**，使用 FastAPI 实现 PDF、PPT、PPTX、DOC、DOCX 等格式的高效解析与结构化输出。

## 特性

- **多格式支持**：PDF、PPT、PPTX、DOC、DOCX
- **高性能解析**：模型预加载，减少初始化时间
- **批量处理**：支持多文件批量上传与解析
- **结构化输出**：返回解析后的文本、图片、布局等结构化数据

## 快速开始

### 1. 环境要求

- Python 3.10
- CUDA 11.8+（GPU加速）
- 内存：8GB+
- centos 7

### 2. [MinerU部署](https://github.com/opendatalab/MinerU/blob/master/docs/README_Ubuntu_CUDA_Acceleration_en_US.md)

### 3. 安装依赖

```
git clone https://github.com/YaoAIPro/mineru-openapi.git
cd mineru-openapi
pip install -r requirements.txt
```

```
python serve.py
```

访问交互式文档：`http://127.0.0.1:8000/docs`

![image-20250307161352665](pic/image-20250307161352665.png)

## API示例

### Python 示例

```python
import requests

url = "http://127.0.0.1:8000/mineru/parsing"

files = [
    ('files', ('file1.pdf', open('file1.pdf', 'rb'), 'application/pdf')),
    ('files', ('file2.docx', open('file2.docx', 'rb'), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')),
    ('files', ('file3.pptx', open('file3.pptx', 'rb'), 'application/vnd.openxmlformats-officedocument.presentationml.presentation'))
]


response = requests.post(url, files=files)

print(response.json())  
```

### 返回结果示例

```json
{
  "message": "success",
  "data": {
    "file1.pdf": {
      "files": [
        "file1_model.pdf",
        "file1_layout.pdf",
        "file1_spans.pdf",
        "file1.md",
        "file1_content_list.json",
        "file1_middle.json"
      ],
      "images": [
        "b4711891fad4eb33f0a715e1d86e58e871c368c23afb403e25f1cd9b81b178a9.jpg"
      ]
    },
    "...": 
  },
  "fails": []
}
```

## API 详细说明

### 1. 文件解析接口

- **URL**: `/mineru/parsing`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- 参数:`files`: 需要解析的文件列表（支持多文件上传）
- 返回结果:
  - `message`: 请求状态（`success`）
  - `data`: 解析后的文件数据，包含文本、图片、布局等信息
  - `fails`: 解析失败的文件列表

## 致谢

本项目基于 OpenDataLab/MinerU 开发，感谢其核心技术的贡献。