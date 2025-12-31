
from datetime import datetime
from pathlib import Path
import hashlib
import os
import re
import requests

class GPTSoVITSTTSEngine:
    """GPT-SoVITS TTS 引擎，参考 Open-LLM-VTuber 的实现"""
    
    def __init__(
        self,
        api_url: str = "",
        text_lang: str = "zh",
        ref_audio_path: str = "",
        prompt_lang: str = "zh",
        prompt_text: str = "",
        aux_ref_audio_paths: str = "",
        text_split_method: str = "cut5",
        batch_size: str = "1",
        media_type: str = "wav",
        streaming_mode: str = "false",
        cache_dir: str = "tts_cache"
    ):
        self.api_url = api_url
        self.text_lang = text_lang
        self.ref_audio_path = ref_audio_path
        self.aux_ref_audio_paths = aux_ref_audio_paths
        self.prompt_lang = prompt_lang
        self.prompt_text = prompt_text
        self.text_split_method = text_split_method
        self.batch_size = batch_size
        self.media_type = media_type
        self.streaming_mode = streaming_mode
        self.cache_dir = cache_dir
        
        # 创建缓存目录
        Path(self.cache_dir).mkdir(exist_ok=True)
    
    def _generate_cache_filename(self, text: str) -> str:
        """根据文本生成缓存文件名"""
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.cache_dir, f"tts_{timestamp}_{text_hash}.{self.media_type}")
    
    def generate_audio(self, text: str, file_name_no_ext="temp_audio") -> str:
        """
        生成语音文件 (修改版：默认覆盖模式)
        
        Parameters:
            text: 要转成语音的文本
            file_name_no_ext: 文件名（默认为 temp_audio，实现单文件覆盖）
        """
        # 1. 清理文本
        cleaned_text = re.sub(r"\[.*?\]", "", text)
        if not cleaned_text.strip():
            return None
        
        # 2. 确定文件名 (强制使用 temp_audio.wav)
        # 如果你想保留历史记录功能，可以改回 self._generate_cache_filename(cleaned_text)
        file_name = os.path.join(self.cache_dir, f"{file_name_no_ext}.{self.media_type}")
        
        # 3. === 关键修改：删除了“检查缓存是否存在”的逻辑 ===
        # 原来的代码在这里有 if os.path.exists(file_name): return file_name
        # 我们必须删掉它，否则它发现文件存在就不会去请求新的语音了！
        # 准备请求数据
        aux_paths = []
        if self.aux_ref_audio_paths.strip():
            # 支持用分号隔开多个路径
            aux_paths = [p.strip() for p in self.aux_ref_audio_paths.split(';') if p.strip()]

        data = {
            "text": cleaned_text,
            "text_lang": self.text_lang,
            "ref_audio_path": self.ref_audio_path,
            "prompt_lang": self.prompt_lang,
            "prompt_text": self.prompt_text,
            "text_split_method": self.text_split_method,
            "batch_size": self.batch_size,
            "media_type": self.media_type,
            "streaming_mode": self.streaming_mode,
            "aux_ref_audio_paths": aux_paths
        }
        
        try:
            # 发送请求
            response = requests.post(self.api_url, json=data, timeout=150)
            if response.status_code == 200:
                # 4. 写入文件 (wb 模式会自动覆盖旧文件)
                # 注意：如果此时文件正在被播放器占用，这里会报错 Permission denied
                # 所以必须确保 venti.py 里调用了 winsound.PlaySound(None, winsound.SND_PURGE)
                with open(file_name, "wb") as audio_file:
                    audio_file.write(response.content)
                return file_name
            else:
                return None
        except Exception as e:
            print(f"TTS Engine Error: {e}")
            return None
    
    def test_connection(self) -> tuple[bool, str]:
        """测试与 GPT-SoVITS API 的连接"""
        try:
            test_text = "测试连接"
            data = {
                "text": test_text,
                "text_lang": self.text_lang,
                "ref_audio_path": self.ref_audio_path,
                "prompt_lang": self.prompt_lang,
                "prompt_text": self.prompt_text,
                "text_split_method": self.text_split_method,
                "batch_size": self.batch_size,
                "media_type": self.media_type,
                "streaming_mode": self.streaming_mode,
            }
            
            response = requests.post(self.api_url, json=data, timeout=120)
            
            if response.status_code == 200:
                return True, "✅ 连接成功"
            else:
                return False, f"❌ API 返回错误: {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "❌ 连接超时"
        except requests.exceptions.ConnectionError:
            return False, "❌ 无法连接到 API 服务器"
        except Exception as e:
            return False, f"❌ 错误: {str(e)}"

