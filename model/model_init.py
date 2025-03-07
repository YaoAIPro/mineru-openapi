from magic_pdf.model.doc_analyze_by_custom_model import ModelSingleton
from magic_pdf.model.sub_modules.model_init import AtomModelSingleton
from magic_pdf.model.model_list import AtomicModel
from magic_pdf.config.constants import MODEL_NAME
from magic_pdf.model.sub_modules.language_detection.utils import model_init
from magic_pdf.libs.config_reader import (get_device, get_formula_config,
                                          get_layout_config,
                                          get_local_models_dir,
                                          get_table_recog_config)
import os
import yaml
import importlib
from loguru import logger

class ModelInitializer:
    def __init__(self):
        self.magic_pdf_path, self.local_models_dir, self.device, self.configs = self.get_model_config()
        self.atom_model_manager = AtomModelSingleton()
        self.model_manager = ModelSingleton()
        self.temp_layout_model = self.init_image_model()
        self.langdetect_model = model_init(MODEL_NAME.YOLO_V11_LangDetect)


    def get_global_magic_pdf_path(self):
        spec = importlib.util.find_spec("magic_pdf")
        if spec and spec.origin:
            return os.path.dirname(os.path.abspath(spec.origin))
        return None

    def get_model_config(self):
        magic_pdf_path = self.get_global_magic_pdf_path()
        if not magic_pdf_path:
            logger.error("magic_pdf 未安装，请执行以下命令之一进行安装：\n"
                         "1. pip install -U \"magic-pdf[full]\" --extra-index-url https://wheels.myhloli.com -i https://mirrors.aliyun.com/pypi/simple\n"
                         "或\n"
                         "2. git clone https://github.com/opendatalab/MinerU.git")
            return None, None, None, None
        
        local_models_dir = get_local_models_dir()
        device = get_device()
        model_config_dir = os.path.join(magic_pdf_path, 'resources', 'model_config')
        config_path = os.path.join(model_config_dir, 'model_configs.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            configs = yaml.load(f, Loader=yaml.FullLoader)
        return magic_pdf_path, local_models_dir, device, configs

    def init_image_model(self):
        temp_layout_model = self.atom_model_manager.get_atom_model(
            atom_model_name=AtomicModel.Layout,
            layout_model_name=MODEL_NAME.DocLayout_YOLO,
            doclayout_yolo_weights=str(
                os.path.join(
                    self.local_models_dir, self.configs['weights'][MODEL_NAME.DocLayout_YOLO]
                )
            ),
            device=self.device,
        )
        return temp_layout_model

    def init_custom_model(self, 
                          ocr=False, 
                          show_log=False, 
                          lang=None, 
                          layout_model=None, 
                          formula_enable=None, 
                          table_enable=None
                          ):
        custom_model = self.model_manager.get_model(
            ocr=ocr, 
            show_log=show_log, 
            lang=lang, 
            layout_model=layout_model, 
            formula_enable=formula_enable, 
            table_enable=table_enable
        )
        print(custom_model)
        return custom_model


# Initialize the models
if __name__ == '__main__':
    model_initializer = ModelInitializer()
    temp_layout_model = model_initializer.temp_layout_model
    langdetect_model = model_initializer.langdetect_model
    custom_model = model_initializer.init_custom_model(ocr=False)
    ocr_model = model_initializer.init_custom_model(ocr=True)
    print("Model initialization completed.")
    