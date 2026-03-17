import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import sys
from PIL import Image

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from layout_generate import LayoutGenerator
except ImportError:
    st.error("无法导入 LayoutGenerator，请检查 layout_generate.py 是否在同一目录下。")
    st.stop()

st.set_page_config(page_title="货架落位图生成器", layout="wide")
st.title("🛒 货架落位图生成器")

# Sidebar: File Upload
st.sidebar.header("1. 上传文件")
prod_file = st.sidebar.file_uploader("上传商品资料表 (Excel)", type=['xlsx'])
layout_file = st.sidebar.file_uploader("上传落位明细清单 (Excel)", type=['xlsx'])

# Initialize session state
if 'generator' not in st.session_state:
    st.session_state.generator = None
if 'fine_tuning_list' not in st.session_state:
    st.session_state.fine_tuning_list = []
if 'current_img' not in st.session_state:
    st.session_state.current_img = None
if 'default_dims' not in st.session_state:
    st.session_state.default_dims = []

# Default attributes list
DEFAULT_ATTRS = ['项目中类', '项目小类', '项目细类', '品牌名称', 'spu名称', '项目商品类别','IP']
DEFAULT_ATTRS_MAPPING = {'项目中类': "item_mid_category",
                         '项目小类': "item_small_category",
                         '项目细类': "item_tiny_category",
                         '品牌名称': "brand_name",
                         'spu名称': "spu_product_name",
                         '项目商品类别': "item_sale_class_code",
                         'IP': "ip",
                         }

