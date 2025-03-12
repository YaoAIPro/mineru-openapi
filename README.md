# MinerU-OpenAPI

**基于[MinerU](https://github.com/opendatalab/MinerU)二次开发的多格式文档解析API服务**，使用 FastAPI 实现 PDF、PPT、PPTX、DOC、DOCX 等格式的高效解析与结构化输出。

## 特性

- **多格式支持**：PDF、PPT、PPTX、DOC、DOCX、PNG、JPG
- **高性能解析**：模型预加载，减少初始化时间
- **批量处理**：支持多文件批量上传与解析
- **结构化输出**：返回解析后的文本、图片、布局等结构化数据
- **分批加载 + 线程池加速**：控制内存占用，防止 OOM，提高并发处理能力
- **支持多GPU部署**：可在多张 GPU 上运行，提高处理能力

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

## API示例

### Python 示例

```python
import json
import requests
import numpy as np
from loguru import logger
from joblib import Parallel, delayed


def do_parse(file_path, url='http://127.0.0.1:8000/predict', **kwargs):
    try:
        kwargs.setdefault('parse_method', 'auto')
        kwargs.setdefault('debug_able', False)
        print(file_path)
        response = requests.post(url,
            data={'kwargs': json.dumps(kwargs), "file_path": file_path}
        )

        if response.status_code == 200:
            output = response.json()
            output['file_path'] = file_path
            return output
        else:
            raise Exception(response.text)
    except Exception as e:
        logger.error(f'File: {file_path} - Info: {e}')


if __name__ == '__main__':
    files = ['file.pdf', 'file2.doc']
    n_jobs = np.clip(len(files), 1, 4)
    results = Parallel(n_jobs, prefer='threads', verbose=10)(
        delayed(do_parse)(p) for p in files
    )
    print(results)
```

