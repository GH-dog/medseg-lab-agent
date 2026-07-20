# -*- coding: utf-8 -*-
"""医学图像分割基础知识库（CNN / U-Net / Transformer）。"""
from __future__ import annotations

MEDSEG_KNOWLEDGE_BASE = {
    "cnn_basics": {
        "title": "卷积神经网络 CNN 基础",
        "content": """
CNN（Convolutional Neural Network）是医学图像分割的经典骨干。
核心组件：卷积层提取局部特征、池化层降采样扩大感受野、激活函数（ReLU）引入非线性。
医学影像特点：灰度/多模态（CT/MRI/超声）、类间不平衡、边界模糊。
常见骨干：VGG、ResNet、DenseNet；分割任务通常采用编码器-解码器结构。
评价指标：Dice、IoU、Hausdorff Distance（HD95）、ASD。
""",
    },
    "unet_architecture": {
        "title": "U-Net 基本架构",
        "content": """
U-Net（Ronneberger 2015）是医学图像分割的里程碑结构。
结构：对称的编码器（下采样）与解码器（上采样），跳跃连接拼接浅层细节与深层语义。
优点：小样本数据也能较好训练；边界细节保留好。
变体：3D U-Net（体数据）、UNet++（密集跳跃）、Attention U-Net（注意力门控）、nnU-Net（自动配置）。
训练要点：Dice+CE 联合损失、数据增强（旋转/翻转/弹性形变）、深监督。
""",
    },
    "nnunet": {
        "title": "nnU-Net 简介",
        "content": """
nnU-Net（Isensee et al.）是“自配置”的 U-Net 框架：根据数据集自动决定预处理、网络拓扑、训练策略。
对新生：先用 nnU-Net 做强基线，再考虑定制网络。
关键流程：指纹分析 -> 规则规划 -> 训练 2D/3D/级联 -> 集成推理。
""",
    },
    "transformer_seg": {
        "title": "Transformer 分割架构",
        "content": """
Vision Transformer / Swin Transformer 将图像切成 patch，用自注意力建模长程依赖。
医学分割代表：TransUNet（CNN编码器+Transformer）、Swin-UNet、UNETR、SegFormer、MedT。
优势：全局上下文；挑战：数据量需求大、显存高、小目标细节可能弱于纯 CNN。
混合架构（CNN+Transformer）在医学分割中更常见。
""",
    },
    "datasets_metrics": {
        "title": "常用数据集与指标",
        "content": """
数据集示例：BraTS（脑肿瘤）、LiTS（肝脏）、KiTS（肾脏）、MSD、ACDC、Synapse 多器官。
指标：Dice Coefficient、Jaccard/IoU、Sensitivity/Specificity、HD95。
注意：报告均值±标准差，跨中心泛化与标定差异。
""",
    },
    "pipeline": {
        "title": "分割实验基本流程",
        "content": """
1. 数据：脱敏、标注质量检查、划分 train/val/test（按病例，勿按切片泄漏）。
2. 预处理：重采样 spacing、强度归一化/窗宽窗位、裁剪/填充。
3. 模型：基线 U-Net/nnU-Net，再换 Transformer 混合模型。
4. 训练：学习率、早停、混合精度、检查点。
5. 后处理：连通域、最大组件、条件随机场（可选）。
6. 分析：失败病例可视化、消融实验。
""",
    },
}


def iter_documents() -> list[dict]:
    """转为 RAG 文档列表。"""
    docs = []
    for key, item in MEDSEG_KNOWLEDGE_BASE.items():
        text = f"{item['title']}\n{item['content'].strip()}"
        docs.append({"id": key, "title": item["title"], "text": text})
    return docs


def get_all_text() -> str:
    return "\n\n".join(d["text"] for d in iter_documents())
