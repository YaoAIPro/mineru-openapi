from magic_pdf.data.dataset import Dataset
from magic_pdf.operators.models import InferenceResult
from magic_pdf.model.sub_modules.model_utils import get_vram
from magic_pdf.libs.clean_memory import clean_memory
from magic_pdf.libs.config_reader import get_device
from magic_pdf.model.batch_analyze import BatchAnalyze
from loguru import logger
import torch
import time
import os

class DocumentAnalyzer:
    def __init__(self, dataset: Dataset, custom_model=None):
        self.dataset = dataset
        self.custom_model = custom_model
        self.device = get_device()
        self.batch_analyze = False
        self.batch_ratio = 1
        self.npu_support = False
        self._check_device_support()

    def _check_device_support(self):
        if str(self.device).startswith("npu"):
            import torch_npu
            if torch_npu.npu.is_available():
                self.npu_support = True

        if torch.cuda.is_available() and self.device != 'cpu' or self.npu_support:
            gpu_memory = int(os.getenv("VIRTUAL_VRAM_SIZE", round(get_vram(self.device))))
            if gpu_memory is not None and gpu_memory >= 8:
                if gpu_memory >= 16:
                    self.batch_ratio = 8
                elif gpu_memory >= 10:
                    self.batch_ratio = 4
                else:
                    self.batch_ratio = 2

                logger.info(f'gpu_memory: {gpu_memory} GB, batch_ratio: {self.batch_ratio}')
                self.batch_analyze = True

    def analyze(self, start_page_id=0, end_page_id=None) -> InferenceResult:
        end_page_id = (
            end_page_id
            if end_page_id is not None and end_page_id >= 0
            else len(self.dataset) - 1
        )

        model_json = []
        doc_analyze_start = time.time()

        if self.batch_analyze:
            model_json = self._batch_analyze(start_page_id, end_page_id)
        else:
            model_json = self._single_analyze(start_page_id, end_page_id)

        gc_start = time.time()
        clean_memory(self.device)
        gc_time = round(time.time() - gc_start, 2)
        logger.info(f'gc time: {gc_time}')

        doc_analyze_time = round(time.time() - doc_analyze_start, 2)
        doc_analyze_speed = round((end_page_id + 1 - start_page_id) / doc_analyze_time, 2)
        logger.info(
            f'doc analyze time: {round(time.time() - doc_analyze_start, 2)},'
            f' speed: {doc_analyze_speed} pages/second'
        )

        return InferenceResult(model_json, self.dataset)

    def _batch_analyze(self, start_page_id, end_page_id):
        images = []
        page_wh_list = []
        for index in range(len(self.dataset)):
            if start_page_id <= index <= end_page_id:
                page_data = self.dataset.get_page(index)
                img_dict = page_data.get_image()
                images.append(img_dict['img'])
                page_wh_list.append((img_dict['width'], img_dict['height']))
        batch_model = BatchAnalyze(model=self.custom_model, batch_ratio=self.batch_ratio)
        analyze_result = batch_model(images)

        model_json = []
        for index in range(len(self.dataset)):
            if start_page_id <= index <= end_page_id:
                result = analyze_result.pop(0)
                page_width, page_height = page_wh_list.pop(0)
            else:
                result = []
                page_height = 0
                page_width = 0

            page_info = {'page_no': index, 'width': page_width, 'height': page_height}
            page_dict = {'layout_dets': result, 'page_info': page_info}
            model_json.append(page_dict)
        return model_json

    def _single_analyze(self, start_page_id, end_page_id):
        model_json = []
        for index in range(len(self.dataset)):
            page_data = self.dataset.get_page(index)
            img_dict = page_data.get_image()
            img = img_dict['img']
            page_width = img_dict['width']
            page_height = img_dict['height']
            if start_page_id <= index <= end_page_id:
                page_start = time.time()
                result = self.custom_model(img)
                logger.info(f'-----page_id : {index}, page total time: {round(time.time() - page_start, 2)}-----')
            else:
                result = []

            page_info = {'page_no': index, 'width': page_width, 'height': page_height}
            page_dict = {'layout_dets': result, 'page_info': page_info}
            model_json.append(page_dict)
        return model_json


class FilesPreprocessing:
        def __init__(self, dataset: Dataset, custom_model=None):
            self.dataset = dataset
            self.custom_model = custom_model

        def analyze(self):
            doc_analyze = DocumentAnalyzer(dataset=self.dataset, custom_model=self.custom_model)
            self.infer_result = doc_analyze.analyze()

        def save(self, name_without_suff, local_image_dir, local_md_dir, image_writer, md_writer):
            pipe_result = self.infer_result.pipe_ocr_mode(image_writer)
            self.infer_result.draw_model(os.path.join(local_md_dir, f"{name_without_suff}_model.pdf"))
            pipe_result.draw_layout(os.path.join(local_md_dir, f"{name_without_suff}_layout.pdf"))
            pipe_result.draw_span(os.path.join(local_md_dir, f"{name_without_suff}_spans.pdf"))
            
            pipe_result.get_markdown(os.path.basename(local_image_dir))
            pipe_result.dump_md(md_writer, f"{name_without_suff}.md", os.path.basename(local_image_dir))
            
            pipe_result.dump_content_list(md_writer, f"{name_without_suff}_content_list.json", os.path.basename(local_image_dir))
            pipe_result.dump_middle_json(md_writer, f"{name_without_suff}_middle.json")

            return [
                os.path.join(local_md_dir, f"{name_without_suff}_model.pdf"),
                os.path.join(local_md_dir, f"{name_without_suff}_layout.pdf"),
                os.path.join(local_md_dir, f"{name_without_suff}_spans.pdf"),
                os.path.join(local_md_dir, f"{name_without_suff}.md"),
                os.path.join(local_md_dir, f"{name_without_suff}_content_list.json"),
                os.path.join(local_md_dir, f"{name_without_suff}_middle.json")]

