import sys
import os
import pandas as pd
import glob
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.cm as cm
from matplotlib import font_manager

# 显式指定中文字体，绘图时用 _CHINESE_FONT_PATH 创建 FontProperties 以保证中文正常显示
_CHINESE_FONT_PROPS = None
_CHINESE_FONT_PATH = None


def _get_chinese_font():
    """返回用于绘图的字体属性；内部会设置 _CHINESE_FONT_PATH 供按字号复用。"""
    global _CHINESE_FONT_PROPS, _CHINESE_FONT_PATH
    if _CHINESE_FONT_PROPS is not None:
        return _CHINESE_FONT_PROPS

    _base = os.path.dirname(os.path.abspath(__file__))

    def _try_load(path):
        try:
            font_manager.fontManager.addfont(path)
            # TTC 需指定 ttc_fontindex，部分环境否则会失败
            if path.lower().endswith('.ttc'):
                try:
                    return font_manager.FontProperties(fname=path, ttc_fontindex=0)
                except Exception:
                    return font_manager.FontProperties(fname=path)
            return font_manager.FontProperties(fname=path)
        except Exception:
            return None

    # 1) 项目 fonts 目录
    for _fname in (
            'NotoSansCJKsc-Regular.otf', 'NotoSansCJKsc-Regular.ttf', 'SourceHanSansSC-Regular.otf', 'wqy-zenhei.ttc',
            'wqy-zenhei.ttf'):
        _p = os.path.join(_base, 'fonts', _fname)
        if os.path.isfile(_p):
            fp = _try_load(_p)
            if fp is not None:
                _CHINESE_FONT_PATH = _p
                _CHINESE_FONT_PROPS = fp
                plt.rcParams['font.sans-serif'] = [fp.get_name()]
                plt.rcParams['axes.unicode_minus'] = False
                return _CHINESE_FONT_PROPS

    # 2) 系统常见路径
    for _p in (
            '/usr/share/fonts/truetype/wqy-zenhei/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy-microhei/wqy-microhei.ttc',
            '/app/fonts/NotoSansCJKsc-Regular.otf',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    ):
        if os.path.isfile(_p):
            fp = _try_load(_p)
            if fp is not None:
                _CHINESE_FONT_PATH = _p
                _CHINESE_FONT_PROPS = fp
                plt.rcParams['font.sans-serif'] = [fp.get_name()]
                plt.rcParams['axes.unicode_minus'] = False
                return _CHINESE_FONT_PROPS

    # 3) 按字体名查找
    for _name in (
            'WenQuanYi Zen Hei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'SimHei', 'Microsoft YaHei', 'STHeiti',
            'Arial Unicode MS'):
        try:
            _f = font_manager.FontProperties(family=_name)
            _path = font_manager.findfont(_f)
            if _path and 'DejaVu' not in _path:
                fp = _try_load(_path)
                if fp is not None:
                    _CHINESE_FONT_PATH = _path
                    _CHINESE_FONT_PROPS = fp
                    plt.rcParams['font.sans-serif'] = [_name]
                    plt.rcParams['axes.unicode_minus'] = False
                    return _CHINESE_FONT_PROPS
        except Exception:
            continue

    # 4) 运行时下载到 fonts 目录（无本地/系统字体时，短超时避免阻塞）
    import urllib.request
    _cache_dir = os.path.join(_base, 'fonts')
    _cache_file = os.path.join(_cache_dir, 'NotoSansCJKsc-Regular.otf')
    _urls = (
        "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf",
        "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf",
    )
    if not os.path.isfile(_cache_file):
        try:
            os.makedirs(_cache_dir, exist_ok=True)
            for _url in _urls:
                try:
                    req = urllib.request.Request(_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        with open(_cache_file, 'wb') as f:
                            f.write(resp.read())
                    break
                except Exception:
                    continue
        except Exception:
            pass
    if os.path.isfile(_cache_file):
        fp = _try_load(_cache_file)
        if fp is not None:
            _CHINESE_FONT_PATH = _cache_file
            _CHINESE_FONT_PROPS = fp
            plt.rcParams['font.sans-serif'] = [fp.get_name()]
            plt.rcParams['axes.unicode_minus'] = False
            return _CHINESE_FONT_PROPS

    plt.rcParams['axes.unicode_minus'] = False
    return None


def _chinese_font_props(size=None):
    """返回中文字体属性，若传入 size 则使用该字号（用于 ax.text 等）。"""
    _get_chinese_font()
    if _CHINESE_FONT_PATH is not None and size is not None:
        return font_manager.FontProperties(fname=_CHINESE_FONT_PATH, size=size)
    return _CHINESE_FONT_PROPS


_setup_chinese_font = _get_chinese_font
_get_chinese_font()


class LayoutGenerator:
    """布局图生成器类"""

    def __init__(self):
        # self.dir_path = dir_path
        self.required_product_cols = [
            "商品编码", "项目商品类别", "项目大类", "项目中类",
            "项目小类", "项目细类", "品牌名称", "SPU商品名称"
        ]
        self.required_layout_cols = [
            "货架序号", "层数", "层组件顺序", "位置", "垫高位置", "商品编码", "货架模板名称"
        ]
        self.product_col_mapping = {
            "*商品编码": "product_nums",
            "项目商品类别": "item_sale_class_code",
            "项目大类": "item_big_category",
            "项目中类": "item_mid_category",
            "项目小类": "item_small_category",
            "项目细类": "item_tiny_category",
            "品牌名称": "brand_name",
            "SPU商品名称": "spu_product_name"
        }
        self.layout_col_mapping = {
            "*货架序号": "shelf_nums",
            "*层数": "layer_nums",
            "*层组件顺序": "layer_tool_order",
            "*位置": "position",
            "垫高位置": "pad_position",
            "*商品编码": "product_nums",
            "*排面量": "display_col_qty",
            "货架模板名称": "template_name"
        }
        self.product_df = None
        self.layout_df = None
        self.merged_df = None
        self.layout_info_final = None

    def _rename_product_num_col(self, col_name, df, rename_col_name):
        """查找并重命名商品资料表中的商品编码列"""
        product_num_col = next((c for c in df.columns if c == col_name),
                               next((c for c in df.columns if c == col_name.replace("*", "")), None))
        if not product_num_col: raise ValueError(f"商品资料表中未找到'{col_name}'列")
        df.rename(columns={product_num_col: rename_col_name}, inplace=True)
        print(f"已重命名列: {product_num_col} -> {rename_col_name}")
        if col_name == "*商品编码":
            df[rename_col_name] = self._norm_code(df[rename_col_name])
            before = len(df)
            df = df[~df[rename_col_name].apply(self._is_empty_code)].copy()
            dropped = before - len(df)
            if dropped:
                print(f"已剔除商品编码为空的行: {dropped} 行")
        return df

    def _norm_code(self, ser):
        s = ser.astype(str).str.strip()

        # 科学计数法如 8.346e+16 转成整数字符串，否则长编码无法与资料表匹配
        def _one(v):
            if v in ("", "nan", "None") or pd.isna(v):
                return v
            vs = str(v).strip()
            if re.match(r"^[\d.]+e[+-]?\d+$", vs, re.I):
                try:
                    return str(int(float(v)))
                except (ValueError, TypeError):
                    return vs
            return vs

        s = s.apply(_one)
        return s.str.replace(r"\.0$", "", regex=True)

    def _is_empty_code(self, val):
        if pd.isna(val):
            return True
        s = str(val).strip()
        if s == "":
            return True
        if s.lower() in ("nan", "none", "null", "#n/a", "na", "n/a"):
            return True
        return False

    def data_prepare(self, product_file=None, layout_file=None):
        """
        准备数据
        :param product_file: 商品资料表路径或文件对象
        :param layout_file: 落位明细清单路径或文件对象
        """
        # ==========================================查找文件==========================================
        if product_file is None or layout_file is None:
            dir_path = '/Users/wujingjun/PycharmProjects/displayproj/src/AlgorithmFunc/GeneticAlg/test/get_layout/layout_test_file'
            files = glob.glob(os.path.join(dir_path, "*.xlsx"))
            for file in files:
                filename = os.path.basename(file)
                if "商品资料表" in filename:
                    product_file = file
                elif "落位明细清单" in filename:
                    layout_file = file

        if not product_file or not layout_file:
            raise FileNotFoundError(f"在 {self.dir_path} 中未找到'商品资料表'或'落位明细清单'文件")
        print(f"读取商品资料表: {product_file}")
        print(f"读取落位明细清单: {layout_file}")

        # ==========================================读取文件==========================================
        try:
            self.product_df = pd.read_excel(product_file, dtype=str)
            self.layout_df = pd.read_excel(layout_file, dtype=str)
        except Exception as e:
            raise ValueError(f"读取Excel文件失败: {str(e)}")
        self.layout_df = self.layout_df.replace('', np.nan)

        # ==========================================检查必须列名==========================================
        product_columns = self.product_df.columns.str.strip().str.replace("*", "", regex=False)
        missing_cols = [col for col in self.required_product_cols if col not in product_columns]
        if missing_cols:
            raise ValueError(f"商品资料表缺失以下必要列: {missing_cols}")
        layout_columns = self.layout_df.columns.str.strip().str.replace("*", "", regex=False)
        missing_cols = [col for col in self.required_layout_cols if col not in layout_columns]
        if missing_cols:
            raise ValueError(f"落位信息表缺失以下必要列: {missing_cols}")
        # ==========================================列名规范化==========================================
        for col_name, rename_col_name in self.product_col_mapping.items():
            self.product_df = self._rename_product_num_col(col_name, self.product_df, rename_col_name)
        for col_name, rename_col_name in self.layout_col_mapping.items():
            self.layout_df = self._rename_product_num_col(col_name, self.layout_df, rename_col_name)
        print("数据准备完成，列名检查通过并已标准化。")
        # ==========================================落位图精确位置获取==========================================
        sort_cols = ['layer_tool_order', 'position', 'pad_position']
        for col in sort_cols:
            if col in self.layout_df.columns:
                self.layout_df[col] = pd.to_numeric(self.layout_df[col], errors='coerce').fillna(0)
        # 排序：按货架、层、组件顺序、位置、垫高位置
        self.layout_df.sort_values(
            by=['shelf_nums', 'layer_nums', 'layer_tool_order', 'position', 'pad_position'],
            ascending=[True, True, True, True, True],
            inplace=True
        )
        self.layout_df['new_position'] = self.layout_df.groupby(['shelf_nums', 'layer_nums']).cumcount() + 1
        print("落位信息已排序，并生成了新的层内位置编号 'new_position'")
        # ==========================================落位图与商品信息合并==========================================
        # 选取需要的列并合并
        layout_cols = [c for c in list(self.layout_col_mapping.values()) + ['new_position'] if
                       c in self.layout_df.columns]
        product_cols = [c for c in list(self.product_col_mapping.values()) if c in self.product_df.columns]

        self.merged_df = pd.merge(self.layout_df[layout_cols], self.product_df[list(set(product_cols))],
                                  on='product_nums', how='left').fillna(-1)

    def draw_block_canvas(self, s_idx, e_idx, block_width, block_height, text, background_color):
        """
        返回一个matplotlib画布（Figure），绘制单个块矩形和文字，
        文字会自动缩放以适应矩形大小。
        """
        # 计算画布大小
        canvas_width = block_width * (e_idx - s_idx)
        canvas_height = block_height

        # 创建画布
        fig = plt.figure(figsize=(canvas_width / 20, canvas_height / 20))
        # 去除边距
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

        # 画矩形
        plt.fill([0, canvas_width, canvas_width, 0],
                 [0, 0, canvas_height, canvas_height],
                 color=background_color, edgecolor='black')

        if not text:
            fontsize = 12
        else:
            lines = text.split('\n')
            num_lines = len(lines)

            # 计算最长行的等效字符数（中文1，英文0.6）
            max_line_len = 0
            for line in lines:
                l = sum(1 if ord(c) > 127 else 0.6 for c in line)
                max_line_len = max(max_line_len, l)
            max_line_len = max(max_line_len, 1)

            # 高度限制：总高度 / (行数 * 行高系数)
            # 宽度限制：总宽度 / 最长行字符数
            # 3.6 是 unit 转 points 的系数
            limit_h = (canvas_height * 3.6) / (num_lines * 1.2)
            limit_w = (canvas_width * 3.6) / max_line_len

            fontsize = min(limit_h, limit_w) * 0.75  # 0.9 安全边距
        # 添加文字
        fp = _chinese_font_props(size=fontsize)
        if fp:
            plt.text(canvas_width / 2, canvas_height / 2, text,
                     ha='center', va='center', fontproperties=fp)
        else:
            plt.text(canvas_width / 2, canvas_height / 2, text,
                     ha='center', va='center', fontsize=fontsize)

        # 去掉坐标轴
        plt.axis('off')
        plt.xlim(0, canvas_width)
        plt.ylim(0, canvas_height)
        # plt.show()
        return fig

    def _resize_image(self, image, target_width=None, target_height=None):
        """
        Resize image to target width and/or height.
        If only one is provided, the other dimension remains unchanged.
        """
        if target_width is None and target_height is None:
            return image

        h, w = image.shape[:2]
        new_w = target_width if target_width is not None else w
        new_h = target_height if target_height is not None else h

        if new_w == w and new_h == h:
            return image

        from PIL import Image
        pil_img = Image.fromarray(image)
        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
        return np.array(pil_img)

    def _combine_images(self, items, axis=1):
        """
        拼接图像或Figure列表
        :param items: list of Figure or np.ndarray
        :param axis: 0 for vertical, 1 for horizontal
        :return: combined np.ndarray
        """
        if not items:
            return None

        images = []
        # Convert Figures to images if necessary
        for item in items:
            if hasattr(item, 'canvas'):
                fig = item
                fig.canvas.draw()
                w, h = fig.canvas.get_width_height()
                buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8)
                buf.shape = (h, w, 4)
                buf = np.roll(buf, 3, axis=2)  # ARGB -> RGBA
                images.append(buf)
                plt.close(fig)
            elif isinstance(item, np.ndarray):
                images.append(item)
            else:
                continue

        if not images:
            return None

        # Align dimensions
        if axis == 1:  # Horizontal concat, align height
            max_h = max(img.shape[0] for img in images)
            processed_images = []
            for img in images:
                h, w, c = img.shape
                if h < max_h:
                    # Pad bottom with white
                    pad = np.full((max_h - h, w, c), 255, dtype=np.uint8)
                    img = np.concatenate([img, pad], axis=0)
                processed_images.append(img)
            return np.concatenate(processed_images, axis=1)
        else:  # Vertical concat, align width
            max_w = max(img.shape[1] for img in images)
            processed_images = []
            for img in images:
                h, w, c = img.shape
                if w < max_w:
                    # Pad right with white
                    pad = np.full((h, max_w - w, c), 255, dtype=np.uint8)
                    img = np.concatenate([img, pad], axis=1)
                processed_images.append(img)
            return np.concatenate(processed_images, axis=0)

    def _combine_shelves_with_gap(self, shelf_images, gap_width=50):
        """
        拼接多个货架图像，中间添加间隔
        :param shelf_images: list of np.ndarray
        :param gap_width: int, width of the gap in pixels
        :return: combined np.ndarray
        """
        if not shelf_images:
            return None

        # 1. 统一所有货架的高度（取最大高度）
        max_h = max(img.shape[0] for img in shelf_images)
        resized_shelf_images = []
        for img in shelf_images:
            h, w, c = img.shape
            if h < max_h:
                # Pad bottom with white
                pad = np.full((max_h - h, w, c), 255, dtype=np.uint8)
                img = np.concatenate([img, pad], axis=0)
            resized_shelf_images.append(img)

        # 2. 添加货架间隔
        final_images = []
        for i, img in enumerate(resized_shelf_images):
            final_images.append(img)
            # 如果不是最后一个，添加间隔
            if i < len(resized_shelf_images) - 1:
                h, w, c = img.shape
                gap = np.full((h, gap_width, c), 255, dtype=np.uint8)
                final_images.append(gap)

        # 3. 拼接
        return self._combine_images(final_images, axis=1)

    def draw_layout(self):
        """生成用于绘图的聚合数据"""
        if self.layout_info_final is None: raise ValueError("请先执行 get_dimension_info")

        # 1. 准备数据
        df = self.layout_info_final.copy()
        shelves = sorted(list(set([int(i) for i in df['shelf_nums']])))
        layers = sorted(list(set([int(i) for i in df['layer_nums']])))
        posids = sorted(list(set([int(i.split('_')[-1]) for i in df['pos_id']])))

        # 2. 设置绘图参数
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'PingFang SC', 'Heiti TC']
        plt.rcParams['axes.unicode_minus'] = False
        unique_values = df['dimension_value'].unique()
        colors = cm.get_cmap('tab20', len(unique_values))
        val_color_map = {val: colors(i) for i, val in enumerate(unique_values)}
        shelf_gap = 50
        block_height = 400
        block_width = 1000
        layer_width = max(posids) * 1000
        layer_height = 400
        shelf_height = layer_height * max(layers)
        shelf_width = layer_width * len(shelves)
        # 生成各层的图
        shelf_images = []
        for shelf_id in shelves:
            shelf_layer_images = []
            for layer_id in layers:
                print('如果layer_df为空，则生成一个空图，宽度为layer_width,高度为layer_height')
                layer_df = df[(df['shelf_nums'].astype(int) == shelf_id) & (df['layer_nums'].astype(int) == layer_id)]
                # layer_df = df[(df['shelf_nums'].astype(int) == 3) & (df['layer_nums'].astype(int) == 4)]
                if len(layer_df) == 0:
                    layer_img = np.ones((layer_height, layer_width, 3), dtype=np.uint8) * 255
                    shelf_layer_images.append(layer_img)
                    continue
                print(
                    '生成一张宽为layer_width,高为layer_height的canvas，根据pos_id分配该层的位置，并在每个pos_id上增加value的值')
                block_id_list = sorted(list(set(layer_df['pos_id'].tolist())))  # ['1_3', '3_4', '4_5']
                layer_canvas = []
                for block_id in block_id_list:
                    s_idx, e_idx = map(int, block_id.split('_'))
                    block_values = layer_df[layer_df['pos_id'] == block_id] \
                        .sort_values('dimension_name')['dimension_value'].tolist()
                    text = "\n".join([str(i) for i in block_values])
                    color = val_color_map[block_values[0]]
                    # text = '测试\n测试'
                    print('生成一张图，宽度为block_width*(e_idx-s_idx),高度为block_height，并且在图上增加text')
                    fig = self.draw_block_canvas(s_idx, e_idx, block_width=50, block_height=80, text=text,
                                                 background_color=color)
                    layer_canvas.append(fig)

                # 拼接层内的块（横向）
                layer_img = self._combine_images(layer_canvas, axis=1)
                if layer_img is not None:
                    shelf_layer_images.append(layer_img)

            # 拼接货架内的层（纵向）
            # 注意：通常层号小的在下，层号大的在上。如果 layers 是升序 [1, 2, 3]，
            # 且我们希望 1 在下，3 在上，那么在图像上应该是 [3, 2, 1] 的顺序（因为图像坐标 0 是顶部）
            # 所以需要反转列表
            if shelf_layer_images:
                # shelf_layer_images.reverse()
                # Use the maximum width among the layers in this shelf
                target_w = max(img.shape[1] for img in shelf_layer_images)
                resized_images = []
                for img in shelf_layer_images:
                    resized_images.append(self._resize_image(img, target_width=target_w))

                shelf_img = self._combine_images(resized_images, axis=0)

                if shelf_img is not None:
                    shelf_images.append(shelf_img)
                    # 显示货架图像
                    plt.figure(figsize=(10, 10))  # 尺寸可以根据需要调整
                    plt.imshow(shelf_img)
                    plt.axis('off')
                    plt.title(f"Shelf {shelf_id} Layer {layer_id}")
                    # plt.show()
                    # print(1)
            else:
                shelf_images.append(np.ones((shelf_height, shelf_width, 3), dtype=np.uint8) * 255)
        print(
            '还需要把多个shelf_id拼成一行并显示，每个shelf_id的宽度为shelf_width，高度为shelf_height,要进行reshape，并且shelf之间的空隙为shelf_gap,并显示')

        if shelf_images:
            shelf_img = self._combine_shelves_with_gap(shelf_images, gap_width=shelf_gap)
            if shelf_img is not None:
                return shelf_img
            else:
                return np.ones((shelf_height, shelf_width, 3), dtype=np.uint8) * 255
        else:
            return np.ones((shelf_height, shelf_width, 3), dtype=np.uint8) * 255

    def get_dimension_info(self, default_dimension_name=['item_mid_category', 'item_sale_class_code'],
                           finetune_layer_dimension=[(1, 1, ['brand_name'])]):
        """生成每个位置的维度信息，支持默认维度和层级微调"""

        def assign_dimension_id(row):
            dimension_name_list = eval(row['dimension_name_list'])
            value_output = []
            for i in dimension_name_list:
                if i =='item_small_category':
                    value_output.append(f"{row['item_mid_category']}_{row['item_small_category']}")
                elif i =='item_tiny_category':
                    value_output.append(f"{row['item_mid_category']}_{row['item_small_category']}_{row['item_tiny_category']}")
                else:
                    value_output.append(row[i])
            return str([row[i] for i in dimension_name_list]), str(value_output)

        if self.merged_df is None: raise ValueError("请先执行 data_prepare")

        # ==========================================生成默认维度信息==========================================
        self.merged_df['dimension_name_list'] = str(default_dimension_name)
        # ==========================================应用微调==========================================
        if finetune_layer_dimension:
            for s_num, l_num, dims in finetune_layer_dimension:
                mask = (self.merged_df['shelf_nums'].astype(str) == str(s_num)) & \
                       (self.merged_df['layer_nums'].astype(str) == str(l_num))
                if mask.any():
                    self.merged_df.loc[mask, 'dimension_name_list'] = str(dims)
        # ==========================================返回落位布局图数据结果==========================================
        # self.merged_df['value_list'] = self.merged_df.apply(assign_dimension_id, axis=1)
        self.merged_df[['value_list', 'value_output']] = self.merged_df.apply(
            assign_dimension_id, axis=1, result_type='expand'
        )
        df = self.merged_df.sort_values(['shelf_nums', 'layer_nums', 'new_position'])
        results = []
        for (s_num, l_num), group in df.groupby(['shelf_nums', 'layer_nums']):
            group['block_id'] = (group['value_list'] != group['value_list'].shift()).cumsum()
            for _, block in group.groupby('block_id'):
                positions = sorted(block['new_position'].tolist())
                pos_str = f"{positions[0]}_{positions[-1] + 1}"
                dimension_names_list = eval(block['dimension_name_list'].iloc[0])
                values_list = eval(block['value_list'].iloc[0])
                values_list_output = eval(block['value_output'].iloc[0])
                for dimension_name, value, value_output in zip(dimension_names_list, values_list,values_list_output):
                    # 这里可以同时遍历 dimension_name 和 value
                    results.append({
                        'shelf_nums': s_num,
                        'layer_nums': l_num,
                        'pos_id': pos_str,
                        'dimension_name': dimension_name,  # 暂用 dim_1, dim_2 表示
                        'dimension_value': value,
                        'dimension_value_output': value_output,
                    })
        self.layout_info_final = pd.DataFrame(results)

    def run(self):
        self.data_prepare()
        self.get_dimension_info()
        self.draw_layout()


if __name__ == "__main__":
    folder_path = '/Users/wujingjun/PycharmProjects/displayproj/src/AlgorithmFunc/GeneticAlg/test/get_layout/layout_test_file'
    generator = LayoutGenerator()
    generator.run()