"""
CAD Agent Workflow Visualization
使用matplotlib生成专业流程图
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(18, 22))
ax.set_xlim(0, 10)
ax.set_ylim(0, 24)
ax.axis('off')

# 定义颜色
colors = {
    'start': '#81C784',
    'input': '#FFE0B2',
    'process': '#C8E6C9',
    'condition': '#FFF9C4',
    'confirm': '#BBDEFB',
    'tool': '#FFCDD2',
    'rag': '#B2DFDB',
    'chat': '#E1BEE7',
    'summary': '#F0F4C3'
}

def draw_node(ax, x, y, text, color, width=2.2, height=0.8):
    """绘制圆角矩形节点"""
    box = FancyBboxPatch((x - width/2, y - height/2), width, height,
                         boxstyle="round,pad=0.1",
                         facecolor=color, edgecolor='black', linewidth=1.5)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', fontsize=9, 
            weight='bold', wrap=True)
    return (x, y)

def draw_diamond(ax, x, y, text, color, size=1.2):
    """绘制菱形（条件节点）"""
    diamond = plt.Polygon([
        [x, y + size/2],
        [x + size, y],
        [x, y - size/2],
        [x - size, y]
    ], facecolor=color, edgecolor='black', linewidth=1.5)
    ax.add_patch(diamond)
    ax.text(x, y, text, ha='center', va='center', fontsize=8, weight='bold')
    return (x, y)

def draw_arrow(ax, start, end, label='', color='black', style='-'):
    """绘制带标签的箭头"""
    arrow = FancyArrowPatch(start, end,
                           arrowstyle='->', mutation_scale=20,
                           color=color, linewidth=2, linestyle=style)
    ax.add_patch(arrow)
    if label:
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        ax.text(mid_x + 0.15, mid_y, label, fontsize=8, 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# 绘制标题
ax.text(5, 23, 'CAD Agent 工作流程图', ha='center', va='center', 
        fontsize=18, weight='bold')

# 第一列：主流程
start = draw_node(ax, 5, 21.5, 'START', colors['start'], 1.5, 0.6)
begin_input = draw_node(ax, 5, 19.5, 'begin_input\n(接收用户输入)', colors['input'])
plan_run = draw_node(ax, 5, 17, 'plan_run\n(生成执行计划)', colors['process'])
post_plan = draw_node(ax, 5, 14.5, 'post_plan_input\n(计划后处理)', colors['condition'])
proc_confirm = draw_node(ax, 5, 12, 'proc_confirm\n(处理用户确认)', colors['confirm'])
toolcall_plan = draw_node(ax, 5, 9.5, 'toolcall_plan\n(准备工具调用)', colors['process'])
tool_call = draw_node(ax, 5, 7, 'tool_call\n(执行工具)', colors['tool'])

# 第二列：RAG和对话路径
rtrv = draw_node(ax, 8.5, 19.5, 'rtrv\n(检索知识)', colors['rag'])
rag = draw_node(ax, 8.5, 17, 'rag\n(RAG回答)', colors['rag'])
chat = draw_node(ax, 1.5, 19.5, 'chat\n(通用对话)', colors['chat'])

# 第三列：循环节点
plan_update = draw_node(ax, 8.5, 9.5, 'plan_update\n(更新计划)', colors['condition'])
tool_summary = draw_node(ax, 8.5, 7, 'tool_summary\n(生成总结)', colors['summary'])

# 绘制主要连接
draw_arrow(ax, start, begin_input, '', 'black')
draw_arrow(ax, begin_input, plan_run, 'cad_run', 'black')
draw_arrow(ax, plan_run, post_plan, '', 'black')
draw_arrow(ax, post_plan, proc_confirm, 'success/\npartial_success', 'green')
draw_arrow(ax, proc_confirm, toolcall_plan, 'confirm_plan', 'green')
draw_arrow(ax, toolcall_plan, tool_call, '', 'black')

# 条件分支
draw_arrow(ax, begin_input, rtrv, 'cad_rag', 'blue')
draw_arrow(ax, begin_input, chat, 'general_chat', 'purple')
draw_arrow(ax, post_plan, (3, 14.5), 'failed/\nmore_info', 'red', '--')
draw_arrow(ax, proc_confirm, (7.5, 12), 'clarify_plan', 'orange', ':')
draw_arrow(ax, proc_confirm, (3, 12), 'reject_plan', 'red', '--')

# 侧边路径连接
draw_arrow(ax, rtrv, rag, '', 'blue')
draw_arrow(ax, rag, (5, 19.5), '返回', 'blue', '--')
draw_arrow(ax, chat, (5, 19.5), '返回', 'purple', '--')

# 工具执行循环
draw_arrow(ax, tool_call, tool_summary, 'run_done', 'green')
draw_arrow(ax, tool_call, plan_update, 'running', 'orange')
draw_arrow(ax, plan_update, tool_call, '继续执行', 'black', '-')

# 工具总结返回
draw_arrow(ax, tool_summary, (5, 7), '完成', 'blue', '--')
draw_arrow(ax, (5, 7), begin_input, '循环', 'blue', '--')

# 失败重连
draw_arrow(ax, (3, 14.5), (3, 17), '', 'red', '--')
draw_arrow(ax, (3, 17), plan_run, '', 'red', '--')
draw_arrow(ax, (3, 12), (3, 14.5), '', 'red', '--')

# 澄清路径
draw_arrow(ax, (7.5, 12), rag, '', 'orange', ':')

# 添加图例
legend_elements = [
    mpatches.Patch(facecolor=colors['start'], edgecolor='black', label='开始节点'),
    mpatches.Patch(facecolor=colors['input'], edgecolor='black', label='输入节点'),
    mpatches.Patch(facecolor=colors['process'], edgecolor='black', label='处理节点'),
    mpatches.Patch(facecolor=colors['condition'], edgecolor='black', label='条件节点'),
    mpatches.Patch(facecolor=colors['confirm'], edgecolor='black', label='确认节点'),
    mpatches.Patch(facecolor=colors['tool'], edgecolor='black', label='工具执行'),
    mpatches.Patch(facecolor=colors['rag'], edgecolor='black', label='RAG检索'),
    mpatches.Patch(facecolor=colors['chat'], edgecolor='black', label='通用对话'),
    mpatches.Patch(facecolor=colors['summary'], edgecolor='black', label='总结节点'),
]

ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0.02, 0.98), fontsize=9)

# 添加说明框
explanation = """
工作流说明:
1. begin_input: 接收用户输入，根据agent_type路由到不同路径
2. plan_run: 分析需求并生成执行计划
3. post_plan_input: 判断计划可行性 (success/partial_success/failed/more_info)
4. proc_confirm: 处理用户确认/拒绝/澄清请求
5. tool_call: 顺序执行工具，支持动态更新
6. 循环执行: tool_call ↔ plan_update 直到所有工具执行完毕
"""
ax.text(5, 2.5, explanation, ha='center', va='center', fontsize=9,
        bbox=dict(boxstyle='round', facecolor='#F5F5F5', alpha=0.8))

plt.tight_layout()
plt.savefig('cad_agent_workflow.png', dpi=200, bbox_inches='tight', facecolor='white')
plt.savefig('cad_agent_workflow.svg', bbox_inches='tight', facecolor='white')
print("✓ 流程图已生成:")
print("  - cad_agent_workflow.png (PNG格式)")
print("  - cad_agent_workflow.svg (SVG矢量格式)")
plt.show()
