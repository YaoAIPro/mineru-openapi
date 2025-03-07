from fastapi import FastAPI, File, UploadFile
from typing import List
from contextlib import asynccontextmanager
from loguru import logger

import torch
import tempfile
import os
import uvicorn
import aiofiles
from PIL import Image

from magic_pdf.data.data_reader_writer import FileBasedDataReader
from magic_pdf.libs.pdf_check import extract_pages
from magic_pdf.data.utils import load_images_from_pdf
from magic_pdf.data.read_api import read_local_office
from document import PymuDocDataset, DirPreprocessing, FilesPreprocessing
from model.model_init import ModelInitializer
import shutil

def clear_gpu_cache():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  
    clear_gpu_cache()


app = FastAPI(lifespan=lifespan)

def get_text_images(temp_layout_model, simple_images):
    text_images = []
    for simple_image in simple_images:
        image = Image.fromarray(simple_image['img'])
        layout_res = temp_layout_model.predict(image)
        for res in layout_res:
            if res['category_id'] in [1]:
                x1, y1, _, _, x2, y2, _, _ = res['poly']
                if x2 - x1 < 100 and y2 - y1 < 100:
                    continue
                text_images.append(image.crop((x1, y1, x2, y2)))
    return text_images

@app.post("/mineru/parsing")
async def parsing(files: List[UploadFile] = File(...)):
    logger.info(f"files == {files}")
    def check_file_type(file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return 1
        elif file_extension in ['.ppt', '.pptx', '.doc', '.docx']:
            return 2
        else:
            return 0
        
    with tempfile.TemporaryDirectory() as temp_dir:
        results, fails = {}, []
        for file in files:
            dp = DirPreprocessing(file=file.filename)
            file_path = os.path.join(temp_dir, file.filename)
            lang = "auto"
            try:
                async with aiofiles.open(file_path, "wb") as buffer:
                    await buffer.write(await file.read())
                
                name_without_suff, local_image_dir, local_md_dir, image_writer, md_writer = dp.get()
                
                flag = check_file_type(file.filename)
                if flag == 1:
                    reader = FileBasedDataReader()
                    pdf_bytes = reader.read(file_path)
                    sample_docs = extract_pages(pdf_bytes)
                    simple_images = load_images_from_pdf(sample_docs.tobytes(), dpi=200)
                    text_images = get_text_images(temp_layout_model, simple_images)
                    ds = PymuDocDataset(bits=pdf_bytes, text_images=text_images, langdetect_model=langdetect_model, lang=lang)
                elif flag == 2:
                    ds = read_local_office(file_path)[0]
                else:
                    continue
                
                fp = FilesPreprocessing(dataset=ds, custom_model=ocr_model)
                fp.analyze()
                files = fp.save(name_without_suff, local_image_dir, local_md_dir, image_writer, md_writer)
            
                results[file.filename] = {"files": files, "images": [os.path.join(local_image_dir,f) for f in os.listdir(local_image_dir)]}
            except Exception as e:
                logger.error(f"Failed to process file {file.filename}: {e}")
                fails.append(file.filename)
                for path in [local_image_dir, local_md_dir]:
                    if os.path.exists(path):
                        shutil.rmtree(path) 
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
    
    return {"message": "success", "data": results, "fails": fails}



if __name__ == "__main__":
    model_initializer = ModelInitializer()
    temp_layout_model = model_initializer.temp_layout_model
    langdetect_model = model_initializer.langdetect_model
    ocr_model = model_initializer.init_custom_model(ocr=True)
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=1)