if prod_file and layout_file:
    # Initialize Generator
    if st.session_state.generator is None:
        with st.spinner("正在加载数据..."):
            try:
                # LayoutGenerator expects file paths or file-like objects for read_excel
                # Since we modified data_prepare to accept arguments, we pass them directly.
                # Note: read_excel supports file-like objects (BytesIO) which st.file_uploader returns.
                generator = LayoutGenerator()
                generator.data_prepare(prod_file, layout_file)
                st.session_state.generator = generator
                st.success("数据加载成功！")
            except Exception as e:
                st.error(f"数据加载失败: {str(e)}")
                st.stop()

    generator = st.session_state.generator

    # --- Section 2: Configuration ---
    st.header("2. 配置默认属性")

    col1, col2 = st.columns(2)
    with col1:
        attr1 = st.selectbox("选择主要属性 (第一层)", DEFAULT_ATTRS, index=0)
    with col2:
        attr2 = st.selectbox("选择次要属性 (第二层, 可选)", ["None"] + DEFAULT_ATTRS)

    current_default_dims = [DEFAULT_ATTRS_MAPPING[attr1]]
    if attr2 != "None":
        current_default_dims.append(DEFAULT_ATTRS_MAPPING[attr2])

    if st.button("生成默认视图"):
        st.session_state.default_dims = current_default_dims
        st.session_state.fine_tuning_list = []  # Reset fine-tuning
        with st.spinner("正在生成视图..."):
            try:
                print(f'查看当前视图：{current_default_dims}')
                generator.get_dimension_info(current_default_dims, [])
                img = generator.draw_layout()
                st.session_state.current_img = img
                st.rerun()
            except Exception as e:
                st.error(f"生成视图失败: {str(e)}")

    # --- Section 3: Fine-tuning ---
    st.header("3. 微调与预览")

    shelves = []
    layers = []

    # Try to extract shelf and layer info if available
    if hasattr(generator,
               'merged_df') and generator.merged_df is not None and 'shelf_nums' in generator.merged_df.columns:
        try:
            # Ensure numeric sorting if possible
            shelves = sorted(generator.merged_df['shelf_nums'].unique().tolist(),
                             key=lambda x: int(x) if str(x).isdigit() else str(x))
            layers = sorted(generator.merged_df['layer_nums'].unique().tolist(),
                            key=lambda x: int(x) if str(x).isdigit() else str(x))
        except:
            shelves = sorted(generator.merged_df['shelf_nums'].unique().tolist())
            layers = sorted(generator.merged_df['layer_nums'].unique().tolist())

    if not shelves:
        st.info("请先点击'生成默认视图'以加载货架结构信息。")

    with st.expander("微调特定层 (点击展开)"):
        st.info("在此处可以为特定的货架层设置不同的显示属性。")

        if shelves and layers:
            ft_col1, ft_col2, ft_col3, ft_col4, ft_col5 = st.columns(5)

            selected_shelf = ft_col1.selectbox("选择货架", shelves)

            # Filter layers for selected shelf
            current_shelf_layers = layers
            if hasattr(generator, 'merged_df') and generator.merged_df is not None:
                mask = generator.merged_df['shelf_nums'] == selected_shelf
                try:
                    current_shelf_layers = sorted(generator.merged_df[mask]['layer_nums'].unique().tolist(),
                                                  key=lambda x: int(x) if str(x).isdigit() else str(x))
                except:
                    current_shelf_layers = sorted(generator.merged_df[mask]['layer_nums'].unique().tolist())

            selected_layer = ft_col2.selectbox("选择层数", current_shelf_layers)

            ft_attr1 = ft_col3.selectbox("该层主要属性", DEFAULT_ATTRS, key="ft_a1")
            ft_attr2 = ft_col4.selectbox("该层次要属性", ["None"] + DEFAULT_ATTRS, key="ft_a2")

            if ft_col5.button("添加/更新微调配置"):
                ft_dims = [DEFAULT_ATTRS_MAPPING[ft_attr1]]
                if ft_attr2 != "None":
                    ft_dims.append(DEFAULT_ATTRS_MAPPING[ft_attr2])

                # Update list: remove existing config for this shelf/layer if any
                new_list = [item for item in st.session_state.fine_tuning_list
                            if not (str(item[0]) == str(selected_shelf) and str(item[1]) == str(selected_layer))]
                new_list.append((selected_shelf, selected_layer, ft_dims))
                st.session_state.fine_tuning_list = new_list
                st.success(f"已更新配置: 货架{selected_shelf} 层{selected_layer} -> {ft_dims}")

        # Show current fine-tuning
        if st.session_state.fine_tuning_list:
            st.write("当前微调配置:")
            ft_display = []
            for s, l, d in st.session_state.fine_tuning_list:
                ft_display.append({"货架": s, "层数": l, "属性": str(d)})
            st.dataframe(pd.DataFrame(ft_display))

            col_apply, col_clear = st.columns(2)
            with col_apply:
                if st.button("应用微调并重新生成"):
                    with st.spinner("正在重新生成视图..."):
                        try:
                            # Use stored default dims
                            dims = st.session_state.default_dims if st.session_state.default_dims else current_default_dims
                            generator.get_dimension_info(dims, st.session_state.fine_tuning_list)
                            img = generator.draw_layout()
                            st.session_state.current_img = img
                            st.rerun()
                        except Exception as e:
                            st.error(f"重新生成失败: {str(e)}")
            with col_clear:
                if st.button("清除所有微调"):
                    st.session_state.fine_tuning_list = []
                    st.rerun()

    # --- Display Plot ---
    if st.session_state.current_img is not None:
        st.subheader("落位图预览")
        st.image(st.session_state.current_img, caption="生成的落位图", use_column_width=True)

        # --- Section 4: Download ---
        st.header("4. 下载结果")

        # Save Plot to buffer
        # current_img is numpy array
        try:
            img_pil = Image.fromarray(st.session_state.current_img.astype('uint8'))
            img_buffer = io.BytesIO()
            img_pil.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            st.download_button(
                label="下载落位图 (PNG)",
                data=img_buffer,
                file_name="shelf_layout.png",
                mime="image/png"
            )
        except Exception as e:
            st.error(f"图片处理失败: {e}")

        # Save Excel
        if hasattr(generator, 'layout_info_final') and generator.layout_info_final is not None:
            df_export = generator.layout_info_final.rename(columns={'dimension_value_output': 'value'})

            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_export.drop(columns=["dimension_value"]).to_excel(writer, index=False)
            excel_buffer.seek(0)

            st.download_button(
                label="下载落位信息 (Excel)",
                data=excel_buffer,
                file_name=f"{generator.layout_df['template_name'].iloc[0]}_布局图.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            with st.expander("查看落位信息数据"):
                st.dataframe(df_export.drop(columns=["dimension_value"]))

else:
    st.info("请在左侧上传必须的文件以开始。")