import json
import math
import time
from typing import List, Union, Dict, overload
import requests
from .DetectResponse import DetectResponse
from .LanguageResponse import LanguageResponse
from .Null import Null
from .TranslateResponse import TranslateResponse

def split_list(obj_list: List, sub_size: int = 128) -> List[list]:
    """split list"""
    if not isinstance(obj_list, list):
        return [[obj_list]]
    if sub_size < 1:
        sub_size = 1
    return [obj_list[i:i + sub_size] for i in range(0, len(obj_list), sub_size)]

def split_list_by_content_size(obj_list: List[str], content_size: int = 102400) -> List[List[str]]:
    """..."""
    if content_size < 1:
        content_size = 1
    if len(obj_list) == 1 or len(''.join(obj_list)) <= content_size:
        return [obj_list]

    mid = math.ceil(len(obj_list) / 2)
    ll = []
    ll.extend(split_list_by_content_size(obj_list[:mid], content_size=content_size))
    ll.extend(split_list_by_content_size(obj_list[mid:], content_size=content_size))
    return ll

class ApiKeyTranslate:
    _BASE_URL: str = 'https://translation.googleapis.com/language/translate/v2'
    _LANGUAGE_URL: str = f'{_BASE_URL}/languages'
    _DETECT_URL: str = f'{_BASE_URL}/detect'
    _LIMIT_SIZE = 102400

    def __init__(
            self, api_key: str,
            target: str = 'zh-CN',
            source: str = None,
            fmt: str = 'html',
            model: str = 'nmt',
            proxies: Dict = None,
            timeout=None
    ):
        self.api_key = api_key
        self.target = target
        self.timeout = timeout
        if source == 'auto':
            source = None
        self.source = source
        self.fmt = fmt
        self.model = model
        self.session = requests.Session()

        if proxies is not None:
            self.session.trust_env = False
            self.session.proxies = proxies

    def languages(self, target: str = None, model: str = None, timeout=...) -> Union[List[LanguageResponse], Null]:
        """语言支持列表"""
        if target is None:
            target = self.target
        if model is None:
            model = self.model
        if timeout is ...:
            timeout = self.timeout
        response = self.session.get(self._LANGUAGE_URL, params={'key': self.api_key, 'target': target, 'model': model},
                                    timeout=timeout)
        if response.status_code == 200:
            return [LanguageResponse(**i) for i in response.json()['data']['languages']]
        return Null(response)

    def detect(self, q: Union[str, List[str]], timeout=...) -> Union[DetectResponse, List[DetectResponse], Null]:
        """语言检测, 支持批量"""
        if timeout is ...:
            timeout = self.timeout
        ll = []
        for ql in split_list(q):
            for qli in split_list_by_content_size(ql):
                for i in range(1, 4):
                    response = self.session.post(self._DETECT_URL, params={'key': self.api_key}, data={'q': qli},
                                                 timeout=timeout)
                    if response.status_code == 429:
                        time.sleep(5 * i)
                        continue
                    break
                if response.status_code != 200:
                    return Null(response)
                ll.extend([DetectResponse(**i[0]) for i in response.json()['data']['detections']])
        if isinstance(q, str):
            return ll[0]
        return ll

    def translate(self, q: Union[str, List[str]], target: str = None, source: str = None, fmt: str = None,
                  model: str = None, timeout=...) -> Union[TranslateResponse, List[TranslateResponse], Null]:
        """文本翻译, 支持批量"""
        if target is None:
            target = self.target
        if source is None:
            source = self.source
        if fmt is None:
            fmt = self.fmt
        if model is None:
            model = self.model
        if timeout is ...:
            timeout = self.timeout
        ll = []
        for ql in split_list(q):
            for qli in split_list_by_content_size(ql):
                for i in range(1, 4):
                    response = self.session.post(self._BASE_URL, params={
                        'key': self.api_key, 'target': target, 'source': source, 'format': fmt, 'model': model
                    }, data={'q': qli}, timeout=timeout)
                    if response.status_code == 429:
                        time.sleep(5 * i)
                        continue
                    break
                if response.status_code != 200:
                    return Null(response)

                ll.extend([TranslateResponse(**i) for i in response.json()['data']['translations']])

        if isinstance(q, str):
            return ll[0]
        return ll

    def translate_jsonl(self, input_file: str, output_file: str, target: str = None, source: str = None):
        """翻译JSONL文件并保存结果"""
        if target is None:
            target = self.target
        if source is None:
            source = self.source

        with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
            for line in infile:
                json_obj = json.loads(line.strip())  # 逐行读取并解析为JSON对象
                text_to_translate = json_obj.get('text', '')  # 假设JSON中有'text'字段需要翻译
                if text_to_translate:
                    translated_text = self.translate(text_to_translate, target=target, source=source)
                    json_obj['translatedText'] = translated_text.translatedText  # 添加翻译结果到JSON对象
                outfile.write(json.dumps(json_obj, ensure_ascii=False) + '\n')  # 写回文件
