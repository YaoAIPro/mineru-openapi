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