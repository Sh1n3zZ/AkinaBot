"""
@Author         : Ailitonia
@Date           : 2022/04/17 0:03
@FileName       : image_util.py
@Project        : nonebot2_miya 
@Description    : Image Tools
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import base64
import random
from typing import Literal
from copy import deepcopy
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont

from src.resource import BaseResource, TemporaryResource
from src.service.omega_requests import OmegaRequests

from .config import image_utils_config


class ImageUtils(object):
    def __init__(self, image: Image.Image):
        self._image = image

    @classmethod
    def init_from_bytes(cls, image: bytes) -> "ImageUtils":
        """从 Bytes 中初始化"""
        with BytesIO(image) as bf:
            image: Image.Image = Image.open(bf)
            image.load()
            new_obj = cls(image=image)
        return new_obj

    @classmethod
    def init_from_file(cls, file: BaseResource) -> "ImageUtils":
        """从文件初始化"""
        with file.open('rb') as f:
            image: Image.Image = Image.open(f)
            image.load()
            new_obj = cls(image=image)
        return new_obj

    @classmethod
    async def init_from_url(cls, image_url: str) -> "ImageUtils":
        """从 URL 初始化"""
        fetcher = OmegaRequests(timeout=30)
        image_result = await fetcher.get(url=image_url)
        with BytesIO(image_result.content) as bf:
            image: Image.Image = Image.open(bf)
            image.load()
            new_obj = cls(image=image)
        return new_obj

    @classmethod
    def init_from_text(
            cls,
            text: str,
            *,
            image_width: int = 512,
            font_name: str | None = None,
            alpha: bool = False
    ) -> "ImageUtils":
        """从文本初始化, 文本转图片并自动裁切

        :param text: 待转换文本
        :param image_width: 限制图片宽度, 像素
        :param font_name: 字体名称, 本地资源中字体文件名
        :param alpha: 输出带 alpha 通道的图片
        """
        if font_name is None:
            font_file = image_utils_config.default_font_file
        else:
            font_file = image_utils_config.default_font_folder(font_name)

        # 处理文字层 主体部分
        font_size = image_width // 25
        font = ImageFont.truetype(font_file.resolve_path, font_size)
        # 按长度切分文本
        text = cls.split_multiline_text(text=text, width=int(image_width * 0.75), font=font)
        _, text_height = font.getsize_multiline(text)
        # 初始化背景图层
        image_height = text_height + 100
        if alpha:
            background = Image.new(mode="RGBA", size=(image_width, image_height), color=(255, 255, 255, 0))
        else:
            background = Image.new(mode="RGB", size=(image_width, image_height), color=(255, 255, 255))
        # 绘制文字
        ImageDraw.Draw(background).multiline_text(
            xy=(int(image_width * 0.115), 50),
            text=text,
            font=font,
            fill=(0, 0, 0)
        )
        new_obj = cls(image=background)
        return new_obj

    @classmethod
    def split_multiline_text(
            cls,
            text: str,
            width: int,
            *,
            font: ImageFont.FreeTypeFont | str | None = None,
            stroke_width: int = 0
    ) -> str:
        """按字体绘制的文本长度切分换行文本

        :param text: 待切分的文本
        :param width: 宽度限制, 像素
        :param font: 绘制使用的字体, 传入 str 为本地字体资源文件名
        :param stroke_width: 文字描边, 像素
        """
        if font is None:
            font = ImageFont.truetype(image_utils_config.default_font_file.resolve_path,
                                      image_utils_config.default_font_size)
        elif isinstance(font, str):
            font = ImageFont.truetype(image_utils_config.default_font_folder(font).resolve_path,
                                      image_utils_config.default_font_size)

        spl_num = 0
        spl_list = []
        for num in range(len(text)):
            text_width, text_height = font.getsize_multiline(text[spl_num:num], stroke_width=stroke_width)
            if text_width > width:
                spl_list.append(text[spl_num:num])
                spl_num = num
        else:
            spl_list.append(text[spl_num:])

        return '\n'.join(spl_list)

    @property
    def image(self) -> Image.Image:
        """获取 Image 对象副本"""
        return deepcopy(self._image)

    @property
    def base64(self) -> str:
        """转换为 Base64 输出"""
        b64 = base64.b64encode(self.get_bytes())
        b64 = str(b64, encoding='utf-8')
        return 'base64://' + b64

    def get_bytes(self, *, format_: str = 'JPEG') -> bytes:
        """获取 Image 内容, 以 Bytes 输出"""
        with BytesIO() as _bf:
            self._image.save(_bf, format=format_)
            _content = _bf.getvalue()
        return _content

    def get_bytes_add_blank(self, bytes_num: int = 16, *, format_: str = 'JPEG') -> bytes:
        """返回图片并在末尾添加空白比特"""
        return self.get_bytes(format_=format_) + b' '*bytes_num

    async def save(self, file_name: str, *, format_: str = 'JPEG') -> TemporaryResource:
        """输出指定格式图片到文件"""
        save_file = image_utils_config.tmp_output_folder(file_name)
        async with save_file.async_open('wb') as af:
            await af.write(self.get_bytes(format_=format_))
        return save_file

    def mark(
            self,
            text: str,
            *,
            position: Literal['la', 'ra', 'lb', 'rb', 'c'] = 'rb',
            fill: tuple[int, int, int] = (128, 128, 128)
    ) -> "ImageUtils":
        """在图片上添加标注文本"""
        image = self.image
        width, height = image.size
        font = ImageFont.truetype(image_utils_config.default_font_file.resolve_path, width // 32)

        match position:
            case 'c':
                ImageDraw.Draw(image).text(
                    xy=(width // 2, height // 2), text=text, font=font, align='center', anchor='mm', fill=fill)
            case 'la':
                ImageDraw.Draw(image).text(
                    xy=(0, 0), text=text, font=font, align='left', anchor='la', fill=fill)
            case 'ra':
                ImageDraw.Draw(image).text(
                    xy=(width, 0), text=text, font=font, align='right', anchor='ra', fill=fill)
            case 'lb':
                ImageDraw.Draw(image).text(
                    xy=(0, height), text=text, font=font, align='left', anchor='lb', fill=fill)
            case 'rb' | _:
                ImageDraw.Draw(image).text(
                    xy=(width, height), text=text, font=font, align='right', anchor='rb', fill=fill)

        self._image = image
        return self

    def gaussian_blur(self, radius: int | None = None) -> "ImageUtils":
        """高斯模糊"""
        _image = self.image
        if radius is None:
            blur_radius = _image.width // 16
        else:
            blur_radius = radius
        blur_image = _image.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        self._image = blur_image
        return self

    def gaussian_noise(
            self,
            *,
            sigma: float = 8,
            enable_random: bool = True,
            mask_factor: float = 0.25) -> "ImageUtils":
        """为图片添加肉眼不可见的底噪

        :param sigma: 噪声sigma, 默认值8
        :param enable_random: 为噪声sigma添加随机扰动, 默认值True
        :param mask_factor: 噪声蒙版透明度修正, 默认值0.25
        :return:
        """
        _image = self.image
        # 处理图片
        width, height = _image.size
        # 为sigma添加随机扰动
        if enable_random:
            _sigma = sigma * (1 + 0.1 * random.random())
        else:
            _sigma = sigma
        # 生成高斯噪声底图
        noise_image = Image.effect_noise(size=(width, height), sigma=_sigma)
        # 生成底噪蒙版
        noise_mask = ImageEnhance.Brightness(noise_image.convert('L')).enhance(factor=mask_factor)
        # 叠加噪声图层
        _image.paste(noise_image, (0, 0), mask=noise_mask)

        self._image = _image
        return self

    def resize_with_filling(self, size: tuple[int, int]) -> "ImageUtils":
        """在不损失原图长宽比的条件下, 使用透明图层将原图转换成指定大小"""
        _image = self.image
        # 计算调整比例
        width, height = _image.size
        rs_width, rs_height = size
        scale = min(rs_width / width, rs_height / height)

        _image = _image.resize((int(width * scale), int(height * scale)))
        box = (int(abs(width * scale - rs_width) / 2), int(abs(height * scale - rs_height) / 2))
        background = Image.new(mode="RGBA", size=size, color=(255, 255, 255, 0))
        background.paste(_image, box=box)

        self._image = background
        return self

    def resize_fill_canvas(self, size: tuple[int, int]) -> "ImageUtils":
        """在不损失原图长宽比的条件下, 填充并平铺指定大小画布"""
        _image = self.image
        # 计算调整比例
        width, height = _image.size
        rs_width, rs_height = size
        scale = max(rs_width / width, rs_height / height)

        _image = _image.resize((int(width * scale), int(height * scale)))
        box = (- int(abs(width * scale - rs_width) / 2), - int(abs(height * scale - rs_height) / 2))
        background = Image.new(mode="RGBA", size=size, color=(255, 255, 255, 0))
        background.paste(_image, box=box)

        self._image = background
        return self


__all__ = [
    'ImageUtils'
]