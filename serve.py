import torch
import filetype
import json, uuid
import litserve as ls
from unittest.mock import patch
from fastapi import HTTPException
# from magic_pdf.tools.common import do_parse
from doc_tools import do_parse
from magic_pdf.model.doc_analyze_by_custom_model import ModelSingleton
from magic_pdf.utils.office_to_pdf import convert_file_to_pdf, ConvertToPdfError
import pymupdf
import tempfile
import os
import shutil

class MinerUAPI(ls.LitAPI):
    def __init__(self, output_dir='output'):
        self.output_dir = output_dir

    @staticmethod
    def clean_memory(device):
        import gc
        if torch.cuda.is_available():
            with torch.cuda.device(device):
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        gc.collect()

    def setup(self, device):
        with patch('magic_pdf.model.doc_analyze_by_custom_model.get_device') as mock_obj:
            mock_obj.return_value = device
            model_manager = ModelSingleton()
            model_manager.get_model(True, False)
            model_manager.get_model(False, False)
            mock_obj.assert_called()
            print(f'Model initialization complete!')

    def convert_to_pdf(self, file_path, output_dir):
        try:
            convert_file_to_pdf(file_path, output_dir)
        except ConvertToPdfError as e:
            raise e
        except FileNotFoundError as e:
            raise e
        except Exception as e:
            raise e
        base_name = os.path.basename(file_path)
        pdf_name = os.path.splitext(base_name)[0] + '.pdf'
        pdf_path = os.path.join(output_dir, pdf_name)
        return pdf_path


    def to_pdf(self, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        try:
            if file_extension in ['.doc', '.docx', '.ppt', '.pptx']:
                temp_dir = tempfile.mkdtemp()
                file_path = self.convert_to_pdf(file_path, temp_dir)
            with pymupdf.open(file_path) as f:
                if f.is_pdf:
                    pdf_bytes = f.tobytes()
                else:
                    pdf_bytes = f.convert_to_pdf()
                return pdf_bytes
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'{e}')
        finally:
            if file_extension in ['.doc', '.docx', '.ppt', '.pptx']:
                shutil.rmtree(temp_dir)

    def collect_files(self, output_dir):

        image_files = []
        other_files = []

        for root, dirs, files in os.walk(output_dir):
            for file in files:

                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(root, output_dir)
                path_parts = relative_path.split(os.sep)
                
                if len(path_parts) == 2 and path_parts[1] == 'images':
                    image_files.append(full_path)
                else:
                    other_files.append(full_path)
        
        return {'output_dir' : output_dir, 'images': image_files, 'files': other_files}

    def decode_request(self, request):
        file = self.to_pdf(request['file_path'])
        kwargs = json.loads(request['kwargs'])
        assert filetype.guess_mime(file) == 'application/pdf'
        return file, kwargs

    def predict(self, inputs):
        try:
            pdf_name = str(uuid.uuid4())
            do_parse(self.output_dir, pdf_name, inputs[0], [], **inputs[1])
            path = os.path.join(self.output_dir, pdf_name)
            return self.collect_files(path)
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'{e}')
        finally:
            self.clean_memory(self.device)

    def encode_response(self, response):
        return {'output_dir': response}


if __name__ == '__main__':
    server = ls.LitServer(MinerUAPI(), accelerator='gpu', devices=[0], timeout=False)
    server.run(port=8000)